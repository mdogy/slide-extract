"""LLM client for integrating with various language model providers."""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM-related errors."""


class LLMClient:
    """Unified client for various LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM client with configuration.

        Args:
            config: LLM configuration dictionary
        """
        self.config = config
        self.provider = config.get("provider")
        self.model = config.get("model")
        self.api_key = config.get("api_key")
        self.max_tokens = config.get("max_tokens", 4000)
        self.temperature = config.get("temperature", 0.3)

        if not self.provider:
            raise LLMError("No LLM provider specified")
        if not self.api_key:
            raise LLMError(f"No API key provided for {self.provider}")

        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate client based on provider."""
        try:
            if self.provider == "openai":
                import openai

                return openai.OpenAI(api_key=self.api_key)

            elif self.provider == "anthropic":
                import anthropic

                return anthropic.Anthropic(api_key=self.api_key)

            elif self.provider == "google":
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                return genai.GenerativeModel(self.model)

            elif self.provider == "openrouter":
                import openai

                base_url = self.config.get("base_url", "https://openrouter.ai/api/v1")
                return openai.OpenAI(api_key=self.api_key, base_url=base_url)

            else:
                raise LLMError(f"Unsupported LLM provider: {self.provider}")

        except ImportError as e:
            raise LLMError(
                f"Required library not installed for {self.provider}. "
                f"Please install required dependencies: {e}"
            ) from e

    def generate_slide_analysis(
        self, slide_text: str, prompt: str, slide_number: int, 
        context: str = "", image_base64: str = None
    ) -> str:
        """
        Generate analysis for a single slide using the configured LLM.

        Args:
            slide_text: Extracted text from the slide
            prompt: Analysis prompt/instructions
            slide_number: Slide number for context
            context: Cumulative context from previous slides
            image_base64: Base64-encoded image of the slide (for multi-modal)

        Returns:
            Generated slide analysis

        Raises:
            LLMError: If generation fails
        """
        try:
            # Create the full prompt with context
            full_prompt = self._create_slide_prompt(slide_text, prompt, slide_number, context)

            # Generate response based on provider and modality
            if image_base64 and self._supports_vision():
                return self._generate_multimodal_response(full_prompt, image_base64)
            else:
                return self._generate_text_response(full_prompt)

        except Exception as e:
            logger.error("Failed to generate slide analysis: %s", e)
            raise LLMError(f"Failed to generate slide analysis: {e}") from e
            
    def _supports_vision(self) -> bool:
        """Check if the current provider/model supports vision capabilities."""
        vision_models = {
            'openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-vision-preview'],
            'anthropic': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
            'google': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro-vision'],
            'openrouter': []  # Most models on OpenRouter support vision if they're GPT-4o or Claude-3
        }
        
        if self.provider not in vision_models:
            return False
            
        if self.provider == 'openrouter':
            # For OpenRouter, check if model name contains known vision models
            vision_keywords = ['gpt-4o', 'claude-3', 'gemini', 'vision']
            return any(keyword in self.model.lower() for keyword in vision_keywords)
        
        return self.model in vision_models[self.provider]

    def _generate_multimodal_response(self, prompt: str, image_base64: str) -> str:
        """Generate response using both text and image input."""
        if self.provider == "openai" or self.provider == "openrouter":
            return self._generate_openai_vision_response(prompt, image_base64)
        elif self.provider == "anthropic":
            return self._generate_anthropic_vision_response(prompt, image_base64)
        elif self.provider == "google":
            return self._generate_google_vision_response(prompt, image_base64)
        else:
            raise LLMError(f"Multi-modal generation not supported for provider: {self.provider}")
    
    def _generate_text_response(self, prompt: str) -> str:
        """Generate text-only response."""
        if self.provider == "openai" or self.provider == "openrouter":
            return self._generate_openai_response(prompt)
        elif self.provider == "anthropic":
            return self._generate_anthropic_response(prompt)
        elif self.provider == "google":
            return self._generate_google_response(prompt)
        else:
            raise LLMError(f"Generation not implemented for provider: {self.provider}")

    def _create_slide_prompt(
        self, slide_text: str, prompt: str, slide_number: int, context: str = ""
    ) -> str:
        """Create a complete prompt for slide analysis with context."""
        context_section = ""
        if context:
            context_section = f"""
## Previous Slides Context

{context}

---
"""
        
        return f"""
{prompt}

{context_section}
## Current Slide to Analyze

**Slide Number:** {slide_number}
**Slide Text Content:** 
{slide_text}

Please provide a comprehensive analysis following the format specified in the prompt above. 
Consider the context from previous slides when analyzing this slide.
"""

    def _generate_openai_response(self, prompt: str) -> str:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            if not response.choices:
                raise LLMError("No response choices returned from OpenAI")

            content = response.choices[0].message.content
            if not content:
                raise LLMError("Empty response content from OpenAI")

            return content.strip()

        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}") from e

    def _generate_anthropic_response(self, prompt: str) -> str:
        """Generate response using Anthropic Claude API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            if not response.content:
                raise LLMError("No response content returned from Anthropic")

            # Handle Anthropic's response format
            content = response.content[0].text if response.content else ""
            if not content:
                raise LLMError("Empty response content from Anthropic")

            return content.strip()

        except Exception as e:
            raise LLMError(f"Anthropic API error: {e}") from e

    def _generate_google_response(self, prompt: str) -> str:
        """Generate response using Google Gemini API."""
        try:
            # Configure generation parameters
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

            response = self.client.generate_content(
                prompt, generation_config=generation_config
            )

            if not response.text:
                raise LLMError("No response text returned from Google")

            return response.text.strip()

        except Exception as e:
            raise LLMError(f"Google API error: {e}") from e
            
    def _generate_openai_vision_response(self, prompt: str, image_base64: str) -> str:
        """Generate response using OpenAI Vision API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            if not response.choices:
                raise LLMError("No response choices returned from OpenAI Vision")

            content = response.choices[0].message.content
            if not content:
                raise LLMError("Empty response content from OpenAI Vision")

            return content.strip()

        except Exception as e:
            raise LLMError(f"OpenAI Vision API error: {e}") from e

    def _generate_anthropic_vision_response(self, prompt: str, image_base64: str) -> str:
        """Generate response using Anthropic Claude Vision API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64,
                                },
                            },
                        ],
                    }
                ],
            )

            if not response.content:
                raise LLMError("No response content returned from Anthropic Vision")

            content = response.content[0].text if response.content else ""
            if not content:
                raise LLMError("Empty response content from Anthropic Vision")

            return content.strip()

        except Exception as e:
            raise LLMError(f"Anthropic Vision API error: {e}") from e

    def _generate_google_vision_response(self, prompt: str, image_base64: str) -> str:
        """Generate response using Google Gemini Vision API."""
        try:
            import base64
            
            # Convert base64 to bytes for Gemini
            image_bytes = base64.b64decode(image_base64)
            
            # Configure generation parameters
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

            response = self.client.generate_content(
                [prompt, {"mime_type": "image/png", "data": image_bytes}],
                generation_config=generation_config
            )

            if not response.text:
                raise LLMError("No response text returned from Google Vision")

            return response.text.strip()

        except Exception as e:
            raise LLMError(f"Google Vision API error: {e}") from e

    def test_connection(self) -> bool:
        """
        Test the connection to the LLM provider.

        Returns:
            True if connection successful, False otherwise
        """
        test_prompt = "Hello! Please respond with 'Connection successful' if you can see this message."

        try:
            response = self.generate_slide_analysis(
                "Test slide content", test_prompt, 1
            )
            logger.info("LLM connection test successful for %s", self.provider)
            return "successful" in response.lower()
        except Exception as e:
            logger.error("LLM connection test failed for %s: %s", self.provider, e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured model.

        Returns:
            Dictionary with model information
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        config: LLM configuration dictionary

    Returns:
        Configured LLM client
    """
    return LLMClient(config)
