"""PDF processing module for extracting text and images from presentation slides."""

import base64
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        "PyMuPDF is required for PDF processing. "
        "Install it with: pip install PyMuPDF"
    ) from e

try:
    from PIL import Image
except ImportError:
    # Try importing without the PIL prefix (fallback)
    try:
        import PIL.Image as Image
    except ImportError as e:
        raise ImportError(
            "Pillow is required for image processing. "
            "Install it with: pip install Pillow"
        ) from e


logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""


class SlideContent(NamedTuple):
    """Container for slide content including text and visual elements."""
    slide_number: int
    text: str
    image_base64: Optional[str] = None
    has_images: bool = False
    image_count: int = 0


class PDFProcessor:
    """Handles extraction of text and visual content from PDF files."""

    def __init__(self):
        """Initialize the PDF processor."""
        self.processed_files: List[str] = []

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from each page of a PDF file.

        Args:
            pdf_path: Path to the PDF file to process

        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text

        Raises:
            PDFProcessingError: If PDF cannot be opened or processed
        """
        if not pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {pdf_path}")

        logger.info("Processing PDF: %s", pdf_path)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as open_error:
            raise PDFProcessingError(
                f"Failed to open PDF {pdf_path}: {str(open_error)}"
            ) from open_error

        page_texts = {}

        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()

                # Clean up the text
                text = self._clean_text(text)

                page_texts[page_num + 1] = text  # 1-indexed page numbers
                logger.debug(
                    "Extracted %d characters from page %d", len(text), page_num + 1
                )

        except Exception as extraction_error:
            raise PDFProcessingError(
                f"Failed to extract text from PDF {pdf_path}: {str(extraction_error)}"
            ) from extraction_error
        finally:
            doc.close()

        self.processed_files.append(str(pdf_path))
        logger.info(
            "Successfully processed %d pages from %s", len(page_texts), pdf_path
        )

        return page_texts

    def extract_slide_content(self, pdf_path: Path) -> Dict[int, SlideContent]:
        """
        Extract both text and visual content from each page of a PDF file.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            Dictionary mapping page numbers to SlideContent objects
            
        Raises:
            PDFProcessingError: If PDF cannot be opened or processed
        """
        if not pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {pdf_path}")

        logger.info("Processing PDF with multi-modal support: %s", pdf_path)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as open_error:
            raise PDFProcessingError(
                f"Failed to open PDF {pdf_path}: {str(open_error)}"
            ) from open_error

        slide_contents = {}

        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                slide_number = page_num + 1
                
                # Extract text
                text = self._clean_text(page.get_text())
                logger.debug("Extracted %d characters from page %d", len(text), slide_number)
                
                # Check for visual content (images + drawings + charts)
                image_list = page.get_images()
                drawings = page.get_drawings()
                
                # Consider slide to have visual content if it has images, drawings, or visual elements
                has_visual_content = len(image_list) > 0 or len(drawings) > 0
                total_visual_elements = len(image_list) + len(drawings)
                image_base64 = None
                
                if has_visual_content:
                    logger.debug("Found %d images and %d drawings on slide %d", 
                                len(image_list), len(drawings), slide_number)
                    # Always render the entire page as an image for comprehensive visual analysis
                    image_base64 = self._render_page_as_image(page)
                else:
                    # Even for "text-only" slides, render as image to capture formatting, layout, fonts
                    logger.debug("Rendering text-only slide %d as image for layout analysis", slide_number)
                    image_base64 = self._render_page_as_image(page)
                
                slide_contents[slide_number] = SlideContent(
                    slide_number=slide_number,
                    text=text,
                    image_base64=image_base64,
                    has_images=has_visual_content,
                    image_count=total_visual_elements
                )

        except Exception as extraction_error:
            raise PDFProcessingError(
                f"Failed to extract content from PDF {pdf_path}: {str(extraction_error)}"
            ) from extraction_error
        finally:
            doc.close()

        self.processed_files.append(str(pdf_path))
        slides_with_visual = sum(1 for sc in slide_contents.values() if sc.has_images)
        total_visual_elements = sum(sc.image_count for sc in slide_contents.values())
        logger.info(
            "Successfully processed %d slides from %s (%d with visual content, %d total visual elements)", 
            len(slide_contents), 
            pdf_path,
            slides_with_visual,
            total_visual_elements
        )

        return slide_contents

    def _render_page_as_image(self, page, dpi: int = 150) -> str:
        """
        Render a PDF page as a base64-encoded image.
        
        Args:
            page: PyMuPDF page object
            dpi: Resolution for image rendering
            
        Returns:
            Base64-encoded image string
        """
        try:
            # Render page as image
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # scaling factor
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.debug("Rendered page as %dx%d image (%d bytes)", 
                        img.width, img.height, len(img_base64))
            
            return img_base64
            
        except Exception as e:
            logger.error("Failed to render page as image: %s", e)
            return None

    def get_pdf_info(self, pdf_path: Path) -> Dict[str, any]:
        """
        Get basic information about a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with PDF metadata
        """
        try:
            doc = fitz.open(str(pdf_path))
            info = {
                'page_count': doc.page_count,
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'has_images': False,
                'total_images': 0
            }
            
            # Count total images across all pages
            total_images = 0
            for page_num in range(doc.page_count):
                page = doc[page_num]
                image_list = page.get_images()
                total_images += len(image_list)
                if len(image_list) > 0:
                    info['has_images'] = True
            
            info['total_images'] = total_images
            doc.close()
            
            logger.info("PDF info: %d pages, %d total images", 
                       info['page_count'], info['total_images'])
            
            return info
            
        except Exception as e:
            logger.error("Failed to get PDF info: %s", e)
            return {'page_count': 0, 'has_images': False, 'total_images': 0}

    def process_multiple_pdfs(self, pdf_paths: List[Path]) -> Dict[str, Dict[int, str]]:
        """
        Process multiple PDF files and extract text from all pages.

        Args:
            pdf_paths: List of paths to PDF files

        Returns:
            Dictionary mapping file paths to page dictionaries

        Raises:
            PDFProcessingError: If any PDF cannot be processed
        """
        results = {}

        for pdf_path in pdf_paths:
            try:
                page_texts = self.extract_text_from_pdf(pdf_path)
                results[str(pdf_path)] = page_texts
            except PDFProcessingError:
                logger.error("Failed to process PDF: %s", pdf_path)
                raise

        logger.info("Successfully processed %d PDF files", len(results))
        return results

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and normalizing.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        import re

        if not text:
            return ""

        # Replace multiple whitespace characters with single spaces

        text = re.sub(r"\s+", " ", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def get_processing_summary(self) -> Dict[str, int]:
        """
        Get a summary of processing results.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "files_processed": len(self.processed_files),
            "files_list": self.processed_files.copy(),
        }
