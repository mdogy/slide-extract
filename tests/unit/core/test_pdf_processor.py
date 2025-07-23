"""Unit tests for the PDF processor module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from slide_extract.core.pdf_processor import PDFProcessor, PDFProcessingError


class TestPDFProcessor:
    """Test cases for PDFProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()

    def test_init(self):
        """Test PDFProcessor initialization."""
        assert self.processor.processed_files == []

    def test_extract_text_from_pdf_file_not_found(self):
        """Test extraction with non-existent file."""
        non_existent_file = Path("/fake/path/file.pdf")

        with pytest.raises(PDFProcessingError, match="PDF file not found"):
            self.processor.extract_text_from_pdf(non_existent_file)

    def test_extract_text_from_pdf_not_pdf_file(self, tmp_path):
        """Test extraction with non-PDF file."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("test content")

        with pytest.raises(PDFProcessingError, match="File is not a PDF"):
            self.processor.extract_text_from_pdf(text_file)

    @patch("slide_extract.pdf_processor.fitz")
    def test_extract_text_from_pdf_success(self, mock_fitz, tmp_path):
        """Test successful PDF text extraction."""
        # Create a mock PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        # Mock the PDF document and pages
        mock_doc = Mock()
        mock_doc.page_count = 2

        mock_page1 = Mock()
        mock_page1.get_text.return_value = "  Page 1 content  \n\n  "

        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Page 2\n\ncontent"

        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
        mock_fitz.open.return_value = mock_doc

        result = self.processor.extract_text_from_pdf(pdf_file)

        # Verify the result
        assert len(result) == 2
        assert result[1] == "Page 1 content"  # Cleaned text
        assert result[2] == "Page 2 content"  # Cleaned text
        assert str(pdf_file) in self.processor.processed_files

        mock_fitz.open.assert_called_once_with(str(pdf_file))
        mock_doc.close.assert_called_once()

    @patch("slide_extract.pdf_processor.fitz")
    def test_extract_text_from_pdf_open_error(self, mock_fitz, tmp_path):
        """Test PDF extraction with file open error."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        mock_fitz.open.side_effect = Exception("Cannot open PDF")

        with pytest.raises(PDFProcessingError, match="Failed to open PDF"):
            self.processor.extract_text_from_pdf(pdf_file)

    @patch("slide_extract.pdf_processor.fitz")
    def test_extract_text_from_pdf_extraction_error(self, mock_fitz, tmp_path):
        """Test PDF extraction with text extraction error."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        mock_doc = Mock()
        mock_doc.page_count = 1
        mock_page = Mock()
        mock_page.get_text.side_effect = Exception("Text extraction failed")
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        with pytest.raises(PDFProcessingError, match="Failed to extract text from PDF"):
            self.processor.extract_text_from_pdf(pdf_file)

        mock_doc.close.assert_called_once()

    def test_process_multiple_pdfs_success(self, tmp_path):
        """Test processing multiple PDFs successfully."""
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        pdf1.touch()
        pdf2.touch()

        # Mock the extract_text_from_pdf method
        with patch.object(self.processor, "extract_text_from_pdf") as mock_extract:
            mock_extract.side_effect = [
                {1: "Content 1", 2: "Content 2"},
                {1: "Content A"},
            ]

            result = self.processor.process_multiple_pdfs([pdf1, pdf2])

            assert len(result) == 2
            assert result[str(pdf1)] == {1: "Content 1", 2: "Content 2"}
            assert result[str(pdf2)] == {1: "Content A"}

            assert mock_extract.call_count == 2

    def test_process_multiple_pdfs_with_error(self, tmp_path):
        """Test processing multiple PDFs with one failing."""
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        pdf1.touch()
        pdf2.touch()

        with patch.object(self.processor, "extract_text_from_pdf") as mock_extract:
            mock_extract.side_effect = [
                {1: "Content 1"},
                PDFProcessingError("Processing failed"),
            ]

            with pytest.raises(PDFProcessingError):
                self.processor.process_multiple_pdfs([pdf1, pdf2])

    def test_clean_text_empty(self):
        """Test text cleaning with empty input."""
        result = PDFProcessor._clean_text("")
        assert result == ""

    def test_clean_text_none(self):
        """Test text cleaning with None input."""
        result = PDFProcessor._clean_text(None)
        assert result == ""

    def test_clean_text_whitespace(self):
        """Test text cleaning with excessive whitespace."""
        input_text = "  Hello   world  \n\n  test  \t  content  "
        expected = "Hello world test content"

        result = PDFProcessor._clean_text(input_text)
        assert result == expected

    def test_clean_text_normal(self):
        """Test text cleaning with normal text."""
        input_text = "Normal text content"
        result = PDFProcessor._clean_text(input_text)
        assert result == input_text

    def test_get_processing_summary_empty(self):
        """Test processing summary with no processed files."""
        summary = self.processor.get_processing_summary()
        assert summary == {"files_processed": 0, "files_list": []}

    def test_get_processing_summary_with_files(self):
        """Test processing summary with processed files."""
        self.processor.processed_files = ["/path/to/file1.pdf", "/path/to/file2.pdf"]

        summary = self.processor.get_processing_summary()
        assert summary == {
            "files_processed": 2,
            "files_list": ["/path/to/file1.pdf", "/path/to/file2.pdf"],
        }

    def test_get_processing_summary_immutable(self):
        """Test that processing summary returns a copy of the files list."""
        self.processor.processed_files = ["/path/to/file.pdf"]
        summary = self.processor.get_processing_summary()

        # Modify the returned list
        summary["files_list"].append("/new/file.pdf")

        # Original should be unchanged
        assert len(self.processor.processed_files) == 1
        assert "/new/file.pdf" not in self.processor.processed_files
