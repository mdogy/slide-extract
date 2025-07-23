"""Integration tests for complete single file CLI workflow."""

import pytest
import subprocess
import json
from pathlib import Path

class TestSingleCLIIntegration:
    """Test complete single file CLI workflows."""
    
    def test_complete_workflow_no_ai(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test complete workflow in no-AI mode."""
        # Create test files
        pdf_path = create_test_pdf("test.pdf")
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        output_path = temp_dir / "output.md"
        
        # Run CLI command
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf_path),
            "-p", str(prompt_path), 
            "-o", str(output_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert output_path.exists()
        assert "placeholder" in output_path.read_text().lower()
    
    def test_resume_functionality(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test resume functionality with interrupted processing."""
        # Create test files
        pdf_path = create_test_pdf("test.pdf")
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        output_path = temp_dir / "output.md"
        
        # Create partial progress state
        progress_file = temp_dir / f".slide_extract_progress_{output_path.stem}.json"
        progress_data = {
            "file_path": str(pdf_path),
            "total_slides": 5,
            "completed_slides": 3,
            "slide_progress": [
                {"slide_number": i, "completed": True, "character_count": 1000, "is_validated": True, "completion_time": "2024-01-01T10:00:00", "error_message": None}
                for i in range(1, 4)
            ],
            "last_validated_slide": 3,
            "output_path": str(output_path),
            "start_time": "2024-01-01T10:00:00",
            "last_update": "2024-01-01T10:15:00",
            "processing_mode": "single",
            "prompt_checksum": "abc123",
            "config_checksum": "def456"
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        # Create partial output
        partial_output = "# Partial Output\n\n**Slide Number:** 1\nContent for slide 1\n"
        with open(output_path, 'w') as f:
            f.write(partial_output)
        
        # Run with resume
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf_path),
            "-p", str(prompt_path),
            "-o", str(output_path),
            "--resume",
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        # Progress file should be cleaned up on completion
        assert not progress_file.exists()
    
    def test_clean_start_functionality(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test clean start ignoring existing progress."""
        # Create test files
        pdf_path = create_test_pdf("test.pdf")
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        output_path = temp_dir / "output.md"
        
        # Create existing progress state
        progress_file = temp_dir / f".slide_extract_progress_{output_path.stem}.json"
        progress_data = {"file_path": str(pdf_path), "completed_slides": 3}
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        # Run with clean start
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf_path),
            "-p", str(prompt_path),
            "-o", str(output_path),
            "--clean-start",
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert output_path.exists()
        # Should have started fresh
        assert "**Slide Number:** 1" in output_path.read_text()
    
    def test_multiple_pdf_processing(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test processing multiple PDF files."""
        # Create test files
        pdf1 = create_test_pdf("test1.pdf")
        pdf2 = create_test_pdf("test2.pdf")
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        output_path = temp_dir / "output.md"
        
        # Run CLI command
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf1), str(pdf2),
            "-p", str(prompt_path),
            "-o", str(output_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert output_path.exists()
        
        # Should contain headers for both files
        content = output_path.read_text()
        assert "test1.pdf" in content
        assert "test2.pdf" in content
    
    def test_error_handling_missing_pdf(self, temp_dir, create_test_prompt):
        """Test error handling for missing PDF file."""
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(temp_dir / "nonexistent.pdf"),
            "-p", str(prompt_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
    
    def test_error_handling_missing_prompt(self, temp_dir, create_test_pdf):
        """Test error handling for missing prompt file."""
        pdf_path = create_test_pdf("test.pdf")
        
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf_path),
            "-p", str(temp_dir / "nonexistent.md"),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
    
    def test_stdout_output(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test output to stdout when no output file specified."""
        pdf_path = create_test_pdf("test.pdf")
        prompt_path = create_test_prompt("test_prompt.md", "Analyze this slide.")
        
        cmd = [
            "python", "-m", "slide_extract.cli.single",
            "-i", str(pdf_path),
            "-p", str(prompt_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert "**Slide Number:**" in result.stdout
        assert "placeholder" in result.stdout.lower()