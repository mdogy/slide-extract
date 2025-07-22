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
        self, slide_text: str, prompt: str, slide_number: int
    ) -> str:
        """
        Generate analysis for a single slide using the configured LLM.

        Args:
            slide_text: Extracted text from the slide
            prompt: Analysis prompt/instructions
            slide_number: Slide number for context

        Returns:
            Generated slide analysis

        Raises:
            LLMError: If generation fails
        """
        try:
            # Create the full prompt
            full_prompt = self._create_slide_prompt(slide_text, prompt, slide_number)

            # Generate response based on provider
            if self.provider == "openai" or self.provider == "openrouter":
                return self._generate_openai_response(full_prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic_response(full_prompt)
            elif self.provider == "google":
                return self._generate_google_response(full_prompt)
            else:
                raise LLMError(
                    f"Generation not implemented for provider: {self.provider}"
                )

        except Exception as e:
            logger.error("Failed to generate slide analysis: %s", e)
            raise LLMError(f"Failed to generate slide analysis: {e}") from e

    def _create_slide_prompt(
        self, slide_text: str, prompt: str, slide_number: int
    ) -> str:
        """Create a complete prompt for slide analysis."""
        return f"""
{prompt}

## Slide to Analyze

**Slide Number:** {slide_number}
**Slide Content:** 
{slide_text}

Please provide a comprehensive analysis following the format specified in the prompt above.
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
