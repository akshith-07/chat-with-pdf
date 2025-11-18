"""
Celery tasks for asynchronous document processing
"""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id):
    """
    Async task to process uploaded document

    Args:
        document_id: ID of the Document to process

    Returns:
        Dictionary with processing results
    """
    from .models import Document
    from .utils import extract_text_from_pdf, detect_if_scanned
    from chat.services import GeminiService

    try:
        # Get document
        document = Document.objects.get(id=document_id)

        logger.info(f"Processing document {document_id}: {document.title}")

        # Update status
        document.processing_status = 'processing'
        document.save()

        # Check if OCR is needed
        try:
            ocr_needed = detect_if_scanned(document.file.path)
            document.ocr_required = ocr_needed

            if ocr_needed:
                logger.warning(f"Document {document_id} requires OCR (scanned PDF)")
                # Note: OCR implementation would go here
                # For now, we'll try regular extraction
        except Exception as e:
            logger.warning(f"Error checking OCR requirement: {str(e)}")

        # Extract text from PDF
        try:
            full_text, page_count = extract_text_from_pdf(document.file.path)
            document.extracted_text = full_text
            document.page_count = page_count
            logger.info(f"Extracted {len(full_text)} characters from {page_count} pages")
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            document.processing_status = 'failed'
            document.processing_error = f"Text extraction failed: {str(e)}"
            document.save()
            raise

        # Generate AI insights
        try:
            gemini = GeminiService()
            insights = gemini.generate_document_insights(full_text, document.title)

            # Update document with insights
            document.summary = insights.get('summary', '')
            document.key_entities = insights.get('entities', {})
            document.key_topics = insights.get('topics', [])
            document.important_dates = insights.get('dates', [])
            document.document_type = insights.get('document_type', 'other')
            document.sentiment = insights.get('sentiment', 'neutral')

            logger.info(f"Generated AI insights for document {document_id}")

        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            # Don't fail the whole process if AI fails
            document.processing_error = f"AI insights failed: {str(e)}"

        # Generate suggested questions
        try:
            questions = gemini.generate_suggested_questions([document])
            from chat.models import SuggestedQuestion

            # Delete old questions
            SuggestedQuestion.objects.filter(document=document).delete()

            # Create new questions
            for idx, question in enumerate(questions):
                question_type = 'summary' if idx == 0 else 'detail' if idx < 3 else 'analysis'
                SuggestedQuestion.objects.create(
                    document=document,
                    question=question,
                    question_type=question_type,
                    order=idx
                )

            logger.info(f"Generated {len(questions)} suggested questions")

        except Exception as e:
            logger.error(f"Error generating suggested questions: {str(e)}")

        # Mark as completed
        document.processing_status = 'completed'
        document.save()

        logger.info(f"Successfully processed document {document_id}")

        return {
            'success': True,
            'document_id': document_id,
            'page_count': page_count,
            'text_length': len(full_text)
        }

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'success': False, 'error': 'Document not found'}

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")

        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.processing_error = str(e)
            document.save()
        except Exception:
            pass

        # Retry task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def generate_document_highlights(document_id, page_numbers=None):
    """
    Generate AI highlights for document pages

    Args:
        document_id: ID of the Document
        page_numbers: List of page numbers to process (None = all pages)

    Returns:
        Number of highlights created
    """
    from .models import Document, DocumentHighlight
    from .utils import extract_page_text
    from chat.services import GeminiService

    try:
        document = Document.objects.get(id=document_id)
        gemini = GeminiService()

        # Determine which pages to process
        if page_numbers is None:
            page_numbers = range(1, min(document.page_count + 1, 11))  # First 10 pages

        highlight_count = 0

        for page_num in page_numbers:
            try:
                # Extract page text
                page_text = extract_page_text(document.file.path, page_num)

                if not page_text or len(page_text.strip()) < 50:
                    continue

                # Generate highlights
                highlights = gemini.smart_highlights(page_text, page_num)

                # Create highlight objects
                for highlight_data in highlights:
                    DocumentHighlight.objects.create(
                        document=document,
                        page=page_num,
                        content=highlight_data.get('text', ''),
                        highlight_type=highlight_data.get('type', 'important'),
                        position={},  # Would be calculated by frontend
                        color='#FFEB3B'  # Yellow default
                    )
                    highlight_count += 1

            except Exception as e:
                logger.warning(f"Error generating highlights for page {page_num}: {str(e)}")
                continue

        logger.info(f"Generated {highlight_count} highlights for document {document_id}")
        return highlight_count

    except Exception as e:
        logger.error(f"Error in generate_document_highlights: {str(e)}")
        return 0


@shared_task
def cleanup_old_exports():
    """
    Clean up old exported conversation files (older than 30 days)
    """
    from chat.models import ConversationExport
    from django.utils import timezone
    from datetime import timedelta
    import os

    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        old_exports = ConversationExport.objects.filter(created_at__lt=cutoff_date)

        deleted_count = 0
        for export in old_exports:
            try:
                # Delete file
                if export.file and os.path.exists(export.file.path):
                    os.remove(export.file.path)

                # Delete record
                export.delete()
                deleted_count += 1

            except Exception as e:
                logger.warning(f"Error deleting export {export.id}: {str(e)}")

        logger.info(f"Cleaned up {deleted_count} old exports")
        return deleted_count

    except Exception as e:
        logger.error(f"Error in cleanup_old_exports: {str(e)}")
        return 0


@shared_task
def update_usage_analytics(workspace_id, user_id, metric_type, value=1):
    """
    Update usage analytics for a workspace/user

    Args:
        workspace_id: Workspace ID
        user_id: User ID
        metric_type: Type of metric (documents_uploaded, questions_asked, etc.)
        value: Value to add (default 1)
    """
    from documents.models import UsageAnalytics
    from django.utils import timezone

    try:
        today = timezone.now().date()

        # Get or create analytics record for today
        analytics, created = UsageAnalytics.objects.get_or_create(
            workspace_id=workspace_id,
            user_id=user_id,
            date=today
        )

        # Update the metric
        if metric_type == 'documents_uploaded':
            analytics.documents_uploaded += value
        elif metric_type == 'questions_asked':
            analytics.questions_asked += value
        elif metric_type == 'conversations_started':
            analytics.conversations_started += value
        elif metric_type == 'tokens_used':
            analytics.tokens_used += value
        elif metric_type == 'processing_time':
            analytics.processing_time += value

        analytics.save()

        return True

    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")
        return False
