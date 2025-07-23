"""Comprehensive pytest configuration with fixtures for all testing scenarios."""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, List
from datetime import datetime

from slide_extract.core.pdf_processor import SlideContent
from slide_extract.core.manifest_manager import FileRecord, FileStatus
from slide_extract.core.progress_manager import ProcessingState, SlideProgress

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture  
def sample_slides_dir():
    """Path to sample slides directory for batch testing."""
    return Path(__file__).parent / "fixtures" / "sample_slides"

@pytest.fixture
def sample_summaries_dir():
    """Path to expected sample summaries."""
    return Path(__file__).parent / "fixtures" / "sample_slide_summaries"

@pytest.fixture
def test_prompts_dir():
    """Path to test prompts."""
    return Path(__file__).parent / "fixtures" / "prompts"

@pytest.fixture
def basic_prompt_path(test_prompts_dir):
    """Path to basic test prompt."""
    return test_prompts_dir / "basic_prompt.md"

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock_client = Mock()
    mock_client.generate_slide_analysis.return_value = """
# Test Analysis

**Slide Number:** 1

**Slide Text:**
Test slide content

**Slide Images/Diagrams:**
Test slide has a simple layout with black background and white text.

**Slide Topics:**
* Test topic 1
* Test topic 2

**Slide Narration:**
"This is a test slide for unit testing purposes."
"""
    mock_client.test_connection.return_value = True
    mock_client.get_model_info.return_value = {
        "provider": "test",
        "model": "test-model"
    }
    return mock_client

@pytest.fixture
def sample_slide_contents():
    """Sample slide contents for testing."""
    return {
        1: SlideContent(
            slide_number=1,
            text="Test slide 1 content",
            image_base64="base64encodedimage1",
            has_images=True,
            image_count=2
        ),
        2: SlideContent(
            slide_number=2,
            text="Test slide 2 content",
            image_base64="base64encodedimage2", 
            has_images=True,
            image_count=1
        ),
        3: SlideContent(
            slide_number=3,
            text="Test slide 3 content",
            image_base64=None,
            has_images=False,
            image_count=0
        ),
    }

@pytest.fixture
def sample_progress_state():
    """Sample processing state for resume testing."""
    return ProcessingState(
        file_path="/test/presentation.pdf",
        total_slides=10,
        completed_slides=5,
        slide_progress=[
            SlideProgress(slide_number=i, completed=True, character_count=1000, is_validated=True)
            for i in range(1, 6)
        ],
        last_validated_slide=5,
        output_path="/test/output.md",
        start_time=datetime.now(),
        last_update=datetime.now(),
        processing_mode="single",
        prompt_checksum="abc123",
        config_checksum="def456"
    )

@pytest.fixture
def sample_manifest_records():
    """Sample manifest records for batch testing."""
    return [
        FileRecord(
            filename="presentation1.pdf",
            input_path="/input/presentation1.pdf",
            output_path="/output/presentation1_summary.md",
            status=FileStatus.COMPLETED,
            total_slides=25,
            completed_slides=25,
            file_size=1024000,
            checksum="abc123"
        ),
        FileRecord(
            filename="presentation2.pdf", 
            input_path="/input/presentation2.pdf",
            output_path="/output/presentation2_summary.md",
            status=FileStatus.IN_PROGRESS,
            total_slides=15,
            completed_slides=8,
            file_size=512000,
            checksum="def456"
        ),
        FileRecord(
            filename="presentation3.pdf",
            input_path="/input/presentation3.pdf", 
            output_path="/output/presentation3_summary.md",
            status=FileStatus.PENDING,
            total_slides=0,
            completed_slides=0,
            file_size=2048000,
            checksum="ghi789"
        ),
    ]

@pytest.fixture
def mock_pdf_processor():
    """Mock PDF processor for testing."""
    mock_processor = Mock()
    mock_processor.extract_slide_content.return_value = {
        1: SlideContent(1, "Test content", "base64image", True, 1),
        2: SlideContent(2, "Test content 2", "base64image2", True, 1),
    }
    mock_processor.get_pdf_info.return_value = {
        'page_count': 2,
        'total_images': 2,
        'has_images': True
    }
    mock_processor.get_processing_summary.return_value = {
        'files_processed': 1,
        'files_list': ['test.pdf']
    }
    return mock_processor

@pytest.fixture
def mock_note_generator():
    """Mock note generator for testing."""
    mock_generator = Mock()
    mock_generator.generate_notes_for_slide_contents_resumable.return_value = "# Test Notes\n\nGenerated notes content"
    mock_generator.load_prompt_from_file.return_value = "Test prompt content"
    mock_generator.get_generation_summary.return_value = {
        'notes_generated': 2,
        'total_characters': 1000
    }
    return mock_generator

# Test data creation helpers
@pytest.fixture
def create_test_pdf(temp_dir):
    """Factory to create test PDF files."""
    def _create_pdf(filename: str, content: str = "Test PDF content") -> Path:
        pdf_path = temp_dir / filename
        # Create a minimal PDF-like file for testing
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n%Test PDF for unit testing\n')
            f.write(content.encode())
        return pdf_path
    return _create_pdf

@pytest.fixture
def create_test_prompt(temp_dir):
    """Factory to create test prompt files."""
    def _create_prompt(filename: str, content: str = "Test prompt content") -> Path:
        prompt_path = temp_dir / filename
        with open(prompt_path, 'w') as f:
            f.write(content)
        return prompt_path
    return _create_prompt