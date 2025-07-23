#!/usr/bin/env python3
"""Quick test for slide 8 visual analysis"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from slide_extract.core.pdf_processor import PDFProcessor
from slide_extract.core.note_generator import NoteGenerator  
from slide_extract.core.config_manager import ConfigManager
from slide_extract.core.llm_client import create_llm_client

def test_slide_8():
    # Initialize components
    config_manager = ConfigManager()
    llm_config = config_manager.get_llm_config()
    llm_client = create_llm_client(llm_config)
    
    pdf_processor = PDFProcessor()
    note_generator = NoteGenerator(llm_client)
    
    # Process PDF
    pdf_path = Path("tests/M01_23_08_31_A_Intro.pdf")
    slide_contents = pdf_processor.extract_slide_content(pdf_path)
    
    # Load prompt
    prompt_path = Path("src/slide_extract/prompts/default_prompt.md")
    prompt_text = note_generator.load_prompt_from_file(prompt_path)
    
    # Generate notes for slide 8 only
    slide_8_content = slide_contents[8]
    print(f"Slide 8 has_images: {slide_8_content.has_images}")
    print(f"Slide 8 image_count: {slide_8_content.image_count}")
    print(f"Slide 8 text: {slide_8_content.text}")
    
    # Generate analysis for slide 8
    slide_8_notes = note_generator.generate_notes_for_slide_content(slide_8_content, prompt_text)
    
    print("\n=== SLIDE 8 ANALYSIS ===")
    print(slide_8_notes)

if __name__ == "__main__":
    test_slide_8()