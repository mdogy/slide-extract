"""Batch directory processing with comprehensive resume capability."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from .manifest_manager import ManifestManager, FileStatus, FileRecord
from .progress_manager import ProgressManager
from .file_manager import FileManager, FileManagerError
from .pdf_processor import PDFProcessor, PDFProcessingError
from .note_generator import NoteGenerator, NoteGenerationError

class BatchProcessingError(Exception):
    """Custom exception for batch processing errors."""
    pass

class BatchProcessor:
    """Handles batch directory processing with manifest-based resume capability."""
    
    def __init__(
        self, 
        input_dir: Path, 
        output_dir: Path, 
        suffix: str = "_summary", 
        extension: str = ".md"
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.suffix = suffix
        self.extension = extension
        
        # Initialize managers
        self.manifest = ManifestManager(output_dir, suffix, extension)
        self.file_manager = FileManager()
        self.logger = logging.getLogger(__name__)
        
        # Validate directories
        if not self.input_dir.exists():
            raise BatchProcessingError(f"Input directory does not exist: {input_dir}")
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def discover_pdfs(self) -> List[Path]:
        """Discover all PDF files in input directory."""
        try:
            return self.file_manager.discover_pdf_files(self.input_dir)
        except FileManagerError as e:
            raise BatchProcessingError(f"Failed to discover PDF files: {e}")
    
    def process_directory(
        self, 
        llm_client, 
        prompt: str, 
        resume: bool = True,
        clean_start: bool = False
    ) -> int:
        """
        Process all PDFs in directory with comprehensive resume capability.
        
        Args:
            llm_client: LLM client for analysis
            prompt: Analysis prompt text
            resume: Whether to resume from existing progress
            clean_start: Force clean start, ignore existing progress
            
        Returns:
            Exit code (0 for success)
        """
        start_time = datetime.now()
        
        # Clean start if requested
        if clean_start:
            self.manifest.cleanup_manifest()
            self.logger.info("Starting fresh (clean start requested)")
        
        # Discover PDF files
        pdf_files = self.discover_pdfs()
        if not pdf_files:
            self.logger.error("No PDF files found to process")
            return 1
        
        # Initialize or load manifest
        existing_records = self.manifest.load_manifest() if resume else []
        
        if not existing_records:
            # Create new manifest
            command_args = f"slide-dir-extract -i {self.input_dir} -o {self.output_dir} --suffix {self.suffix}"
            self.manifest.initialize_manifest(pdf_files, command_args)
            self.logger.info(f"Initialized new batch processing for {len(pdf_files)} files")
        else:
            # Resume existing batch
            self.logger.info(f"Resuming batch processing from existing manifest")
            
            # Detect file changes
            changed_files = self.manifest.detect_file_changes(self.input_dir)
            if changed_files:
                self.logger.warning(f"Detected changes in {len(changed_files)} files since last run")
                # Could implement logic to re-process changed files
        
        # Get processing status
        summary = self.manifest.get_processing_summary()
        self.logger.info(f"Processing summary: {summary}")
        
        # Process files that need processing
        files_to_process = self.manifest.get_files_by_status(FileStatus.PENDING)
        files_with_errors = self.manifest.get_files_by_status(FileStatus.ERROR)
        
        # Ask user about error files if any
        if files_with_errors and resume:
            self.logger.info(f"Found {len(files_with_errors)} files with previous errors")
            # For now, skip error files - could implement retry logic
        
        total_to_process = len(files_to_process)
        if total_to_process == 0:
            self.logger.info("All files already processed successfully")
            return 0
        
        self.logger.info(f"Processing {total_to_process} files...")
        
        # Initialize processors
        pdf_processor = PDFProcessor()
        note_generator = NoteGenerator(llm_client)
        
        success_count = 0
        error_count = 0
        
        try:
            for i, record in enumerate(files_to_process, 1):
                self.logger.info(f"Processing {i}/{total_to_process}: {record.filename}")
                
                try:
                    success = self._process_single_file(
                        record, pdf_processor, note_generator, prompt
                    )
                    
                    if success:
                        success_count += 1
                        self.logger.info(f"✓ Completed {record.filename}")
                    else:
                        error_count += 1
                        self.logger.error(f"✗ Failed {record.filename}")
                
                except KeyboardInterrupt:
                    self.logger.info("Batch processing interrupted by user")
                    self.logger.info(f"Progress saved. Resume with same command to continue.")
                    return 130  # Standard exit code for SIGINT
                
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"✗ Critical error processing {record.filename}: {e}")
                    self.manifest.update_file_status(
                        record.filename, 
                        FileStatus.ERROR,
                        error_message=str(e)
                    )
        
        finally:
            # Final summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info(f"Batch processing completed in {duration}")
            self.logger.info(f"Successfully processed: {success_count}")
            self.logger.info(f"Errors: {error_count}")
            
            # Final status summary
            final_summary = self.manifest.get_processing_summary()
            self.logger.info(f"Final status: {final_summary}")
        
        return 0 if error_count == 0 else 1
    
    def _process_single_file(
        self, 
        record: FileRecord, 
        pdf_processor: PDFProcessor, 
        note_generator: NoteGenerator, 
        prompt: str
    ) -> bool:
        """
        Process a single PDF file with progress tracking.
        
        Returns:
            True if successful, False if failed
        """
        input_path = Path(record.input_path)
        output_path = Path(record.output_path)
        
        try:
            # Mark as in progress
            self.manifest.update_file_status(
                record.filename, 
                FileStatus.IN_PROGRESS,
                start_time=datetime.now()
            )
            
            # Extract PDF content
            self.logger.debug(f"Extracting content from {input_path}")
            slide_contents = pdf_processor.extract_slide_content(input_path)
            
            # Update total slides count
            total_slides = len(slide_contents)
            self.manifest.update_file_status(
                record.filename,
                FileStatus.IN_PROGRESS,
                total_slides=total_slides
            )
            
            # Set up progress manager for this file
            progress_manager = ProgressManager(
                output_path=output_path,
                mode='batch',
                file_path=input_path
            )
            
            # Check for resumable work on individual file
            start_slide = 1
            if progress_manager.has_incomplete_work():
                start_slide, _ = progress_manager.get_resume_point()
                self.logger.info(f"Resuming {record.filename} from slide {start_slide}")
            
            # Generate notes with resume capability
            notes = note_generator.generate_notes_for_slide_contents_resumable(
                slide_contents, 
                prompt, 
                progress_manager,
                start_from_slide=start_slide
            )
            
            # Write final output
            self.file_manager.write_output_file(notes, output_path)
            
            # Clean up individual file progress
            progress_manager.cleanup_state()
            
            # Mark as completed
            self.manifest.update_file_status(
                record.filename,
                FileStatus.COMPLETED,
                completed_slides=total_slides,
                completion_time=datetime.now()
            )
            
            self.logger.info(f"Generated {len(notes)} characters for {record.filename}")
            return True
            
        except (PDFProcessingError, NoteGenerationError, FileManagerError) as e:
            self.logger.error(f"Processing error for {record.filename}: {e}")
            self.manifest.update_file_status(
                record.filename,
                FileStatus.ERROR,
                error_message=str(e)
            )
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error for {record.filename}: {e}")
            self.manifest.update_file_status(
                record.filename,
                FileStatus.ERROR,
                error_message=f"Unexpected error: {str(e)}"
            )
            return False
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary of batch processing."""
        records = self.manifest.load_manifest()
        
        if not records:
            return {
                'total_files': 0,
                'status_counts': {},
                'message': 'No manifest found'
            }
        
        status_counts = self.manifest.get_processing_summary()
        
        # Calculate progress
        completed = status_counts.get('COMPLETED', 0)
        total = status_counts.get('TOTAL', 0)
        progress_percent = (completed / total * 100) if total > 0 else 0
        
        # Find files with errors
        error_files = [r.filename for r in records if r.status == FileStatus.ERROR]
        
        return {
            'total_files': total,
            'status_counts': status_counts,
            'progress_percent': progress_percent,
            'error_files': error_files,
            'input_directory': str(self.input_dir),
            'output_directory': str(self.output_dir),
            'naming_pattern': f"{{filename}}{self.suffix}{self.extension}"
        }