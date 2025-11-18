"""
Utility functions for PDF processing and text extraction
"""

import PyPDF2
import re
from typing import Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_file) -> Tuple[str, int]:
    """
    Extract text from uploaded PDF file with page markers

    Args:
        pdf_file: Django UploadedFile object or file path

    Returns:
        Tuple of (full_text, page_count)
        full_text includes page markers like [Page 1], [Page 2] etc.
    """
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text_by_page = []

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
                if text.strip():  # Only add non-empty pages
                    text_by_page.append({
                        'page': page_num,
                        'text': text.strip()
                    })
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                text_by_page.append({
                    'page': page_num,
                    'text': f"[Error extracting text from page {page_num}]"
                })

        # Combine all pages with page markers
        full_text = '\n\n'.join([
            f"[Page {p['page']}]\n{p['text']}"
            for p in text_by_page
        ])

        page_count = len(reader.pages)

        logger.info(f"Successfully extracted text from {page_count} pages")
        return full_text, page_count

    except Exception as e:
        logger.error(f"Error reading PDF file: {str(e)}")
        raise ValueError(f"Failed to process PDF file: {str(e)}")


def extract_text_by_page(pdf_file) -> List[Dict[str, any]]:
    """
    Extract text from PDF and return as a list of pages

    Args:
        pdf_file: Django UploadedFile object or file path

    Returns:
        List of dicts with page number and text
        Example: [{'page': 1, 'text': '...'}, {'page': 2, 'text': '...'}]
    """
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        pages = []

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
                pages.append({
                    'page': page_num,
                    'text': text.strip() if text else ''
                })
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                pages.append({
                    'page': page_num,
                    'text': '',
                    'error': str(e)
                })

        return pages

    except Exception as e:
        logger.error(f"Error reading PDF file: {str(e)}")
        raise ValueError(f"Failed to process PDF file: {str(e)}")


def detect_if_scanned(pdf_file, sample_pages: int = 3) -> bool:
    """
    Detect if PDF is scanned (image-based) and needs OCR

    Args:
        pdf_file: Django UploadedFile object or file path
        sample_pages: Number of pages to sample for detection

    Returns:
        True if OCR is likely needed, False otherwise
    """
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(reader.pages)

        # Sample first few pages
        pages_to_check = min(sample_pages, total_pages)
        text_found = 0

        for i in range(pages_to_check):
            text = reader.pages[i].extract_text()
            if text and len(text.strip()) > 50:  # At least 50 characters
                text_found += 1

        # If less than half of sampled pages have text, likely scanned
        ocr_needed = text_found < (pages_to_check / 2)

        logger.info(f"PDF scan detection: {text_found}/{pages_to_check} pages with text. OCR needed: {ocr_needed}")
        return ocr_needed

    except Exception as e:
        logger.warning(f"Error detecting scan status: {str(e)}")
        return False  # Default to no OCR


def extract_page_text(pdf_file, page_number: int) -> str:
    """
    Extract text from a specific page

    Args:
        pdf_file: Django UploadedFile object or file path
        page_number: Page number (1-indexed)

    Returns:
        Text content of the page
    """
    try:
        reader = PyPDF2.PdfReader(pdf_file)

        if page_number < 1 or page_number > len(reader.pages):
            raise ValueError(f"Page number {page_number} out of range (1-{len(reader.pages)})")

        page = reader.pages[page_number - 1]  # Convert to 0-indexed
        text = page.extract_text()

        return text.strip() if text else ''

    except Exception as e:
        logger.error(f"Error extracting text from page {page_number}: {str(e)}")
        raise ValueError(f"Failed to extract page text: {str(e)}")


def extract_metadata(pdf_file) -> Dict[str, any]:
    """
    Extract PDF metadata

    Args:
        pdf_file: Django UploadedFile object or file path

    Returns:
        Dictionary with metadata (title, author, subject, etc.)
    """
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        metadata = reader.metadata

        return {
            'title': metadata.get('/Title', '') if metadata else '',
            'author': metadata.get('/Author', '') if metadata else '',
            'subject': metadata.get('/Subject', '') if metadata else '',
            'creator': metadata.get('/Creator', '') if metadata else '',
            'producer': metadata.get('/Producer', '') if metadata else '',
            'creation_date': metadata.get('/CreationDate', '') if metadata else '',
            'page_count': len(reader.pages)
        }

    except Exception as e:
        logger.warning(f"Error extracting metadata: {str(e)}")
        return {}


def clean_extracted_text(text: str) -> str:
    """
    Clean and normalize extracted text

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\"\'\/]', '', text)

    # Normalize line breaks
    text = re.sub(r'\n+', '\n', text)

    return text.strip()


def get_file_size(file_obj) -> int:
    """
    Get file size in bytes

    Args:
        file_obj: Django UploadedFile object

    Returns:
        Size in bytes
    """
    try:
        file_obj.seek(0, 2)  # Seek to end
        size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        return size
    except Exception as e:
        logger.warning(f"Error getting file size: {str(e)}")
        return 0


def validate_pdf(file_obj, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Validate PDF file

    Args:
        file_obj: Django UploadedFile object
        max_size_mb: Maximum allowed file size in MB

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    if not file_obj.name.lower().endswith('.pdf'):
        return False, "File must be a PDF"

    # Check file size
    size = get_file_size(file_obj)
    max_size_bytes = max_size_mb * 1024 * 1024

    if size > max_size_bytes:
        return False, f"File size exceeds {max_size_mb}MB limit"

    # Try to read PDF
    try:
        reader = PyPDF2.PdfReader(file_obj)
        page_count = len(reader.pages)

        if page_count == 0:
            return False, "PDF file contains no pages"

        if page_count > 1000:
            return False, "PDF file has too many pages (max 1000)"

        file_obj.seek(0)  # Reset file pointer
        return True, ""

    except Exception as e:
        return False, f"Invalid PDF file: {str(e)}"
