"""
Gemini AI Service for document analysis and chat
"""

import google.generativeai as genai
from django.conf import settings
import re
import json
import logging
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class GeminiService:
    """Service class for Google Gemini AI interactions"""

    def __init__(self):
        """Initialize Gemini with API key"""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("Gemini AI service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {str(e)}")
            raise

    def generate_document_insights(self, text: str, title: str) -> Dict[str, any]:
        """
        Generate comprehensive document insights using AI

        Args:
            text: Document text content
            title: Document title

        Returns:
            Dictionary with summary, entities, topics, etc.
        """
        try:
            # Limit text to avoid token limits (use first 20k chars for analysis)
            text_sample = text[:20000] if len(text) > 20000 else text

            prompt = f"""Analyze this document titled "{title}" and provide comprehensive insights.

Document content:
{text_sample}

Provide the following analysis in JSON format:
1. A concise summary (100-150 words)
2. Key entities:
   - People (names of individuals mentioned)
   - Organizations (companies, institutions)
   - Locations (places, cities, countries)
3. Important dates and events (chronological list)
4. Main topics/themes (list of 3-7 topics)
5. Document type (choose from: contract, research, report, manual, legal, financial, educational, other)
6. Overall sentiment (positive, neutral, negative, or mixed)
7. Key takeaways (3-5 bullet points)

Return ONLY valid JSON in this exact format:
{{
    "summary": "Brief summary here...",
    "entities": {{
        "people": ["Name 1", "Name 2"],
        "organizations": ["Org 1", "Org 2"],
        "locations": ["Location 1", "Location 2"]
    }},
    "dates": ["2024-01-15: Event description", "2024-02-20: Another event"],
    "topics": ["Topic 1", "Topic 2", "Topic 3"],
    "document_type": "research",
    "sentiment": "neutral",
    "takeaways": ["Key point 1", "Key point 2", "Key point 3"]
}}"""

            start_time = time.time()
            response = self.model.generate_content(prompt)
            processing_time = time.time() - start_time

            # Parse JSON response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            insights = json.loads(response_text.strip())

            logger.info(f"Generated insights for '{title}' in {processing_time:.2f}s")
            return insights

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {str(e)}")
            # Return default structure
            return {
                'summary': response.text[:500] if response and response.text else "Unable to generate summary",
                'entities': {'people': [], 'organizations': [], 'locations': []},
                'dates': [],
                'topics': [],
                'document_type': 'other',
                'sentiment': 'neutral',
                'takeaways': []
            }
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            raise

    def multi_document_chat(
        self,
        documents: List,
        question: str,
        history: List = None
    ) -> Dict[str, any]:
        """
        Chat with multiple documents simultaneously

        Args:
            documents: List of Document objects
            question: User's question
            history: List of previous Message objects

        Returns:
            Dictionary with answer, citations, metadata
        """
        try:
            start_time = time.time()

            # Build context from all documents
            context = "You are an expert document analyst. You have access to the following documents:\n\n"

            for idx, doc in enumerate(documents, 1):
                # Limit each document to avoid token limits
                doc_text = doc.extracted_text[:10000] if len(doc.extracted_text) > 10000 else doc.extracted_text
                context += f"DOCUMENT {idx}: {doc.title}\n"
                context += f"Type: {doc.document_type}\n"
                context += f"Summary: {doc.summary[:200] if doc.summary else 'N/A'}\n"
                context += f"Content:\n{doc_text}\n\n"
                context += "="*80 + "\n\n"

            # Add conversation history
            if history:
                context += "CONVERSATION HISTORY:\n"
                for msg in history[-10:]:  # Last 10 messages
                    sender = "User" if msg.sender_type == "user" else "Assistant"
                    context += f"{sender}: {msg.content[:300]}\n"
                context += "\n"

            # Build the main prompt
            prompt = f"""{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer using information from ALL relevant documents
2. Be specific and cite your sources using the format [Document Title, Page X]
3. Include direct quotes when helpful, formatted as "quote here" [Document Title, Page X]
4. If documents contain conflicting information, mention both perspectives
5. If the answer is not in the documents, say so clearly
6. Be comprehensive but concise
7. Provide page numbers whenever possible based on [Page X] markers in the text

Your detailed answer:"""

            response = self.model.generate_content(prompt)
            processing_time = time.time() - start_time

            # Extract citations from response
            citations = self._extract_citations(response.text, documents)

            # Estimate confidence (simple heuristic based on citations)
            confidence = min(0.95, 0.6 + (len(citations) * 0.1))

            result = {
                'answer': response.text,
                'citations': citations,
                'confidence_score': confidence,
                'processing_time': processing_time,
                'documents_used': len(documents)
            }

            logger.info(f"Generated answer with {len(citations)} citations in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Error in multi-document chat: {str(e)}")
            raise

    def compare_documents(
        self,
        documents: List,
        comparison_type: str
    ) -> Dict[str, any]:
        """
        Compare multiple documents

        Args:
            documents: List of Document objects
            comparison_type: 'similarities', 'differences', 'timeline', or 'synthesis'

        Returns:
            Dictionary with comparison results
        """
        try:
            # Build context
            doc_summaries = "Documents to compare:\n\n"
            for idx, doc in enumerate(documents, 1):
                text_sample = doc.extracted_text[:5000]
                doc_summaries += f"DOCUMENT {idx}: {doc.title}\n"
                doc_summaries += f"Type: {doc.document_type}\n"
                doc_summaries += f"Summary: {doc.summary}\n"
                doc_summaries += f"Content sample:\n{text_sample}\n\n"
                doc_summaries += "="*80 + "\n\n"

            # Create prompt based on comparison type
            if comparison_type == 'similarities':
                prompt = f"""{doc_summaries}

Analyze these documents and identify KEY SIMILARITIES:
1. Common themes and topics
2. Shared conclusions or findings
3. Similar methodologies or approaches
4. Overlapping information
5. Consistent data or statistics

Provide a detailed analysis with specific examples and page references."""

            elif comparison_type == 'differences':
                prompt = f"""{doc_summaries}

Analyze these documents and identify KEY DIFFERENCES:
1. Contrasting viewpoints or conclusions
2. Different methodologies or approaches
3. Conflicting data or statistics
4. Unique information in each document
5. Varying perspectives on the same topic

Provide a detailed analysis with specific examples and page references."""

            elif comparison_type == 'timeline':
                prompt = f"""{doc_summaries}

Create a CHRONOLOGICAL TIMELINE of events from these documents:
1. Extract all dates and events mentioned
2. Organize them chronologically
3. Note which document each event comes from
4. Identify any date conflicts between documents

Format as a timeline with dates and descriptions."""

            else:  # synthesis
                prompt = f"""{doc_summaries}

Provide a COMPREHENSIVE SYNTHESIS of these documents:
1. Main themes across all documents
2. How the documents relate to each other
3. Comprehensive overview of the topic
4. Key insights from combining the information
5. Any gaps or missing information

Provide a well-structured synthesis."""

            response = self.model.generate_content(prompt)

            return {
                'comparison_type': comparison_type,
                'analysis': response.text,
                'document_count': len(documents),
                'document_titles': [doc.title for doc in documents]
            }

        except Exception as e:
            logger.error(f"Error comparing documents: {str(e)}")
            raise

    def generate_suggested_questions(self, documents: List) -> List[str]:
        """
        Generate smart questions for documents

        Args:
            documents: List of Document objects (can be single or multiple)

        Returns:
            List of suggested questions
        """
        try:
            if len(documents) == 1:
                doc = documents[0]
                text_sample = doc.extracted_text[:3000]

                prompt = f"""Based on this {doc.document_type} document titled "{doc.title}", generate 7 insightful questions that would help someone understand and analyze it.

Document preview:
{text_sample}

Generate varied questions including:
- 1 high-level summary question
- 2 specific detail questions
- 2 analytical questions
- 2 application or implication questions

Return ONLY the questions, one per line, without numbering."""

            else:
                titles = ", ".join([d.title for d in documents])
                types = ", ".join(list(set([d.document_type for d in documents])))

                prompt = f"""Generate 7 insightful questions for analyzing these {len(documents)} documents together:

Documents: {titles}
Types: {types}

Generate questions that:
- Compare and contrast the documents
- Find connections and relationships
- Identify agreements and discrepancies
- Synthesize information across documents
- Analyze implications of combined information

Return ONLY the questions, one per line, without numbering."""

            response = self.model.generate_content(prompt)

            # Parse questions
            questions = [
                q.strip()
                for q in response.text.split('\n')
                if q.strip() and not q.strip().isdigit()
            ]

            # Clean up questions (remove numbering if present)
            questions = [re.sub(r'^\d+[\.\)]\s*', '', q) for q in questions]

            # Return up to 7 questions
            return questions[:7]

        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            # Return default questions
            return [
                "What is the main topic of this document?",
                "What are the key points or findings?",
                "What conclusions are presented?",
                "What evidence or data is provided?",
                "What are the practical implications?",
                "Are there any limitations mentioned?",
                "What questions remain unanswered?"
            ]

    def smart_highlights(self, page_content: str, page_number: int) -> List[Dict[str, str]]:
        """
        Identify key sections to highlight on a page

        Args:
            page_content: Text content of the page
            page_number: Page number

        Returns:
            List of highlights with text and type
        """
        try:
            prompt = f"""Analyze this page from a document and identify the most important sentences or phrases that should be highlighted.

Page {page_number} content:
{page_content[:2000]}

For each highlight, specify:
- The exact text to highlight (keep it concise, 1-2 sentences max)
- Type: key_point, definition, statistic, conclusion, or important

Return as JSON array:
[
    {{"text": "exact text to highlight", "type": "key_point"}},
    {{"text": "another highlight", "type": "definition"}}
]

Limit to 5 most important highlights. Return ONLY valid JSON."""

            response = self.model.generate_content(prompt)

            # Parse response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            highlights = json.loads(response_text.strip())
            return highlights[:5]  # Max 5 highlights per page

        except Exception as e:
            logger.warning(f"Error generating highlights: {str(e)}")
            return []

    def translate_content(self, text: str, target_language: str) -> str:
        """
        Translate document content or AI responses

        Args:
            text: Text to translate
            target_language: Target language (e.g., 'Spanish', 'French')

        Returns:
            Translated text
        """
        try:
            prompt = f"Translate the following text to {target_language}. Maintain the original formatting and structure:\n\n{text}"
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error translating content: {str(e)}")
            return text  # Return original on error

    def _extract_citations(self, response_text: str, documents: List) -> List[Dict[str, any]]:
        """
        Extract citations from AI response

        Args:
            response_text: AI-generated response text
            documents: List of Document objects

        Returns:
            List of citation dictionaries
        """
        citations = []

        # Pattern 1: [Document Title, Page X]
        pattern1 = r'\[(.*?),\s*[Pp]age\s*(\d+)\]'
        matches = re.findall(pattern1, response_text)

        for doc_title, page in matches:
            for doc in documents:
                if doc_title.lower() in doc.title.lower() or doc.title.lower() in doc_title.lower():
                    # Try to extract quote around citation
                    quote = self._extract_quote_near_citation(response_text, doc_title, page)

                    citations.append({
                        'document_id': doc.id,
                        'document_title': doc.title,
                        'page': int(page),
                        'quote': quote
                    })
                    break

        # Pattern 2: "Quote" [Document Title, Page X]
        pattern2 = r'"([^"]+)"\s*\[(.*?),\s*[Pp]age\s*(\d+)\]'
        matches2 = re.findall(pattern2, response_text)

        for quote, doc_title, page in matches2:
            for doc in documents:
                if doc_title.lower() in doc.title.lower() or doc.title.lower() in doc_title.lower():
                    # Check if citation already exists
                    existing = any(
                        c['document_id'] == doc.id and c['page'] == int(page)
                        for c in citations
                    )
                    if not existing:
                        citations.append({
                            'document_id': doc.id,
                            'document_title': doc.title,
                            'page': int(page),
                            'quote': quote
                        })
                    break

        # Remove duplicates
        unique_citations = []
        seen = set()
        for citation in citations:
            key = (citation['document_id'], citation['page'])
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)

        return unique_citations

    def _extract_quote_near_citation(self, text: str, doc_title: str, page: str) -> str:
        """
        Extract quote text near a citation

        Args:
            text: Full response text
            doc_title: Document title from citation
            page: Page number

        Returns:
            Extracted quote or empty string
        """
        try:
            # Look for quoted text before the citation
            pattern = r'"([^"]+)"\s*\[' + re.escape(doc_title)
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        except Exception:
            pass

        return ""
