"""Unit tests for the note generator module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from slide_extract.core.note_generator import NoteGenerator, NoteGenerationError


class TestNoteGenerator:
    """Test cases for NoteGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = NoteGenerator()

    def test_init(self):
        """Test NoteGenerator initialization."""
        assert self.generator.generated_notes == []

    def test_load_prompt_from_file_not_found(self):
        """Test loading prompt from non-existent file."""
        non_existent_file = Path("/fake/path/prompt.md")

        with pytest.raises(NoteGenerationError, match="Prompt file not found"):
            self.generator.load_prompt_from_file(non_existent_file)

    def test_load_prompt_from_file_empty(self, tmp_path):
        """Test loading empty prompt file."""
        prompt_file = tmp_path / "empty.md"
        prompt_file.write_text("")

        with pytest.raises(NoteGenerationError, match="Prompt file is empty"):
            self.generator.load_prompt_from_file(prompt_file)

    def test_load_prompt_from_file_whitespace_only(self, tmp_path):
        """Test loading prompt file with only whitespace."""
        prompt_file = tmp_path / "whitespace.md"
        prompt_file.write_text("   \n\t  \n  ")

        with pytest.raises(NoteGenerationError, match="Prompt file is empty"):
            self.generator.load_prompt_from_file(prompt_file)

    def test_load_prompt_from_file_success(self, tmp_path):
        """Test successful prompt loading."""
        prompt_file = tmp_path / "prompt.md"
        content = "This is a test prompt for generating notes."
        prompt_file.write_text(f"  {content}  \n")

        result = self.generator.load_prompt_from_file(prompt_file)
        assert result == content

    def test_load_prompt_from_file_non_markdown(self, tmp_path):
        """Test loading prompt from non-markdown file (should work with warning)."""
        prompt_file = tmp_path / "prompt.txt"
        content = "This is a test prompt."
        prompt_file.write_text(content)

        with patch("slide_extract.note_generator.logger") as mock_logger:
            result = self.generator.load_prompt_from_file(prompt_file)
            assert result == content
            mock_logger.warning.assert_called_once()

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_load_prompt_from_file_io_error(self, mock_file, tmp_path):
        """Test loading prompt with IO error."""
        prompt_file = tmp_path / "prompt.md"

        with pytest.raises(NoteGenerationError, match="Failed to read prompt file"):
            self.generator.load_prompt_from_file(prompt_file)

    def test_generate_notes_for_slide(self):
        """Test note generation for a single slide."""
        slide_number = 1
        slide_text = "This is slide content"
        prompt = "Generate comprehensive notes"

        result = self.generator.generate_notes_for_slide(
            slide_number, slide_text, prompt
        )

        expected = (
            "--- SLIDE 1 NOTES ---\n"
            "PROMPT: Generate comprehensive notes\n\n"
            "SLIDE CONTENT: This is slide content\n"
            "--- END NOTES ---\n\n"
        )

        assert result == expected
        assert len(self.generator.generated_notes) == 1
        assert self.generator.generated_notes[0] == expected

    def test_generate_notes_for_slide_multiple(self):
        """Test generating notes for multiple slides."""
        # First slide
        result1 = self.generator.generate_notes_for_slide(1, "Content 1", "Prompt")
        # Second slide
        result2 = self.generator.generate_notes_for_slide(2, "Content 2", "Prompt")

        assert len(self.generator.generated_notes) == 2
        assert "SLIDE 1 NOTES" in result1
        assert "SLIDE 2 NOTES" in result2

    def test_generate_notes_for_pdf(self):
        """Test generating notes for a complete PDF."""
        pdf_path = "/path/to/test.pdf"
        page_texts = {
            1: "First slide content",
            2: "Second slide content",
            3: "Third slide content",
        }
        prompt = "Create detailed notes"

        result = self.generator.generate_notes_for_pdf(pdf_path, page_texts, prompt)

        assert len(result) == 4  # Header + 3 slides
        assert "# Notes for test.pdf" in result[0]
        assert "SLIDE 1 NOTES" in result[1]
        assert "SLIDE 2 NOTES" in result[2]
        assert "SLIDE 3 NOTES" in result[3]

    def test_generate_notes_for_pdf_empty(self):
        """Test generating notes for PDF with no pages."""
        pdf_path = "/path/to/empty.pdf"
        page_texts = {}
        prompt = "Create notes"

        result = self.generator.generate_notes_for_pdf(pdf_path, page_texts, prompt)

        assert len(result) == 1  # Only header
        assert "# Notes for empty.pdf" in result[0]

    def test_generate_notes_for_multiple_pdfs(self):
        """Test generating notes for multiple PDFs."""
        pdf_data = {
            "/path/to/pdf1.pdf": {1: "PDF1 Content 1", 2: "PDF1 Content 2"},
            "/path/to/pdf2.pdf": {1: "PDF2 Content 1"},
        }
        prompt = "Generate notes"

        result = self.generator.generate_notes_for_multiple_pdfs(pdf_data, prompt)

        # Should contain content for both PDFs
        assert "# Notes for pdf1.pdf" in result
        assert "# Notes for pdf2.pdf" in result
        assert "SLIDE 1 NOTES" in result
        assert "SLIDE 2 NOTES" in result
        assert len(result) > 0

    def test_generate_notes_for_multiple_pdfs_empty(self):
        """Test generating notes for no PDFs."""
        pdf_data = {}
        prompt = "Generate notes"

        result = self.generator.generate_notes_for_multiple_pdfs(pdf_data, prompt)
        assert result == ""

    def test_write_notes_to_file_success(self, tmp_path):
        """Test successful note writing to file."""
        output_file = tmp_path / "output.md"
        notes = "This is test content\nWith multiple lines"

        self.generator.write_notes_to_file(notes, output_file)

        # Verify file was written
        assert output_file.exists()
        assert output_file.read_text() == notes

    def test_write_notes_to_file_create_directory(self, tmp_path):
        """Test note writing creates parent directories."""
        output_file = tmp_path / "subdir" / "output.md"
        notes = "Test content"

        self.generator.write_notes_to_file(notes, output_file)

        assert output_file.exists()
        assert output_file.read_text() == notes

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_write_notes_to_file_io_error(self, mock_open, tmp_path):
        """Test note writing with IO error."""
        output_file = tmp_path / "output.md"
        notes = "Test content"

        with pytest.raises(NoteGenerationError, match="Failed to write notes"):
            self.generator.write_notes_to_file(notes, output_file)

    def test_get_generation_summary_empty(self):
        """Test generation summary with no notes."""
        summary = self.generator.get_generation_summary()
        assert summary == {"notes_generated": 0, "total_characters": 0}

    def test_get_generation_summary_with_notes(self):
        """Test generation summary with generated notes."""
        # Generate some notes
        self.generator.generate_notes_for_slide(1, "Content 1", "Prompt")
        self.generator.generate_notes_for_slide(2, "Content 2", "Prompt")

        summary = self.generator.get_generation_summary()

        assert summary["notes_generated"] == 2
        assert summary["total_characters"] > 0
        assert isinstance(summary["total_characters"], int)

    def test_generate_notes_for_slide_with_special_characters(self):
        """Test note generation with special characters in content."""
        slide_number = 1
        slide_text = 'Content with émojis 🎉 and special chars: <>"&'
        prompt = 'Prompt with special chars: <>"&'

        result = self.generator.generate_notes_for_slide(
            slide_number, slide_text, prompt
        )

        assert slide_text in result
        assert prompt in result
        assert "SLIDE 1 NOTES" in result

    def test_generate_notes_for_slide_with_long_content(self):
        """Test note generation with very long content."""
        slide_number = 999
        slide_text = "A" * 10000  # Very long content
        prompt = "B" * 5000  # Very long prompt

        result = self.generator.generate_notes_for_slide(
            slide_number, slide_text, prompt
        )

        assert "SLIDE 999 NOTES" in result
        assert slide_text in result
        assert prompt in result
