"""Unit tests for batch processor functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from slide_extract.core.batch_processor import BatchProcessor, BatchProcessingError
from slide_extract.core.manifest_manager import FileStatus

class TestBatchProcessor:
    """Test batch processing functionality."""
    
    def test_discover_pdfs(self, temp_dir):
        """Test PDF file discovery."""
        # Create test PDF files
        (temp_dir / "presentation1.pdf").touch()
        (temp_dir / "presentation2.PDF").touch()  # Test case insensitive
        (temp_dir / "not_a_pdf.txt").touch()
        (temp_dir / "subdir").mkdir()
        
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        pdfs = processor.discover_pdfs()
        
        assert len(pdfs) == 2
        assert any(p.name == "presentation1.pdf" for p in pdfs)
        assert any(p.name == "presentation2.PDF" for p in pdfs)
        assert not any(p.name == "not_a_pdf.txt" for p in pdfs)
    
    def test_init_with_invalid_input_dir(self, temp_dir):
        """Test initialization with invalid input directory."""
        with pytest.raises(BatchProcessingError):
            BatchProcessor(
                input_dir=temp_dir / "nonexistent",
                output_dir=temp_dir / "output",
                suffix="_summary",
                extension=".md"
            )
    
    def test_process_directory_new_batch(self, temp_dir, mock_llm_client):
        """Test processing new batch from scratch."""
        # Create test PDF files
        (temp_dir / "test1.pdf").touch()
        (temp_dir / "test2.pdf").touch()
        
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        with patch.object(processor, '_process_single_file', return_value=True):
            result = processor.process_directory(
                llm_client=mock_llm_client,
                prompt="Test prompt",
                resume=False,
                clean_start=False
            )
        
        assert result == 0
        assert (temp_dir / "output" / ".slide_dir_extract_manifest.txt").exists()
    
    def test_process_directory_with_resume(self, temp_dir, mock_llm_client, sample_manifest_records):
        """Test batch processing with resume capability."""
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary", 
            extension=".md"
        )
        
        # Mock manifest with existing records
        with patch.object(processor.manifest, 'load_manifest', return_value=sample_manifest_records):
            with patch.object(processor.manifest, 'get_files_by_status') as mock_get_files:
                # Return only pending files
                pending_files = [r for r in sample_manifest_records if r.status == FileStatus.PENDING]
                mock_get_files.return_value = pending_files
                
                with patch.object(processor, '_process_single_file', return_value=True):
                    result = processor.process_directory(
                        llm_client=mock_llm_client,
                        prompt="Test prompt",
                        resume=True,
                        clean_start=False
                    )
        
        assert result == 0
    
    def test_process_single_file_success(self, temp_dir, mock_llm_client, sample_manifest_records):
        """Test successful single file processing."""
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        # Create test file
        test_pdf = temp_dir / "test.pdf"
        test_pdf.touch()
        
        record = sample_manifest_records[2]  # PENDING record
        record.input_path = str(test_pdf)
        record.output_path = str(temp_dir / "output" / "test_summary.md")
        
        # Mock dependencies
        mock_pdf_processor = Mock()
        mock_pdf_processor.extract_slide_content.return_value = {1: Mock(), 2: Mock()}
        
        mock_note_generator = Mock()
        mock_note_generator.generate_notes_for_slide_contents_resumable.return_value = "Test notes"
        
        with patch('slide_extract.core.batch_processor.ProgressManager'):
            result = processor._process_single_file(
                record, mock_pdf_processor, mock_note_generator, "Test prompt"
            )
        
        assert result == True
    
    def test_process_single_file_with_error(self, temp_dir, mock_llm_client, sample_manifest_records):
        """Test single file processing with error handling."""
        processor = BatchProcessor(
            input_dir=temp_dir, 
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        record = sample_manifest_records[2]  # PENDING record
        
        # Mock PDF processor to raise error
        mock_pdf_processor = Mock()
        mock_pdf_processor.extract_slide_content.side_effect = Exception("Test error")
        
        mock_note_generator = Mock()
        
        result = processor._process_single_file(
            record, mock_pdf_processor, mock_note_generator, "Test prompt"
        )
        
        assert result == False
    
    def test_get_status_summary(self, temp_dir, sample_manifest_records):
        """Test status summary generation."""
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        # Mock manifest
        with patch.object(processor.manifest, 'load_manifest', return_value=sample_manifest_records):
            summary = processor.get_status_summary()
        
        assert summary['total_files'] == 3
        assert summary['status_counts']['COMPLETED'] == 1
        assert summary['status_counts']['IN_PROGRESS'] == 1
        assert summary['status_counts']['PENDING'] == 1
        assert summary['progress_percent'] == pytest.approx(33.33, rel=1e-2)
        assert summary['input_directory'] == str(temp_dir)
        assert summary['output_directory'] == str(temp_dir / "output")
    
    def test_get_status_summary_no_manifest(self, temp_dir):
        """Test status summary with no manifest."""
        processor = BatchProcessor(
            input_dir=temp_dir,
            output_dir=temp_dir / "output",
            suffix="_summary",
            extension=".md"
        )
        
        summary = processor.get_status_summary()
        
        assert summary['total_files'] == 0
        assert summary['message'] == 'No manifest found'