"""Batch directory processing CLI with comprehensive manifest tracking."""

import argparse
import sys
import logging
from pathlib import Path

from .common import CommonCLI, CLIError
from ..core.batch_processor import BatchProcessor, BatchProcessingError

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for batch directory processing."""
    parser = argparse.ArgumentParser(
        description="Batch process PDF presentations in a directory with resume capability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slide-dir-extract -i ./presentations -p prompt.md
  slide-dir-extract -i ./pdfs -p prompt.md -o ./outputs --suffix "_notes"
  slide-dir-extract -i ./presentations -p prompt.md --resume
  slide-dir-extract -i ./presentations -p prompt.md --clean-start
        """,
    )

    parser.add_argument(
        "--input-dir", "-i",
        required=True,
        help="Directory containing PDF presentation files"
    )

    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for generated files (default: current directory)"
    )
    
    parser.add_argument(
        "--suffix",
        default="_summary",
        help="Output filename suffix (default: '_summary')"
    )
    
    parser.add_argument(
        "--extension",
        default=".md",
        help="Output file extension (default: '.md')"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous interrupted batch processing (default: auto-detect)"
    )
    
    parser.add_argument(
        "--clean-start",
        action="store_true",
        help="Ignore existing progress and start fresh"
    )
    
    parser.add_argument(
        "--show-status",
        action="store_true",
        help="Show current processing status and exit"
    )

    # Add common arguments
    CommonCLI.add_common_arguments(parser)

    return parser.parse_args()

def main() -> int:
    """Batch directory processor with manifest-based resume capability."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set up logging
        log_file = "slide_extract_batch.log"
        CommonCLI.setup_logging(args.verbose, log_file)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting batch directory processing with resume capability")
        logger.debug(f"Arguments: {args}")
        
        # Validate directories
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
        
        CommonCLI.validate_directory(input_dir)
        CommonCLI.validate_directory(output_dir, create_if_missing=True)
        
        # Initialize batch processor
        try:
            batch_processor = BatchProcessor(
                input_dir=input_dir,
                output_dir=output_dir,
                suffix=args.suffix,
                extension=args.extension
            )
        except BatchProcessingError as e:
            raise CLIError(str(e))
        
        # Show status if requested
        if args.show_status:
            status_summary = batch_processor.get_status_summary()
            print(f"Batch Processing Status for {output_dir}:")
            print(f"  Input Directory: {status_summary['input_directory']}")
            print(f"  Output Directory: {status_summary['output_directory']}")
            print(f"  Naming Pattern: {status_summary['naming_pattern']}")
            print(f"  Progress: {status_summary['progress_percent']:.1f}%")
            print()
            for status, count in status_summary['status_counts'].items():
                if count > 0:
                    print(f"  {status}: {count}")
            
            if status_summary['error_files']:
                print(f"\nFiles with errors:")
                for error_file in status_summary['error_files']:
                    print(f"  - {error_file}")
            
            return 0
        
        # Load prompt
        prompt_path = Path(args.prompt)
        prompt_text = CommonCLI.load_and_validate_prompt(prompt_path)
        
        # Initialize LLM (unless no-ai mode)
        llm_client = CommonCLI.initialize_llm(
            Path(args.config) if args.config else None,
            args.no_ai
        )
        
        # Process directory
        logger.info(f"Processing directory: {input_dir} -> {output_dir}")
        logger.info(f"Output naming: [filename]{args.suffix}{args.extension}")
        
        result = batch_processor.process_directory(
            llm_client=llm_client,
            prompt=prompt_text,
            resume=args.resume,
            clean_start=args.clean_start
        )
        
        # Final status summary
        final_summary = batch_processor.get_status_summary()
        logger.info("Batch processing completed")
        logger.info(f"Final status: {final_summary['status_counts']}")
        
        # Print summary to console
        print(f"\nBatch Processing Summary:")
        print(f"Input Directory: {input_dir}")
        print(f"Output Directory: {output_dir}")
        print(f"Progress: {final_summary['progress_percent']:.1f}%")
        for status, count in final_summary['status_counts'].items():
            if count > 0:
                print(f"  {status}: {count}")
        
        if final_summary['error_files']:
            print(f"\nFiles with errors:")
            for error_file in final_summary['error_files']:
                print(f"  - {error_file}")
        
        return result
        
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Batch processing interrupted by user")
        logger.info("Progress saved in manifest. Use --resume to continue from where you left off")
        return 130
        
    except (CLIError, BatchProcessingError, FileNotFoundError, ValueError, RuntimeError) as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Batch processing error: {e}")
        return 1
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error during batch processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())