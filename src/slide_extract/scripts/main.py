#!/usr/bin/env python3
"""
AI-Powered Presentation Note Generation CLI Script

This script processes PDF presentation slides and generates speaker notes
using user-provided prompts.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

try:
    # When run as a module
    from ..core.pdf_processor import PDFProcessor, PDFProcessingError
    from ..core.note_generator import NoteGenerator, NoteGenerationError
    from ..core.config_manager import ConfigManager, ConfigurationError
    from ..core.llm_client import create_llm_client, LLMError
except ImportError:
    # When run directly
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent.parent / "core"))
    from pdf_processor import PDFProcessor, PDFProcessingError
    from note_generator import NoteGenerator, NoteGenerationError
    from config_manager import ConfigManager, ConfigurationError
    from llm_client import create_llm_client, LLMError


class SlideExtractorError(Exception):
    """Custom exception for general application errors."""


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration for the application.

    Args:
        verbose: If True, set logging level to DEBUG, otherwise INFO
    """
    # Configure file logging
    file_handler = logging.FileHandler("script_run.log")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Configure console logging (to stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # Set logging level based on verbose flag
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level, handlers=[file_handler, console_handler], force=True
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {log_level} level")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate AI-powered speaker notes from PDF presentation slides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slide-extract -i presentation.pdf -p prompt.md
  slide-extract -i slide1.pdf slide2.pdf -p prompt.md -o notes.md
  slide-extract -i presentation.pdf -p prompt.md -v -o output.md
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        required=True,
        help="Path(s) to input PDF slide deck files",
    )

    parser.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="Path to Markdown file containing the generation prompt",
    )

    parser.add_argument(
        "--output", "-o", help="Path to output Markdown file (default: write to stdout)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    parser.add_argument(
        "--config", "-c", help="Path to configuration file (default: config.yaml)"
    )

    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use placeholder mode without AI (for testing)",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    return parser.parse_args()


def validate_input_files(pdf_paths: List[str], prompt_path: str) -> None:
    """
    Validate that all input files exist and are accessible.

    Args:
        pdf_paths: List of PDF file paths
        prompt_path: Path to prompt file

    Raises:
        SlideExtractorError: If any file is invalid or inaccessible
    """
    logger = logging.getLogger(__name__)

    # Validate PDF files
    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        if not path.exists():
            raise SlideExtractorError(f"PDF file not found: {pdf_path}")
        if not path.is_file():
            raise SlideExtractorError(f"Path is not a file: {pdf_path}")
        if not path.suffix.lower() == ".pdf":
            raise SlideExtractorError(f"File is not a PDF: {pdf_path}")

    # Validate prompt file
    prompt_file = Path(prompt_path)
    if not prompt_file.exists():
        raise SlideExtractorError(f"Prompt file not found: {prompt_path}")
    if not prompt_file.is_file():
        raise SlideExtractorError(f"Prompt path is not a file: {prompt_path}")

    logger.info(f"Validated {len(pdf_paths)} PDF files and prompt file")


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Set up logging
        setup_logging(args.verbose)
        logger = logging.getLogger(__name__)

        logger.info("Starting slide extraction process")
        logger.debug(f"Arguments: {args}")

        # Validate input files
        validate_input_files(args.input, args.prompt)

        # Convert string paths to Path objects
        pdf_paths = [Path(path) for path in args.input]
        prompt_path = Path(args.prompt)
        output_path = Path(args.output) if args.output else None

        # Initialize configuration
        config_manager = ConfigManager(Path(args.config) if args.config else None)

        # Initialize LLM client if not in no-ai mode
        llm_client = None
        if not args.no_ai:
            try:
                llm_config = config_manager.get_llm_config()
                llm_client = create_llm_client(llm_config)

                # Test connection
                logger.info("Testing LLM connection...")
                if llm_client.test_connection():
                    model_info = llm_client.get_model_info()
                    logger.info(
                        "LLM connection successful: %s %s",
                        model_info["provider"],
                        model_info["model"],
                    )
                else:
                    logger.error("LLM connection test failed")
                    raise SlideExtractorError(
                        "No LLM/AI has been configured or connection failed. "
                        "Either run with --no-ai flag to use placeholders, or "
                        "follow the README instructions to set up an LLM API key."
                    )

            except (ConfigurationError, LLMError) as e:
                logger.error("LLM initialization failed: %s", e)
                raise SlideExtractorError(
                    "No LLM/AI has been configured. "
                    "Either run with --no-ai flag to use placeholders, or "
                    "follow the README instructions to set up an LLM API key."
                ) from e
        else:
            logger.info("Running in no-AI mode (placeholder only)")

        # Initialize processors
        pdf_processor = PDFProcessor()
        note_generator = NoteGenerator(llm_client)

        # Load the user prompt
        logger.info("Loading user prompt")
        prompt_text = note_generator.load_prompt_from_file(prompt_path)

        # Process PDF files with multi-modal support
        logger.info(f"Processing {len(pdf_paths)} PDF files with multi-modal analysis")
        
        all_slide_contents = {}
        for pdf_path in pdf_paths:
            # Get PDF info first
            pdf_info = pdf_processor.get_pdf_info(pdf_path)
            logger.info(f"PDF {pdf_path.name}: {pdf_info['page_count']} pages, {pdf_info['total_images']} images")
            
            # Extract slide content with multi-modal support
            slide_contents = pdf_processor.extract_slide_content(pdf_path)
            all_slide_contents[str(pdf_path)] = slide_contents

        # Generate notes using multi-modal content
        logger.info("Generating speaker notes with multi-modal analysis")
        all_notes = []
        
        for pdf_path_str, slide_contents in all_slide_contents.items():
            pdf_name = Path(pdf_path_str).name
            header = f"# Notes for {pdf_name}\n\n"
            all_notes.append(header)
            
            # Generate notes for each slide with multi-modal support
            slide_notes = note_generator.generate_notes_for_slide_contents(slide_contents, prompt_text)
            all_notes.append(slide_notes)
        
        notes = "".join(all_notes)

        # Output results
        if output_path:
            note_generator.write_notes_to_file(notes, output_path)
            logger.info(f"Notes written to {output_path}")
        else:
            # Write to stdout (not using logger for actual output)
            print(notes, end="")
            logger.info("Notes written to stdout")

        # Log summary
        pdf_summary = pdf_processor.get_processing_summary()
        note_summary = note_generator.get_generation_summary()

        logger.info(
            f"Processing complete: "
            f"{pdf_summary['files_processed']} files, "
            f"{note_summary['notes_generated']} notes generated, "
            f"{note_summary['total_characters']} characters"
        )

        return 0

    except (
        SlideExtractorError,
        PDFProcessingError,
        NoteGenerationError,
        ConfigurationError,
        LLMError,
    ) as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Application error: {e}")
        return 1

    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Process interrupted by user")
        return 130

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
