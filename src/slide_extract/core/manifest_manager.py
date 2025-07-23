"""Batch processing manifest management with robust tracking."""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
import csv
import logging
import hashlib

class FileStatus(Enum):
    """Processing status for individual files."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

@dataclass
class FileRecord:
    """Individual file processing record."""
    filename: str
    input_path: str
    output_path: str
    status: FileStatus
    total_slides: int
    completed_slides: int
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    file_size: int = 0
    checksum: str = ""  # To detect file changes
    
class ManifestManager:
    """Manages batch processing manifest with comprehensive tracking."""
    
    def __init__(self, output_dir: Path, suffix: str = "_summary", extension: str = ".md"):
        self.output_dir = Path(output_dir)
        self.suffix = suffix
        self.extension = extension
        self.manifest_file = self.output_dir / ".slide_dir_extract_manifest.txt"
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize_manifest(self, pdf_files: List[Path], command_args: str) -> None:
        """Initialize manifest with discovered PDF files."""
        records = []
        
        for pdf_path in sorted(pdf_files):  # Sort for consistent order
            output_filename = pdf_path.stem + self.suffix + self.extension
            output_path = self.output_dir / output_filename
            
            # Calculate file checksum for change detection
            file_checksum = self._calculate_file_checksum(pdf_path)
            
            record = FileRecord(
                filename=pdf_path.name,
                input_path=str(pdf_path),
                output_path=str(output_path),
                status=FileStatus.PENDING,
                total_slides=0,  # Will be updated during processing
                completed_slides=0,
                file_size=pdf_path.stat().st_size,
                checksum=file_checksum
            )
            records.append(record)
        
        # Write manifest header and records
        self._write_manifest(records, command_args)
        self.logger.info(f"Initialized manifest with {len(records)} files")
    
    def _write_manifest(self, records: List[FileRecord], command_args: str = "") -> None:
        """Write complete manifest to file."""
        try:
            with open(self.manifest_file, 'w', newline='') as f:
                # Write header with metadata
                f.write(f"# Slide Directory Extract Progress Manifest\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Command: {command_args}\n")
                f.write(f"# Output Directory: {self.output_dir}\n")
                f.write(f"# Total Files: {len(records)}\n")
                f.write(f"#\n")
                
                # Write CSV data
                writer = csv.writer(f, delimiter='|')
                writer.writerow([
                    'STATUS', 'FILENAME', 'INPUT_PATH', 'OUTPUT_PATH', 
                    'TOTAL_SLIDES', 'COMPLETED_SLIDES', 'START_TIME', 
                    'COMPLETION_TIME', 'ERROR_MESSAGE', 'FILE_SIZE', 'CHECKSUM'
                ])
                
                for record in records:
                    writer.writerow([
                        record.status.value,
                        record.filename,
                        record.input_path,
                        record.output_path,
                        record.total_slides,
                        record.completed_slides,
                        record.start_time.isoformat() if record.start_time else '',
                        record.completion_time.isoformat() if record.completion_time else '',
                        record.error_message or '',
                        record.file_size,
                        record.checksum
                    ])
                        
        except Exception as e:
            self.logger.error(f"Failed to write manifest: {e}")
            raise
    
    def load_manifest(self) -> List[FileRecord]:
        """Load existing manifest from file."""
        if not self.manifest_file.exists():
            return []
        
        records = []
        try:
            with open(self.manifest_file, 'r') as f:
                # Skip header lines
                lines = f.readlines()
                data_lines = [line for line in lines if not line.startswith('#')]
                
                reader = csv.reader(data_lines, delimiter='|')
                header = next(reader, None)  # Skip header row
                
                for row in reader:
                    if len(row) >= 11:  # Ensure minimum required fields
                        record = FileRecord(
                            filename=row[1],
                            input_path=row[2],
                            output_path=row[3],
                            status=FileStatus(row[0]),
                            total_slides=int(row[4]) if row[4] else 0,
                            completed_slides=int(row[5]) if row[5] else 0,
                            start_time=datetime.fromisoformat(row[6]) if row[6] else None,
                            completion_time=datetime.fromisoformat(row[7]) if row[7] else None,
                            error_message=row[8] if row[8] else None,
                            file_size=int(row[9]) if row[9] else 0,
                            checksum=row[10] if len(row) > 10 else ""
                        )
                        records.append(record)
                        
        except Exception as e:
            self.logger.error(f"Failed to load manifest: {e}")
            # Return empty list to start fresh if manifest is corrupted
            return []
        
        self.logger.info(f"Loaded manifest with {len(records)} records")
        return records
    
    def update_file_status(self, filename: str, status: FileStatus, **kwargs) -> None:
        """Update status and metadata for a specific file."""
        records = self.load_manifest()
        
        # Find and update the record
        for record in records:
            if record.filename == filename:
                record.status = status
                
                # Update optional fields
                if 'total_slides' in kwargs:
                    record.total_slides = kwargs['total_slides']
                if 'completed_slides' in kwargs:
                    record.completed_slides = kwargs['completed_slides']
                if 'error_message' in kwargs:
                    record.error_message = kwargs['error_message']
                if 'start_time' in kwargs:
                    record.start_time = kwargs['start_time']
                if 'completion_time' in kwargs:
                    record.completion_time = kwargs['completion_time']
                
                break
        
        # Write updated manifest
        self._write_manifest(records)
        self.logger.debug(f"Updated {filename}: {status.value}")
    
    def get_files_by_status(self, status: FileStatus) -> List[FileRecord]:
        """Get all files with specified status."""
        records = self.load_manifest()
        return [record for record in records if record.status == status]
    
    def get_processing_summary(self) -> Dict[str, int]:
        """Get summary of processing status."""
        records = self.load_manifest()
        summary = {status.value: 0 for status in FileStatus}
        
        for record in records:
            summary[record.status.value] += 1
        
        summary['TOTAL'] = len(records)
        return summary
    
    def detect_file_changes(self, input_dir: Path) -> List[str]:
        """Detect if any input files have changed since manifest creation."""
        records = self.load_manifest()
        changed_files = []
        
        for record in records:
            input_path = Path(record.input_path)
            if input_path.exists():
                current_checksum = self._calculate_file_checksum(input_path)
                if current_checksum != record.checksum:
                    changed_files.append(record.filename)
                    self.logger.warning(f"File changed: {record.filename}")
        
        return changed_files
    
    def cleanup_manifest(self) -> None:
        """Remove manifest file for clean start."""
        try:
            if self.manifest_file.exists():
                self.manifest_file.unlink()
                self.logger.info("Cleaned up manifest file")
        except Exception as e:
            self.logger.error(f"Failed to cleanup manifest: {e}")
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate simple checksum for file change detection."""
        try:
            hash_obj = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read first and last 1KB for quick checksum
                hash_obj.update(f.read(1024))
                f.seek(-1024, 2)  # Seek to 1KB from end
                hash_obj.update(f.read(1024))
            return hash_obj.hexdigest()[:16]  # First 16 chars
        except Exception:
            return ""