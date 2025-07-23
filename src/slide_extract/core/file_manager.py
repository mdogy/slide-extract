"""File management utilities for slide extraction."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

class FileManagerError(Exception):
    """Custom exception for file manager errors."""
    pass

class FileManager:
    """Handles file operations, validation, and naming conventions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_pdf_files(self, pdf_paths: List[Path]) -> None:
        """
        Validate that PDF files exist and are accessible.
        
        Args:
            pdf_paths: List of Path objects to PDF files
            
        Raises:
            FileManagerError: If any file is invalid
        """
        for pdf_path in pdf_paths:
            if not pdf_path.exists():
                raise FileManagerError(f"PDF file not found: {pdf_path}")
            if not pdf_path.is_file():
                raise FileManagerError(f"Path is not a file: {pdf_path}")
            if not pdf_path.suffix.lower() == ".pdf":
                raise FileManagerError(f"File is not a PDF: {pdf_path}")
            
            # Check file size (should be > 0)
            if pdf_path.stat().st_size == 0:
                raise FileManagerError(f"PDF file is empty: {pdf_path}")
        
        self.logger.info(f"Validated {len(pdf_paths)} PDF files")
    
    def validate_directory(self, dir_path: Path, create_if_missing: bool = False) -> None:
        """
        Validate directory exists or create if requested.
        
        Args:
            dir_path: Path to directory
            create_if_missing: Whether to create directory if it doesn't exist
            
        Raises:
            FileManagerError: If directory validation fails
        """
        if not dir_path.exists():
            if create_if_missing:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Created directory: {dir_path}")
                except Exception as e:
                    raise FileManagerError(f"Failed to create directory {dir_path}: {e}")
            else:
                raise FileManagerError(f"Directory not found: {dir_path}")
        elif not dir_path.is_dir():
            raise FileManagerError(f"Path is not a directory: {dir_path}")
    
    def validate_prompt_file(self, prompt_path: Path) -> str:
        """
        Validate and load prompt file.
        
        Args:
            prompt_path: Path to prompt file
            
        Returns:
            Content of prompt file
            
        Raises:
            FileManagerError: If prompt file is invalid
        """
        if not prompt_path.exists():
            raise FileManagerError(f"Prompt file not found: {prompt_path}")
        if not prompt_path.is_file():
            raise FileManagerError(f"Prompt path is not a file: {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                raise FileManagerError(f"Prompt file is empty: {prompt_path}")
            
            self.logger.info(f"Loaded prompt from {prompt_path} ({len(content)} characters)")
            return content
            
        except Exception as e:
            raise FileManagerError(f"Failed to read prompt file {prompt_path}: {e}")
    
    def discover_pdf_files(self, directory: Path) -> List[Path]:
        """
        Discover all PDF files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of PDF file paths, sorted alphabetically
        """
        if not directory.exists() or not directory.is_dir():
            raise FileManagerError(f"Invalid directory: {directory}")
        
        pdf_files = []
        
        # Find all PDF files (case-insensitive)
        for pattern in ['*.pdf', '*.PDF']:
            pdf_files.extend(directory.glob(pattern))
        
        # Sort for consistent processing order
        pdf_files.sort()
        
        self.logger.info(f"Discovered {len(pdf_files)} PDF files in {directory}")
        return pdf_files
    
    def generate_output_path(
        self, 
        input_path: Path, 
        output_dir: Path, 
        suffix: str = "_summary", 
        extension: str = ".md"
    ) -> Path:
        """
        Generate output file path based on input file and parameters.
        
        Args:
            input_path: Input PDF file path
            output_dir: Output directory
            suffix: Suffix to add to filename
            extension: File extension for output
            
        Returns:
            Generated output file path
        """
        output_filename = input_path.stem + suffix + extension
        return output_dir / output_filename
    
    def ensure_output_directory(self, output_path: Path) -> None:
        """
        Ensure output directory exists for given file path.
        
        Args:
            output_path: Path to output file
        """
        output_dir = output_path.parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created output directory: {output_dir}")
    
    def write_output_file(self, content: str, output_path: Path) -> None:
        """
        Write content to output file with proper error handling.
        
        Args:
            content: Content to write
            output_path: Path to output file
            
        Raises:
            FileManagerError: If writing fails
        """
        try:
            # Ensure output directory exists
            self.ensure_output_directory(output_path)
            
            # Write content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Written {len(content)} characters to {output_path}")
            
        except Exception as e:
            raise FileManagerError(f"Failed to write output file {output_path}: {e}")
    
    def append_to_file(self, content: str, file_path: Path) -> None:
        """
        Append content to existing file.
        
        Args:
            content: Content to append
            file_path: Path to file
            
        Raises:
            FileManagerError: If appending fails
        """
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"Appended {len(content)} characters to {file_path}")
            
        except Exception as e:
            raise FileManagerError(f"Failed to append to file {file_path}: {e}")
    
    def backup_file(self, file_path: Path, backup_suffix: str = ".backup") -> Path:
        """
        Create backup of existing file.
        
        Args:
            file_path: Path to file to backup
            backup_suffix: Suffix for backup file
            
        Returns:
            Path to backup file
            
        Raises:
            FileManagerError: If backup fails
        """
        if not file_path.exists():
            raise FileManagerError(f"Cannot backup non-existent file: {file_path}")
        
        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
        
        try:
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            raise FileManagerError(f"Failed to create backup of {file_path}: {e}")
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        if not file_path.exists():
            return {'exists': False}
        
        stat = file_path.stat()
        
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'is_file': file_path.is_file(),
            'is_dir': file_path.is_dir(),
            'extension': file_path.suffix,
            'stem': file_path.stem,
            'name': file_path.name
        }
    
    def clean_temp_files(self, directory: Path, patterns: List[str]) -> int:
        """
        Clean temporary files matching patterns.
        
        Args:
            directory: Directory to clean
            patterns: List of glob patterns to match
            
        Returns:
            Number of files cleaned
        """
        cleaned_count = 0
        
        for pattern in patterns:
            for file_path in directory.glob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"Cleaned temp file: {file_path}")
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        cleaned_count += 1
                        self.logger.debug(f"Cleaned temp directory: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean {file_path}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned {cleaned_count} temporary files/directories")
        
        return cleaned_count