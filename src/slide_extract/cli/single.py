"""Enhanced single file processing CLI with resume capability."""

import argparse
import sys
import logging
from pathlib import Path
from typing import List

from .common import CommonCLI, CLIError
from ..core.pdf_processor import PDFProcessor, PDFProcessingError
from ..core.note_generator import NoteGenerator, NoteGenerationError
from ..core.progress_manager import ProgressManager

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for single file processing."""
    parser = argparse.ArgumentParser(
        description="Generate AI-powered speaker notes from PDF presentation slides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slide-extract -i presentation.pdf -p prompt.md
  slide-extract -i slide1.pdf slide2.pdf -p prompt.md -o notes.md
  slide-extract -i presentation.pdf -p prompt.md -v --resume
        """,
    )

    parser.add_argument(
        "--input", "-i",
        nargs="+",
        required=True,
        help="Path(s) to input PDF slide deck files"
    )

    parser.add_argument(
        "--output", "-o", 
        help="Path to output Markdown file (default: write to stdout)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous interrupted processing"
    )
    
    parser.add_argument(
        "--clean-start",
        action="store_true", 
        help="Ignore any existing progress and start fresh"
    )

    # Add common arguments
    CommonCLI.add_common_arguments(parser)

    return parser.parse_args()

def main() -> int:
    """Enhanced single file processor with resume capability."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set up logging
        log_file = "slide_extract_single.log"
        CommonCLI.setup_logging(args.verbose, log_file)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting enhanced slide extraction process with resume capability")
        logger.debug(f"Arguments: {args}")
        
        # Validate inputs
        pdf_paths = [Path(path) for path in args.input]
        CommonCLI.validate_pdf_files(pdf_paths)
        
        prompt_path = Path(args.prompt)
        output_path = Path(args.output) if args.output else None
        
        # Initialize LLM
        llm_client = CommonCLI.initialize_llm(
            Path(args.config) if args.config else None, 
            args.no_ai
        )
        
        # Load prompt
        prompt_text = CommonCLI.load_and_validate_prompt(prompt_path)
        
        # Initialize processors
        pdf_processor = PDFProcessor()
        note_generator = NoteGenerator(llm_client)
        
        # Process each PDF file
        all_notes = []
        
        for pdf_path in pdf_paths:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Initialize progress manager for this file
            progress_manager = ProgressManager(
                output_path=output_path,
                mode='single',
                file_path=pdf_path
            )
            
            # Clean start if requested
            if args.clean_start:
                progress_manager.cleanup_state()
                logger.info("Starting fresh (clean start requested)")
            
            # Check for resumable work
            start_slide = 1
            if args.resume or progress_manager.has_incomplete_work():
                if progress_manager.has_incomplete_work():
                    start_slide, state = progress_manager.get_resume_point()
                    logger.info(f"Resuming from slide {start_slide} of {pdf_path}")
                else:
                    logger.info("No previous progress found, starting from beginning")
            
            # Get PDF info
            pdf_info = pdf_processor.get_pdf_info(pdf_path)
            logger.info(f"PDF {pdf_path.name}: {pdf_info['page_count']} pages, {pdf_info['total_images']} images")
            
            # Extract slide content with multi-modal support
            logger.info("Extracting slide content with multi-modal analysis")
            slide_contents = pdf_processor.extract_slide_content(pdf_path)
            
            # Add file header
            if len(pdf_paths) > 1:
                header = f"# Notes for {pdf_path.name}\n\n"
                all_notes.append(header)
            
            # Generate notes with resume capability
            logger.info(f"Generating speaker notes with multi-modal analysis (starting from slide {start_slide})")
            slide_notes = note_generator.generate_notes_for_slide_contents_resumable(
                slide_contents, 
                prompt_text,
                progress_manager,
                start_from_slide=start_slide
            )
            
            all_notes.append(slide_notes)
            
            # Clean up progress state on successful completion
            progress_manager.cleanup_state()
            
            logger.info(f"Successfully processed {pdf_path}")
        
        # Combine all notes
        final_notes = "".join(all_notes)
        
        # Output results
        CommonCLI.handle_output(final_notes, output_path)
        
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
        
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Process interrupted by user")
        logger.info("Progress saved. Use --resume flag to continue from where you left off")
        return 130
        
    except (CLIError, PDFProcessingError, NoteGenerationError, FileNotFoundError, ValueError, RuntimeError) as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Application error: {e}")
        return 1
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())