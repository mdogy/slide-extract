"""Unit tests for progress manager and resume functionality."""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from slide_extract.core.progress_manager import ProgressManager, ProcessingState, SlideProgress

class TestProgressManager:
    """Test progress manager functionality."""
    
    def test_has_incomplete_work_no_state_file(self, temp_dir):
        """Test detection when no state file exists."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        assert not progress_manager.has_incomplete_work()
    
    def test_has_incomplete_work_with_valid_state(self, temp_dir, sample_progress_state):
        """Test detection with valid state file."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single', 
            file_path=temp_dir / "test.pdf"
        )
        
        # Create test PDF file
        (temp_dir / "test.pdf").touch()
        
        # Save state
        progress_manager.save_state(sample_progress_state)
        
        assert progress_manager.has_incomplete_work()
    
    def test_get_resume_point_with_incomplete_slide(self, temp_dir, sample_progress_state):
        """Test resume point detection with incomplete last slide."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        # Create test files
        (temp_dir / "test.pdf").touch()
        
        # Modify state to have incomplete last slide
        sample_progress_state.completed_slides = 6
        sample_progress_state.last_validated_slide = 5
        
        progress_manager.save_state(sample_progress_state)
        
        with patch.object(progress_manager, '_cleanup_incomplete_output'):
            resume_slide, state = progress_manager.get_resume_point()
            assert resume_slide == 6  # Should resume from slide after last validated
    
    def test_checkpoint_slide(self, temp_dir, sample_slide_contents):
        """Test slide checkpoint functionality."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        slide_content = sample_slide_contents[1]
        test_content = "Test slide analysis content"
        
        # Checkpoint slide
        progress_manager.checkpoint_slide(1, test_content, slide_content)
        
        # Verify state was saved
        assert progress_manager.state_file.exists()
        
        # Load and verify state
        state = progress_manager.load_state()
        assert state.completed_slides == 1
        assert len(state.slide_progress) == 1
        assert state.slide_progress[0].slide_number == 1
        assert state.slide_progress[0].completed == True
    
    def test_validate_slide_content(self, temp_dir):
        """Test slide content validation."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        # Valid content
        valid_content = """
        **Slide Number:** 1
        **Slide Text:** Test content
        **Slide Images/Diagrams:** Test images
        **Slide Topics:** Test topics
        **Slide Narration:** Test narration
        """
        
        assert progress_manager._validate_slide_content(valid_content)
        
        # Invalid content (missing sections)
        invalid_content = "**Slide Number:** 1"
        assert not progress_manager._validate_slide_content(invalid_content)
    
    def test_cleanup_incomplete_output(self, temp_dir):
        """Test cleanup of incomplete output content."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        # Create output file with multiple slides
        output_content = """
        **Slide Number:** 1
        Content for slide 1
        ---
        **Slide Number:** 2
        Content for slide 2
        ---
        **Slide Number:** 3
        Incomplete content for slide 3
        """
        
        with open(progress_manager.output_path, 'w') as f:
            f.write(output_content)
        
        # Cleanup after slide 2
        progress_manager._cleanup_incomplete_output(2)
        
        # Verify truncation
        with open(progress_manager.output_path, 'r') as f:
            truncated_content = f.read()
        
        assert "**Slide Number:** 3" not in truncated_content
        assert "**Slide Number:** 2" in truncated_content
    
    def test_record_slide_error(self, temp_dir):
        """Test error recording functionality."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        # Record error
        progress_manager.record_slide_error(5, "Test error message")
        
        # Verify error was recorded
        state = progress_manager.load_state()
        assert len(state.slide_progress) == 1
        assert state.slide_progress[0].slide_number == 5
        assert state.slide_progress[0].completed == False
        assert state.slide_progress[0].error_message == "Test error message"
    
    def test_cleanup_state(self, temp_dir):
        """Test state file cleanup."""
        progress_manager = ProgressManager(
            output_path=temp_dir / "output.md",
            mode='single',
            file_path=temp_dir / "test.pdf"
        )
        
        # Create state file
        state = ProcessingState(
            file_path=str(temp_dir / "test.pdf"),
            total_slides=5,
            completed_slides=0,
            slide_progress=[],
            last_validated_slide=0,
            output_path=str(temp_dir / "output.md"),
            start_time=datetime.now(),
            last_update=datetime.now(),
            processing_mode="single",
            prompt_checksum="abc123",
            config_checksum="def456"
        )
        progress_manager.save_state(state)
        
        assert progress_manager.state_file.exists()
        
        # Cleanup
        progress_manager.cleanup_state()
        
        assert not progress_manager.state_file.exists()