"""Integration tests for complete batch CLI workflow."""

import pytest
import subprocess
from pathlib import Path

class TestBatchCLIIntegration:
    """Test complete batch CLI workflows."""
    
    def test_complete_batch_workflow_no_ai(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test complete batch workflow in no-AI mode."""
        # Create input directory with PDFs
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        
        # Create test PDFs
        create_test_pdf("presentation1.pdf").rename(input_dir / "presentation1.pdf")
        create_test_pdf("presentation2.pdf").rename(input_dir / "presentation2.pdf")
        
        # Create test prompt
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        # Run batch CLI command
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", str(prompt_path),
            "-o", str(output_dir),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert output_dir.exists()
        
        # Check manifest exists
        manifest_file = output_dir / ".slide_dir_extract_manifest.txt"
        assert manifest_file.exists()
        
        # Check output files exist
        assert (output_dir / "presentation1_summary.md").exists()
        assert (output_dir / "presentation2_summary.md").exists()
    
    def test_batch_resume_functionality(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test batch processing with resume from manifest."""
        # Setup directories and files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        create_test_pdf("test1.pdf").rename(input_dir / "test1.pdf")
        create_test_pdf("test2.pdf").rename(input_dir / "test2.pdf")
        create_test_pdf("test3.pdf").rename(input_dir / "test3.pdf")
        
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        # Create existing manifest with partial completion
        manifest_content = """# Slide Directory Extract Progress Manifest
# Generated: 2024-01-01T10:00:00
# Command: slide-dir-extract -i input -o output
# Output Directory: output
# Total Files: 3
#
STATUS|FILENAME|INPUT_PATH|OUTPUT_PATH|TOTAL_SLIDES|COMPLETED_SLIDES|START_TIME|COMPLETION_TIME|ERROR_MESSAGE|FILE_SIZE|CHECKSUM
COMPLETED|test1.pdf|input/test1.pdf|output/test1_summary.md|10|10|2024-01-01T10:00:00|2024-01-01T10:05:00||1024|abc123
IN_PROGRESS|test2.pdf|input/test2.pdf|output/test2_summary.md|8|5|2024-01-01T10:05:00|||512|def456
PENDING|test3.pdf|input/test3.pdf|output/test3_summary.md|0|0|||||2048|ghi789
"""
        
        manifest_file = output_dir / ".slide_dir_extract_manifest.txt"
        with open(manifest_file, 'w') as f:
            f.write(manifest_content)
        
        # Create completed output file
        completed_output = "# Completed output for test1.pdf"
        with open(output_dir / "test1_summary.md", 'w') as f:
            f.write(completed_output)
        
        # Run with resume
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", str(prompt_path),
            "-o", str(output_dir),
            "--resume",
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        
        # Should have processed pending files
        assert (output_dir / "test3_summary.md").exists()
        
        # Original completed file should remain
        assert (output_dir / "test1_summary.md").read_text() == completed_output
    
    def test_batch_status_command(self, temp_dir, create_test_pdf):
        """Test batch status display command.""" 
        # Setup with existing manifest
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        # Create manifest
        manifest_content = """# Slide Directory Extract Progress Manifest
STATUS|FILENAME|INPUT_PATH|OUTPUT_PATH|TOTAL_SLIDES|COMPLETED_SLIDES|START_TIME|COMPLETION_TIME|ERROR_MESSAGE|FILE_SIZE|CHECKSUM
COMPLETED|test1.pdf|input/test1.pdf|output/test1_summary.md|10|10|2024-01-01T10:00:00|2024-01-01T10:05:00||1024|abc123
PENDING|test2.pdf|input/test2.pdf|output/test2_summary.md|0|0|||||512|def456
ERROR|test3.pdf|input/test3.pdf|output/test3_summary.md|0|0|||Processing failed|2048|ghi789
"""
        
        manifest_file = output_dir / ".slide_dir_extract_manifest.txt"
        with open(manifest_file, 'w') as f:
            f.write(manifest_content)
        
        # Run status command
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", "dummy.md",  # Won't be used for status
            "-o", str(output_dir),
            "--show-status"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        assert "COMPLETED: 1" in result.stdout
        assert "PENDING: 1" in result.stdout
        assert "ERROR: 1" in result.stdout
    
    def test_batch_clean_start(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test batch processing with clean start."""
        # Setup directories and files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        create_test_pdf("test.pdf").rename(input_dir / "test.pdf")
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        # Create existing manifest
        manifest_file = output_dir / ".slide_dir_extract_manifest.txt"
        with open(manifest_file, 'w') as f:
            f.write("# Old manifest")
        
        # Run with clean start
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", str(prompt_path),
            "-o", str(output_dir),
            "--clean-start",
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        
        # Should have created new manifest
        assert manifest_file.exists()
        content = manifest_file.read_text()
        assert "Old manifest" not in content
        assert "test.pdf" in content
    
    def test_custom_suffix_and_extension(self, temp_dir, create_test_pdf, create_test_prompt):
        """Test batch processing with custom suffix and extension."""
        # Create input directory with PDFs
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        
        create_test_pdf("presentation.pdf").rename(input_dir / "presentation.pdf")
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        # Run with custom naming
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", str(prompt_path),
            "-o", str(output_dir),
            "--suffix", "_notes",
            "--extension", ".txt",
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 0
        
        # Check custom output file exists
        expected_output = output_dir / "presentation_notes.txt"
        assert expected_output.exists()
    
    def test_error_handling_invalid_input_dir(self, temp_dir, create_test_prompt):
        """Test error handling for invalid input directory."""
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(temp_dir / "nonexistent"),
            "-p", str(prompt_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "does not exist" in result.stderr.lower()
    
    def test_no_pdfs_found(self, temp_dir, create_test_prompt):
        """Test handling when no PDF files are found."""
        # Create empty input directory
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        
        # Add non-PDF file
        (input_dir / "not_a_pdf.txt").touch()
        
        prompt_path = create_test_prompt("batch_prompt.md", "Analyze these slides.")
        
        cmd = [
            "python", "-m", "slide_extract.cli.batch",
            "-i", str(input_dir),
            "-p", str(prompt_path),
            "--no-ai"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir.parent)
        
        assert result.returncode == 1
        assert "no pdf files found" in result.stderr.lower()