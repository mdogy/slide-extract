"""Note generation module for creating speaker notes from slides and prompts."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .llm_client import LLMClient, LLMError
except ImportError:
    from llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)


class NoteGenerationError(Exception):
    """Custom exception for note generation errors."""


class NoteGenerator:
    """Handles generation of speaker notes from slide content and user prompts."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize the note generator.
        
        Args:
            llm_client: LLM client for AI-powered note generation
        """
        self.generated_notes: List[str] = []
        self.llm_client = llm_client
        self.use_ai = llm_client is not None

    def load_prompt_from_file(self, prompt_file: Path) -> str:
        """
        Load the user prompt from a Markdown file.

        Args:
            prompt_file: Path to the Markdown file containing the prompt

        Returns:
            The content of the prompt file as a string

        Raises:
            NoteGenerationError: If the prompt file cannot be read
        """
        if not prompt_file.exists():
            raise NoteGenerationError(f"Prompt file not found: {prompt_file}")

        if prompt_file.suffix.lower() not in [".md", ".markdown"]:
            logger.warning("Prompt file %s is not a Markdown file", prompt_file)

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                raise NoteGenerationError(f"Prompt file is empty: {prompt_file}")

            logger.info("Loaded prompt from %s (%d characters)", prompt_file, len(content))
            return content

        except IOError as e:
            raise NoteGenerationError(
                f"Failed to read prompt file {prompt_file}: {str(e)}"
            ) from e

    def generate_notes_for_slide(
        self, slide_number: int, slide_text: str, prompt: str
    ) -> str:
        """
        Generate speaker notes for a single slide using AI or placeholder.

        Args:
            slide_number: The slide number (1-indexed)
            slide_text: The extracted text content from the slide
            prompt: The user-provided prompt for note generation

        Returns:
            Generated speaker notes as a formatted string
            
        Raises:
            NoteGenerationError: If AI generation fails
        """
        logger.debug("Generating notes for slide %d", slide_number)

        if self.use_ai and self.llm_client:
            try:
                # Use AI to generate comprehensive notes
                ai_response = self.llm_client.generate_slide_analysis(
                    slide_text, prompt, slide_number
                )
                notes = ai_response + "\n---\n\n"
                
            except LLMError as e:
                logger.error("AI generation failed for slide %d: %s", slide_number, e)
                # Fallback to placeholder format
                notes = self._generate_placeholder_notes(slide_number, slide_text, prompt)
                
        else:
            # Use placeholder implementation
            notes = self._generate_placeholder_notes(slide_number, slide_text, prompt)

        self.generated_notes.append(notes)
        return notes
        
    def _generate_placeholder_notes(self, slide_number: int, slide_text: str, prompt: str) -> str:
        """
        Generate placeholder notes in the expected format.
        
        Args:
            slide_number: The slide number
            slide_text: The slide text content
            prompt: The analysis prompt
            
        Returns:
            Formatted placeholder notes
        """
        return (
            f"#### Slide: Slide {slide_number}\n\n"
            f"**Slide Number:** {slide_number}\n\n"
            f"**Slide Text:**\n{slide_text}\n\n"
            f"**Slide Images/Diagrams:**\n"
            f"[AI vision analysis not available - placeholder mode]\n\n"
            f"**Slide Topics:**\n"
            f"*   [AI topic extraction not available - placeholder mode]\n\n"
            f"**Slide Narration:**\n"
            f'"[AI-generated narration not available - placeholder mode]"\n\n'
            f"---\n\n"
        )

        self.generated_notes.append(notes)
        return notes

    def generate_notes_for_pdf(
        self, pdf_path: str, page_texts: Dict[int, str], prompt: str
    ) -> List[str]:
        """
        Generate notes for all slides in a PDF.

        Args:
            pdf_path: Path to the source PDF file
            page_texts: Dictionary mapping page numbers to extracted text
            prompt: The user-provided prompt

        Returns:
            List of generated notes for each slide
        """
        logger.info("Generating notes for %d slides from %s", len(page_texts), pdf_path)

        pdf_notes = []

        # Add header for this PDF
        header = f"# Notes for {Path(pdf_path).name}\n\n"
        pdf_notes.append(header)

        # Generate notes for each slide
        for slide_num in sorted(page_texts.keys()):
            slide_text = page_texts[slide_num]
            notes = self.generate_notes_for_slide(slide_num, slide_text, prompt)
            pdf_notes.append(notes)

        logger.info("Generated notes for %d slides", len(page_texts))
        return pdf_notes

    def generate_notes_for_multiple_pdfs(
        self, pdf_data: Dict[str, Dict[int, str]], prompt: str
    ) -> str:
        """
        Generate notes for multiple PDF files.

        Args:
            pdf_data: Dictionary mapping PDF paths to their page texts
            prompt: The user-provided prompt

        Returns:
            Combined notes for all PDFs as a single string
        """
        logger.info("Generating notes for %d PDF files", len(pdf_data))

        all_notes = []

        for pdf_path, page_texts in pdf_data.items():
            pdf_notes = self.generate_notes_for_pdf(pdf_path, page_texts, prompt)
            all_notes.extend(pdf_notes)

        combined_notes = "".join(all_notes)

        logger.info("Generated %d characters of notes", len(combined_notes))
        return combined_notes

    def write_notes_to_file(self, notes: str, output_file: Path) -> None:
        """
        Write generated notes to an output file.

        Args:
            notes: The generated notes content
            output_file: Path to the output file

        Raises:
            NoteGenerationError: If the file cannot be written
        """
        try:
            # Ensure parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(notes)

            logger.info("Notes written to %s (%d characters)", output_file, len(notes))

        except IOError as e:
            raise NoteGenerationError(
                f"Failed to write notes to {output_file}: {str(e)}"
            ) from e

    def get_generation_summary(self) -> Dict[str, int]:
        """
        Get a summary of note generation results.

        Returns:
            Dictionary with generation statistics
        """
        total_chars = sum(len(note) for note in self.generated_notes)
        return {
            "notes_generated": len(self.generated_notes),
            "total_characters": total_chars,
        }
