"""Note generation module for creating speaker notes from slides and prompts."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .llm_client import LLMClient, LLMError
    from .pdf_processor import SlideContent
except ImportError:
    from llm_client import LLMClient, LLMError
    from pdf_processor import SlideContent

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
        self.cumulative_context: List[str] = []
        self.processed_slides: List[int] = []

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

            logger.info(
                "Loaded prompt from %s (%d characters)", prompt_file, len(content)
            )
            return content

        except IOError as e:
            raise NoteGenerationError(
                f"Failed to read prompt file {prompt_file}: {str(e)}"
            ) from e

    def generate_notes_for_slide_content(
        self, slide_content: SlideContent, prompt: str
    ) -> str:
        """
        Generate speaker notes for a slide using multi-modal AI with cumulative context.

        Args:
            slide_content: SlideContent object with text and image data
            prompt: The user-provided prompt for note generation

        Returns:
            Generated speaker notes as a formatted string

        Raises:
            NoteGenerationError: If AI generation fails
        """
        slide_number = slide_content.slide_number
        logger.debug("Generating notes for slide %d (multi-modal: %s)", 
                    slide_number, slide_content.has_images)

        if self.use_ai and self.llm_client:
            try:
                # Build cumulative context from previous slides
                context = self._build_context()
                
                # Use AI to generate comprehensive notes
                logger.info("Requesting AI analysis for slide %d (context: %d chars, images: %s)...", 
                           slide_number, len(context), slide_content.has_images)
                
                ai_response = self.llm_client.generate_slide_analysis(
                    slide_content.text, 
                    prompt, 
                    slide_number,
                    context=context,
                    image_base64=slide_content.image_base64
                )
                
                logger.info(
                    "AI analysis completed for slide %d (%d chars)",
                    slide_number,
                    len(ai_response),
                )
                
                # Verify image descriptions if slide had images
                if slide_content.has_images:
                    self._verify_image_descriptions(ai_response, slide_number, slide_content.image_count)
                
                notes = ai_response + "\n---\n\n"
                
                # Add to cumulative context for future slides
                self._add_to_context(slide_number, slide_content.text, ai_response)

            except LLMError as e:
                logger.error("AI generation failed for slide %d: %s", slide_number, e)
                # Fallback to placeholder format
                notes = self._generate_placeholder_notes(
                    slide_number, slide_content.text, prompt, slide_content
                )

        else:
            # Use placeholder implementation
            notes = self._generate_placeholder_notes(
                slide_number, slide_content.text, prompt, slide_content
            )

        self.generated_notes.append(notes)
        self.processed_slides.append(slide_number)
        return notes
        
    def _build_context(self, max_context_slides: int = 3) -> str:
        """
        Build cumulative context from previous slides.
        
        Args:
            max_context_slides: Maximum number of previous slides to include
            
        Returns:
            Formatted context string
        """
        if not self.cumulative_context:
            return ""
            
        # Take the most recent slides for context
        recent_context = self.cumulative_context[-max_context_slides:]
        return "\n".join(recent_context)
    
    def _add_to_context(self, slide_number: int, slide_text: str, analysis: str) -> None:
        """
        Add slide summary to cumulative context.
        
        Args:
            slide_number: The slide number
            slide_text: Original slide text
            analysis: AI-generated analysis
        """
        # Extract key points for context (limit length)
        summary_lines = analysis.split('\n')[:5]  # First 5 lines as summary
        summary = '\n'.join(summary_lines)
        
        context_entry = f"Slide {slide_number}: {slide_text[:200]}...\nKey points: {summary[:300]}..."
        self.cumulative_context.append(context_entry)
        
        # Keep context manageable - limit to last 5 slides
        if len(self.cumulative_context) > 5:
            self.cumulative_context.pop(0)
    
    def _verify_image_descriptions(self, analysis: str, slide_number: int, expected_images: int) -> None:
        """
        Verify that image descriptions are present in the analysis.
        
        Args:
            analysis: Generated analysis text
            slide_number: Slide number for logging
            expected_images: Number of images detected in slide
        """
        # Look for image-related keywords in the analysis
        image_keywords = ['image', 'diagram', 'chart', 'graph', 'figure', 'picture', 'visual', 'shown', 'displays']
        
        analysis_lower = analysis.lower()
        image_mentions = sum(1 for keyword in image_keywords if keyword in analysis_lower)
        
        if expected_images > 0 and image_mentions == 0:
            logger.warning(
                "Slide %d has %d images but no image descriptions found in analysis",
                slide_number, expected_images
            )
        else:
            logger.debug(
                "Slide %d: Found %d image-related mentions for %d detected images",
                slide_number, image_mentions, expected_images
            )

    def generate_notes_for_slide(
        self, slide_number: int, slide_text: str, prompt: str
    ) -> str:
        """
        Legacy method for backward compatibility - generates notes for text-only slides.
        """
        slide_content = SlideContent(
            slide_number=slide_number,
            text=slide_text,
            image_base64=None,
            has_images=False,
            image_count=0
        )
        return self.generate_notes_for_slide_content(slide_content, prompt)

    def _generate_placeholder_notes(
        self, slide_number: int, slide_text: str, prompt: str, slide_content: SlideContent = None
    ) -> str:
        """
        Generate placeholder notes in the expected format.

        Args:
            slide_number: The slide number
            slide_text: The slide text content
            prompt: The analysis prompt
            slide_content: Optional SlideContent for image information

        Returns:
            Formatted placeholder notes
        """
        image_info = "[AI vision analysis not available - placeholder mode]"
        if slide_content and slide_content.has_images:
            image_info = f"[{slide_content.image_count} image(s) detected but AI vision analysis not available - placeholder mode]"
            
        return (
            f"#### Slide: Slide {slide_number}\n\n"
            f"**Slide Number:** {slide_number}\n\n"
            f"**Slide Text:**\n{slide_text}\n\n"
            f"**Slide Images/Diagrams:**\n"
            f"{image_info}\n\n"
            f"**Slide Topics:**\n"
            f"*   [AI topic extraction not available - placeholder mode]\n\n"
            f"**Slide Narration:**\n"
            f'"[AI-generated narration not available - placeholder mode]"\n\n'
            f"---\n\n"
        )
        
    def generate_notes_for_slide_contents(
        self, slide_contents: Dict[int, SlideContent], prompt: str
    ) -> str:
        """
        Generate notes for multiple slides with verification and range processing.
        
        Args:
            slide_contents: Dictionary of slide number to SlideContent
            prompt: The user-provided prompt
            
        Returns:
            Combined notes for all slides
        """
        total_slides = len(slide_contents)
        logger.info("Generating notes for %d slides with multi-modal support", total_slides)
        
        all_notes = []
        
        # Process slides in order
        for slide_num in sorted(slide_contents.keys()):
            slide_content = slide_contents[slide_num]
            
            notes = self.generate_notes_for_slide_content(slide_content, prompt)
            all_notes.append(notes)
            
            # Log progress
            if slide_num % 5 == 0 or slide_num == total_slides:
                logger.info("Processed %d/%d slides", slide_num, total_slides)
        
        # Verify all slides were processed
        self._verify_complete_processing(slide_contents)
        
        combined_notes = "".join(all_notes)
        logger.info("Generated %d characters of notes for %d slides", 
                   len(combined_notes), total_slides)
        
        return combined_notes

    def generate_notes_for_slide_contents_resumable(
        self, 
        slide_contents: Dict[int, SlideContent], 
        prompt: str,
        progress_manager,
        start_from_slide: int = 1
    ) -> str:
        """
        Generate notes with resume capability and progress tracking.
        
        Args:
            slide_contents: Dictionary of slide content
            prompt: Generation prompt
            progress_manager: Progress tracking manager
            start_from_slide: Slide number to start/resume from
            
        Returns:
            Generated notes string
        """
        logger.info(f"Starting note generation from slide {start_from_slide} of {len(slide_contents)} total slides")
        
        # Update progress manager with total slides
        progress_manager.update_total_slides(len(slide_contents))
        
        # Load existing content if resuming
        existing_notes = []
        if start_from_slide > 1 and progress_manager.output_path and progress_manager.output_path.exists():
            try:
                with open(progress_manager.output_path, 'r') as f:
                    existing_content = f.read()
                    existing_notes.append(existing_content)
                    logger.info(f"Loaded existing content ({len(existing_content)} chars)")
            except Exception as e:
                logger.error(f"Failed to load existing content: {e}")
        
        # Process slides from resume point
        new_notes = []
        processed_count = start_from_slide - 1
        
        try:
            for slide_num in range(start_from_slide, len(slide_contents) + 1):
                if slide_num not in slide_contents:
                    logger.warning(f"Slide {slide_num} not found in content, skipping")
                    continue
                    
                slide_content = slide_contents[slide_num]
                
                # Build cumulative context for this slide
                context = self._build_context_for_slide(slide_num, max_context_chars=2000)
                
                logger.info(f"Requesting AI analysis for slide {slide_num} (context: {len(context)} chars, images: {slide_content.has_images})...")
                
                try:
                    # Generate analysis for this slide
                    if self.use_ai and self.llm_client:
                        slide_analysis = self.llm_client.generate_slide_analysis(
                            slide_content.text,
                            prompt,
                            slide_num,
                            context=context,
                            image_base64=slide_content.image_base64
                        )
                    else:
                        # Fallback to placeholder
                        slide_analysis = self._generate_placeholder_notes(
                            slide_num, slide_content.text, prompt, slide_content
                        )
                    
                    # Validate generated content
                    if not self._validate_generated_content(slide_analysis, slide_num):
                        raise NoteGenerationError(f"Generated content for slide {slide_num} failed validation")
                    
                    logger.info(f"AI analysis completed for slide {slide_num} ({len(slide_analysis)} chars)")
                    
                    # Format the slide analysis
                    formatted_analysis = self._format_slide_analysis(slide_analysis, slide_num, slide_content)
                    new_notes.append(formatted_analysis)
                    
                    # Update context history for next slide
                    self._add_to_context_history(slide_num, slide_content.text, slide_analysis)
                    
                    # Checkpoint progress
                    progress_manager.checkpoint_slide(slide_num, formatted_analysis, slide_content)
                    
                    processed_count += 1
                    
                    # Progress logging
                    if processed_count % 5 == 0:
                        logger.info(f"Processed {processed_count}/{len(slide_contents)} slides")
                        
                except Exception as e:
                    logger.error(f"Failed to generate analysis for slide {slide_num}: {e}")
                    # Save error state but continue processing
                    progress_manager.record_slide_error(slide_num, str(e))
                    raise NoteGenerationError(f"Failed to process slide {slide_num}: {e}")
        
        except KeyboardInterrupt:
            logger.info(f"Processing interrupted by user at slide {slide_num}")
            logger.info(f"Progress saved. Resume with same command to continue from slide {slide_num}")
            raise
        
        except Exception as e:
            logger.error(f"Critical error during processing: {e}")
            raise
        
        # Combine existing and new content
        all_notes = existing_notes + new_notes
        final_content = "".join(all_notes)
        
        # Final validation
        self._validate_complete_output(final_content, len(slide_contents))
        
        # Update completion statistics
        self.stats = getattr(self, 'stats', {})
        self.stats['notes_generated'] = len(slide_contents)
        self.stats['total_characters'] = len(final_content)
        
        logger.info(f"Note generation completed: {len(slide_contents)} slides, {len(final_content)} characters")
        
        return final_content

    def _build_context_for_slide(self, slide_num: int, max_context_chars: int = 2000) -> str:
        """
        Build cumulative context for a specific slide.
        
        Args:
            slide_num: Current slide number
            max_context_chars: Maximum characters for context
            
        Returns:
            Formatted context string
        """
        if not self.cumulative_context:
            return ""
        
        # Build context from recent slides, respecting character limit
        context_parts = []
        char_count = 0
        
        # Work backwards from most recent slides
        for context_entry in reversed(self.cumulative_context):
            if char_count + len(context_entry) > max_context_chars:
                break
            context_parts.insert(0, context_entry)
            char_count += len(context_entry)
        
        return "\n\n".join(context_parts)

    def _add_to_context_history(self, slide_number: int, slide_text: str, analysis: str) -> None:
        """
        Add slide summary to cumulative context.
        
        Args:
            slide_number: The slide number
            slide_text: Original slide text
            analysis: AI-generated analysis
        """
        # Extract key points for context (limit length)
        summary_lines = analysis.split('\n')[:5]  # First 5 lines as summary
        summary = '\n'.join(summary_lines)
        
        context_entry = f"Slide {slide_number}: {slide_text[:200]}...\nKey points: {summary[:300]}..."
        self.cumulative_context.append(context_entry)
        
        # Keep context manageable - limit to last 5 slides
        if len(self.cumulative_context) > 5:
            self.cumulative_context.pop(0)

    def _validate_generated_content(self, content: str, slide_num: int) -> bool:
        """Validate individual slide content meets quality standards."""
        # In no-AI mode, use relaxed validation for placeholder content
        if not self.use_ai:
            if len(content.strip()) < 50:  # More lenient for placeholders
                logger.warning(f"Slide {slide_num} content too short ({len(content)} chars)")
                return False
            # Just check basic structure exists
            return '**Slide Number:**' in content
        
        # Full validation for AI-generated content
        if len(content.strip()) < 100:  # Minimum reasonable length
            logger.warning(f"Slide {slide_num} content too short ({len(content)} chars)")
            return False
        
        # Check for required sections
        required_sections = [
            '**Slide Number:**',
            '**Slide Text:**', 
            '**Slide Images/Diagrams:**',
            '**Slide Topics:**',
            '**Slide Narration:**'
        ]
        
        missing_sections = [section for section in required_sections if section not in content]
        if missing_sections:
            logger.warning(f"Slide {slide_num} missing sections: {missing_sections}")
            return False
        
        # Check for reasonable narration length
        narration_start = content.find('**Slide Narration:**')
        if narration_start > -1:
            narration_content = content[narration_start:].split('---')[0]
            if len(narration_content.strip()) < 200:  # Minimum narration length
                logger.warning(f"Slide {slide_num} narration too short")
                return False
        
        return True

    def _validate_complete_output(self, content: str, expected_slides: int) -> None:
        """Validate the complete output meets quality standards."""
        # Count slide sections
        slide_count = content.count('**Slide Number:**')
        if slide_count != expected_slides:
            raise NoteGenerationError(f"Output contains {slide_count} slides, expected {expected_slides}")
        
        # Check overall length is reasonable (more lenient for no-AI mode)
        avg_chars_per_slide = len(content) / expected_slides
        min_chars_per_slide = 100 if not self.use_ai else 500  # Relaxed for placeholders
        if avg_chars_per_slide < min_chars_per_slide:
            logger.warning(f"Average content per slide is low ({avg_chars_per_slide:.0f} chars)")
        
        logger.info(f"Output validation passed: {slide_count} slides, {len(content)} total characters")

    def _format_slide_analysis(self, analysis: str, slide_num: int, slide_content) -> str:
        """Format slide analysis with consistent structure."""
        # If analysis already has proper formatting, return as-is
        if '**Slide Number:**' in analysis:
            return analysis + '\n---\n\n'
        
        # Otherwise, wrap in standard format
        return f"""#### Slide {slide_num}

{analysis}

---

"""
    
    def _verify_complete_processing(self, expected_slides: Dict[int, SlideContent]) -> None:
        """
        Verify that all slides were processed and contain appropriate content.
        
        Args:
            expected_slides: Dictionary of expected slide numbers to content
        """
        expected_nums = set(expected_slides.keys())
        processed_nums = set(self.processed_slides)
        
        missing_slides = expected_nums - processed_nums
        if missing_slides:
            logger.error("Missing slides in processing: %s", sorted(missing_slides))
            raise NoteGenerationError(f"Failed to process slides: {sorted(missing_slides)}")
        
        # Check for slides with images that should have descriptions
        slides_with_images = [
            num for num, content in expected_slides.items() 
            if content.has_images
        ]
        
        if slides_with_images:
            logger.info("Processed %d slides with images: %s", 
                       len(slides_with_images), slides_with_images)
        
        # Verify image descriptions exist for slides with images
        missing_descriptions = []
        for slide_num in slides_with_images:
            # Check if the corresponding note mentions images
            slide_index = slide_num - 1
            if slide_index < len(self.generated_notes):
                note_content = self.generated_notes[slide_index].lower()
                image_keywords = ['image', 'diagram', 'chart', 'graph', 'figure', 'visual']
                if not any(keyword in note_content for keyword in image_keywords):
                    missing_descriptions.append(slide_num)
        
        if missing_descriptions:
            logger.warning(
                "Slides with images but no descriptions: %s", 
                missing_descriptions
            )
            
        logger.info("Processing verification complete: %d/%d slides processed successfully", 
                   len(processed_nums), len(expected_nums))

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
        total_slides = sum(len(page_texts) for page_texts in pdf_data.values())
        logger.info(
            "Generating notes for %d PDF files (%d total slides)",
            len(pdf_data),
            total_slides,
        )

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
