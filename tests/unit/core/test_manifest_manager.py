"""Unit tests for manifest manager functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from slide_extract.core.manifest_manager import ManifestManager, FileStatus, FileRecord

class TestManifestManager:
    """Test manifest management functionality."""
    
    def test_initialize_manifest(self, temp_dir):
        """Test manifest initialization with PDF files."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        
        # Create test PDF files
        pdf_files = [
            temp_dir / "test1.pdf",
            temp_dir / "test2.pdf"
        ]
        for pdf in pdf_files:
            pdf.touch()
        
        # Initialize manifest
        manager.initialize_manifest(pdf_files, "test command")
        
        # Verify manifest file exists
        assert manager.manifest_file.exists()
        
        # Verify records were created
        records = manager.load_manifest()
        assert len(records) == 2
        assert all(r.status == FileStatus.PENDING for r in records)
    
    def test_load_manifest(self, temp_dir, sample_manifest_records):
        """Test loading existing manifest."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        
        # Write test manifest
        manager._write_manifest(sample_manifest_records, "test command")
        
        # Load and verify
        loaded_records = manager.load_manifest()
        assert len(loaded_records) == len(sample_manifest_records)
        assert loaded_records[0].filename == "presentation1.pdf"
        assert loaded_records[0].status == FileStatus.COMPLETED
    
    def test_update_file_status(self, temp_dir, sample_manifest_records):
        """Test updating file status in manifest."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        manager._write_manifest(sample_manifest_records, "test command")
        
        # Update status
        manager.update_file_status(
            "presentation2.pdf", 
            FileStatus.COMPLETED,
            completed_slides=15
        )
        
        # Verify update
        records = manager.load_manifest()
        updated_record = next(r for r in records if r.filename == "presentation2.pdf")
        assert updated_record.status == FileStatus.COMPLETED
        assert updated_record.completed_slides == 15
    
    def test_get_files_by_status(self, temp_dir, sample_manifest_records):
        """Test filtering files by status."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        manager._write_manifest(sample_manifest_records, "test command")
        
        # Get pending files
        pending_files = manager.get_files_by_status(FileStatus.PENDING)
        assert len(pending_files) == 1
        assert pending_files[0].filename == "presentation3.pdf"
        
        # Get completed files
        completed_files = manager.get_files_by_status(FileStatus.COMPLETED)
        assert len(completed_files) == 1
        assert completed_files[0].filename == "presentation1.pdf"
    
    def test_get_processing_summary(self, temp_dir, sample_manifest_records):
        """Test processing summary generation."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        manager._write_manifest(sample_manifest_records, "test command")
        
        summary = manager.get_processing_summary()
        
        assert summary['TOTAL'] == 3
        assert summary['COMPLETED'] == 1
        assert summary['IN_PROGRESS'] == 1
        assert summary['PENDING'] == 1
        assert summary['ERROR'] == 0
    
    def test_detect_file_changes(self, temp_dir):
        """Test file change detection."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        
        # Create test file
        test_pdf = temp_dir / "test.pdf"
        with open(test_pdf, 'wb') as f:
            f.write(b"original content")
        
        # Initialize manifest
        manager.initialize_manifest([test_pdf], "test command")
        
        # Modify file
        with open(test_pdf, 'wb') as f:
            f.write(b"modified content")
        
        # Detect changes
        changed_files = manager.detect_file_changes(temp_dir)
        assert "test.pdf" in changed_files
    
    def test_cleanup_manifest(self, temp_dir):
        """Test manifest cleanup."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        
        # Create manifest
        manager.initialize_manifest([temp_dir / "test.pdf"], "test command")
        assert manager.manifest_file.exists()
        
        # Cleanup
        manager.cleanup_manifest()
        assert not manager.manifest_file.exists()
    
    def test_calculate_file_checksum(self, temp_dir):
        """Test file checksum calculation."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        manager = ManifestManager(output_dir)
        
        # Create test file
        test_file = temp_dir / "test.txt"
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Calculate checksum
        checksum1 = manager._calculate_file_checksum(test_file)
        checksum2 = manager._calculate_file_checksum(test_file)
        
        # Should be consistent
        assert checksum1 == checksum2
        assert len(checksum1) == 16  # First 16 chars of MD5
        
        # Should change with content
        with open(test_file, 'w') as f:
            f.write("different content")
        
        checksum3 = manager._calculate_file_checksum(test_file)
        assert checksum1 != checksum3