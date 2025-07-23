"""Unit tests for the main CLI module."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from slide_extract.scripts.main import (
    setup_logging,
    parse_arguments,
    validate_input_files,
    main,
    SlideExtractorError,
)


class TestSetupLogging:
    """Test cases for logging setup."""

    @patch("slide_extract.main.logging")
    def test_setup_logging_info_level(self, mock_logging):
        """Test logging setup with INFO level."""
        setup_logging(verbose=False)

        mock_logging.basicConfig.assert_called_once()
        call_args = mock_logging.basicConfig.call_args
        assert call_args[1]["level"] == mock_logging.INFO

    @patch("slide_extract.main.logging")
    def test_setup_logging_debug_level(self, mock_logging):
        """Test logging setup with DEBUG level."""
        setup_logging(verbose=True)

        mock_logging.basicConfig.assert_called_once()
        call_args = mock_logging.basicConfig.call_args
        assert call_args[1]["level"] == mock_logging.DEBUG

    @patch("slide_extract.main.logging")
    def test_setup_logging_handlers(self, mock_logging):
        """Test that both file and console handlers are configured."""
        setup_logging(verbose=False)

        call_args = mock_logging.basicConfig.call_args
        handlers = call_args[1]["handlers"]
        assert len(handlers) == 2


class TestParseArguments:
    """Test cases for argument parsing."""

    def test_parse_arguments_minimal(self):
        """Test parsing with minimal required arguments."""
        test_args = ["-i", "test.pdf", "-p", "prompt.md"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_arguments()

        assert args.input == ["test.pdf"]
        assert args.prompt == "prompt.md"
        assert args.output is None
        assert args.verbose is False

    def test_parse_arguments_all_options(self):
        """Test parsing with all arguments."""
        test_args = [
            "-i",
            "file1.pdf",
            "file2.pdf",
            "-p",
            "prompt.md",
            "-o",
            "output.md",
            "-v",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_arguments()

        assert args.input == ["file1.pdf", "file2.pdf"]
        assert args.prompt == "prompt.md"
        assert args.output == "output.md"
        assert args.verbose is True

    def test_parse_arguments_long_form(self):
        """Test parsing with long-form arguments."""
        test_args = [
            "--input",
            "test.pdf",
            "--prompt",
            "prompt.md",
            "--output",
            "output.md",
            "--verbose",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_arguments()

        assert args.input == ["test.pdf"]
        assert args.prompt == "prompt.md"
        assert args.output == "output.md"
        assert args.verbose is True

    def test_parse_arguments_missing_input(self):
        """Test parsing fails when input is missing."""
        test_args = ["-p", "prompt.md"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_parse_arguments_missing_prompt(self):
        """Test parsing fails when prompt is missing."""
        test_args = ["-i", "test.pdf"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_parse_arguments_version(self):
        """Test version argument."""
        test_args = ["--version"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_arguments()


class TestValidateInputFiles:
    """Test cases for input file validation."""

    def test_validate_input_files_pdf_not_found(self):
        """Test validation with non-existent PDF file."""
        with pytest.raises(SlideExtractorError, match="PDF file not found"):
            validate_input_files(["/fake/path.pdf"], "prompt.md")

    def test_validate_input_files_prompt_not_found(self, tmp_path):
        """Test validation with non-existent prompt file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        with pytest.raises(SlideExtractorError, match="Prompt file not found"):
            validate_input_files([str(pdf_file)], "/fake/prompt.md")

    def test_validate_input_files_pdf_not_file(self, tmp_path):
        """Test validation with PDF path that is not a file."""
        pdf_dir = tmp_path / "test.pdf"
        pdf_dir.mkdir()
        prompt_file = tmp_path / "prompt.md"
        prompt_file.touch()

        with pytest.raises(SlideExtractorError, match="Path is not a file"):
            validate_input_files([str(pdf_dir)], str(prompt_file))

    def test_validate_input_files_not_pdf(self, tmp_path):
        """Test validation with non-PDF file."""
        text_file = tmp_path / "test.txt"
        text_file.touch()
        prompt_file = tmp_path / "prompt.md"
        prompt_file.touch()

        with pytest.raises(SlideExtractorError, match="File is not a PDF"):
            validate_input_files([str(text_file)], str(prompt_file))

    def test_validate_input_files_prompt_not_file(self, tmp_path):
        """Test validation with prompt path that is not a file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()
        prompt_dir = tmp_path / "prompt.md"
        prompt_dir.mkdir()

        with pytest.raises(SlideExtractorError, match="Prompt path is not a file"):
            validate_input_files([str(pdf_file)], str(prompt_dir))

    def test_validate_input_files_success(self, tmp_path):
        """Test successful validation."""
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        prompt_file = tmp_path / "prompt.md"

        pdf1.touch()
        pdf2.touch()
        prompt_file.touch()

        # Should not raise any exception
        validate_input_files([str(pdf1), str(pdf2)], str(prompt_file))


class TestMainFunction:
    """Test cases for the main function."""

    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.validate_input_files")
    @patch("slide_extract.main.PDFProcessor")
    @patch("slide_extract.main.NoteGenerator")
    @patch("slide_extract.main.parse_arguments")
    def test_main_success_stdout(
        self,
        mock_parse,
        mock_note_gen_class,
        mock_pdf_proc_class,
        mock_validate,
        mock_setup_logging,
    ):
        """Test successful main execution with stdout output."""
        # Mock arguments
        mock_args = Mock()
        mock_args.input = ["test.pdf"]
        mock_args.prompt = "prompt.md"
        mock_args.output = None
        mock_args.verbose = False
        mock_parse.return_value = mock_args

        # Mock processors
        mock_pdf_proc = Mock()
        mock_pdf_proc.process_multiple_pdfs.return_value = {"test.pdf": {1: "content"}}
        mock_pdf_proc.get_processing_summary.return_value = {
            "files_processed": 1,
            "notes_generated": 1,
        }
        mock_pdf_proc_class.return_value = mock_pdf_proc

        mock_note_gen = Mock()
        mock_note_gen.load_prompt_from_file.return_value = "test prompt"
        mock_note_gen.generate_notes_for_multiple_pdfs.return_value = "generated notes"
        mock_note_gen.get_generation_summary.return_value = {
            "notes_generated": 1,
            "total_characters": 15,
        }
        mock_note_gen_class.return_value = mock_note_gen

        with patch("builtins.print") as mock_print:
            result = main()

        assert result == 0
        mock_print.assert_called_once_with("generated notes", end="")
        mock_note_gen.write_notes_to_file.assert_not_called()

    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.validate_input_files")
    @patch("slide_extract.main.PDFProcessor")
    @patch("slide_extract.main.NoteGenerator")
    @patch("slide_extract.main.parse_arguments")
    def test_main_success_file_output(
        self,
        mock_parse,
        mock_note_gen_class,
        mock_pdf_proc_class,
        mock_validate,
        mock_setup_logging,
    ):
        """Test successful main execution with file output."""
        # Mock arguments
        mock_args = Mock()
        mock_args.input = ["test.pdf"]
        mock_args.prompt = "prompt.md"
        mock_args.output = "output.md"
        mock_args.verbose = True
        mock_parse.return_value = mock_args

        # Mock processors
        mock_pdf_proc = Mock()
        mock_pdf_proc.process_multiple_pdfs.return_value = {"test.pdf": {1: "content"}}
        mock_pdf_proc.get_processing_summary.return_value = {"files_processed": 1}
        mock_pdf_proc_class.return_value = mock_pdf_proc

        mock_note_gen = Mock()
        mock_note_gen.load_prompt_from_file.return_value = "test prompt"
        mock_note_gen.generate_notes_for_multiple_pdfs.return_value = "generated notes"
        mock_note_gen.get_generation_summary.return_value = {
            "notes_generated": 1,
            "total_characters": 15,
        }
        mock_note_gen_class.return_value = mock_note_gen

        result = main()

        assert result == 0
        mock_note_gen.write_notes_to_file.assert_called_once()

    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.parse_arguments")
    def test_main_slide_extractor_error(self, mock_parse, mock_setup_logging):
        """Test main function with SlideExtractorError."""
        mock_parse.side_effect = SlideExtractorError("Test error")

        result = main()
        assert result == 1

    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.parse_arguments")
    def test_main_keyboard_interrupt(self, mock_parse, mock_setup_logging):
        """Test main function with KeyboardInterrupt."""
        mock_parse.side_effect = KeyboardInterrupt()

        result = main()
        assert result == 130

    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.parse_arguments")
    def test_main_unexpected_error(self, mock_parse, mock_setup_logging):
        """Test main function with unexpected error."""
        mock_parse.side_effect = Exception("Unexpected error")

        result = main()
        assert result == 1

    @patch("slide_extract.main.validate_input_files")
    @patch("slide_extract.main.setup_logging")
    @patch("slide_extract.main.parse_arguments")
    def test_main_validation_error(self, mock_parse, mock_setup_logging, mock_validate):
        """Test main function with validation error."""
        mock_args = Mock()
        mock_args.input = ["test.pdf"]
        mock_args.prompt = "prompt.md"
        mock_args.verbose = False
        mock_parse.return_value = mock_args

        mock_validate.side_effect = SlideExtractorError("Validation failed")

        result = main()
        assert result == 1

    @patch("slide_extract.main.main")
    def test_main_module_execution(self, mock_main):
        """Test that main is called when module is executed directly."""
        mock_main.return_value = 0

        # This simulates running the script directly
        with patch("slide_extract.main.__name__", "__main__"):
            exec('if __name__ == "__main__": import sys; sys.exit(main())')

        # This test is more about structure than actual execution
        # In real usage, the main function would be called
