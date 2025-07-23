"""Shared CLI utilities and common functionality."""

import logging
import sys
from pathlib import Path
from typing import Optional, List
import argparse

from ..core.config_manager import ConfigManager, ConfigurationError
from ..core.llm_client import create_llm_client, LLMError
from ..core.file_manager import FileManager, FileManagerError

class CommonCLI:
    """Shared CLI operations for both single and batch processing."""
    
    @staticmethod
    def setup_logging(verbose: bool = False, log_file: str = "slide_extract.log") -> None:
        """Configure logging with file and console output."""
        # Configure file logging
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Configure console logging (to stderr)
        console_handler = logging.StreamHandler(sys.stderr)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)

        # Set logging level based on verbose flag
        log_level = logging.DEBUG if verbose else logging.INFO

        # Configure root logger
        logging.basicConfig(
            level=log_level, 
            handlers=[file_handler, console_handler], 
            force=True
        )

        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized at {log_level} level")
    
    @staticmethod
    def validate_pdf_files(pdf_paths: List[Path]) -> None:
        """Validate that PDF files exist and are accessible."""
        file_manager = FileManager()
        try:
            file_manager.validate_pdf_files(pdf_paths)
        except FileManagerError as e:
            raise CLIError(str(e))
    
    @staticmethod
    def validate_directory(dir_path: Path, create_if_missing: bool = False) -> None:
        """Validate directory exists or create if requested."""
        file_manager = FileManager()
        try:
            file_manager.validate_directory(dir_path, create_if_missing)
        except FileManagerError as e:
            raise CLIError(str(e))
    
    @staticmethod
    def initialize_llm(config_path: Optional[Path], no_ai: bool):
        """Initialize LLM client with proper error handling."""
        logger = logging.getLogger(__name__)
        
        if no_ai:
            logger.info("Running in no-AI mode (placeholder only)")
            return None
        
        try:
            # Initialize configuration
            config_manager = ConfigManager(config_path)
            
            # Create LLM client
            llm_config = config_manager.get_llm_config()
            llm_client = create_llm_client(llm_config)

            # Test connection
            logger.info("Testing LLM connection...")
            if llm_client.test_connection():
                model_info = llm_client.get_model_info()
                logger.info(
                    "LLM connection successful: %s %s",
                    model_info["provider"],
                    model_info["model"],
                )
                return llm_client
            else:
                logger.error("LLM connection test failed")
                raise CLIError("LLM connection failed")

        except (ConfigurationError, LLMError) as e:
            logger.error("LLM initialization failed: %s", e)
            raise CLIError(
                "No LLM/AI has been configured. "
                "Either run with --no-ai flag to use placeholders, or "
                "follow the README instructions to set up an LLM API key."
            ) from e
    
    @staticmethod
    def load_and_validate_prompt(prompt_path: Path) -> str:
        """Load and validate prompt file."""
        file_manager = FileManager()
        try:
            return file_manager.validate_prompt_file(prompt_path)
        except FileManagerError as e:
            raise CLIError(str(e))
    
    @staticmethod
    def handle_output(content: str, output_path: Optional[Path]) -> None:
        """Handle output to file or stdout."""
        logger = logging.getLogger(__name__)
        
        if output_path:
            file_manager = FileManager()
            try:
                file_manager.write_output_file(content, output_path)
            except FileManagerError as e:
                raise CLIError(str(e))
        else:
            # Write to stdout (not using logger for actual output)
            print(content, end="")
            logger.info(f"Output written to stdout ({len(content)} characters)")
    
    @staticmethod
    def add_common_arguments(parser: argparse.ArgumentParser) -> None:
        """Add common arguments used by both CLI commands."""
        parser.add_argument(
            "--prompt", "-p", 
            required=True,
            help="Path to Markdown file containing the generation prompt"
        )
        
        parser.add_argument(
            "--config", "-c", 
            help="Path to configuration file (default: config.yaml)"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging (DEBUG level)"
        )
        
        parser.add_argument(
            "--no-ai",
            action="store_true",
            help="Use placeholder mode without AI (for testing)"
        )
        
        parser.add_argument(
            "--version", 
            action="version", 
            version="slide-extract 1.1.0"
        )

class CLIError(Exception):
    """Custom exception for CLI-specific errors."""
    pass