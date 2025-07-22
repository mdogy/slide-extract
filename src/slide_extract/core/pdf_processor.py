"""PDF processing module for extracting text from presentation slides."""

import logging
from pathlib import Path
from typing import Dict, List

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        "PyMuPDF is required for PDF processing. "
        "Install it with: pip install PyMuPDF"
    ) from e


logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""


class PDFProcessor:
    """Handles extraction of text content from PDF files."""

    def __init__(self):
        """Initialize the PDF processor."""
        self.processed_files: List[str] = []

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from each page of a PDF file.

        Args:
            pdf_path: Path to the PDF file to process

        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text

        Raises:
            PDFProcessingError: If PDF cannot be opened or processed
        """
        if not pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {pdf_path}")

        logger.info("Processing PDF: %s", pdf_path)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as open_error:
            raise PDFProcessingError(
                f"Failed to open PDF {pdf_path}: {str(open_error)}"
            ) from open_error

        page_texts = {}

        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()

                # Clean up the text
                text = self._clean_text(text)

                page_texts[page_num + 1] = text  # 1-indexed page numbers
                logger.debug(
                    "Extracted %d characters from page %d", len(text), page_num + 1
                )

        except Exception as extraction_error:
            raise PDFProcessingError(
                f"Failed to extract text from PDF {pdf_path}: {str(extraction_error)}"
            ) from extraction_error
        finally:
            doc.close()

        self.processed_files.append(str(pdf_path))
        logger.info(
            "Successfully processed %d pages from %s", len(page_texts), pdf_path
        )

        return page_texts

    def process_multiple_pdfs(self, pdf_paths: List[Path]) -> Dict[str, Dict[int, str]]:
        """
        Process multiple PDF files and extract text from all pages.

        Args:
            pdf_paths: List of paths to PDF files

        Returns:
            Dictionary mapping file paths to page dictionaries

        Raises:
            PDFProcessingError: If any PDF cannot be processed
        """
        results = {}

        for pdf_path in pdf_paths:
            try:
                page_texts = self.extract_text_from_pdf(pdf_path)
                results[str(pdf_path)] = page_texts
            except PDFProcessingError:
                logger.error("Failed to process PDF: %s", pdf_path)
                raise

        logger.info("Successfully processed %d PDF files", len(results))
        return results

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and normalizing.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        import re

        if not text:
            return ""

        # Replace multiple whitespace characters with single spaces

        text = re.sub(r"\s+", " ", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def get_processing_summary(self) -> Dict[str, int]:
        """
        Get a summary of processing results.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "files_processed": len(self.processed_files),
            "files_list": self.processed_files.copy(),
        }
