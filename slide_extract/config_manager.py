"""Configuration and API key management for LLM integration."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError as e:
    raise ImportError(
        "PyYAML is required for configuration management. "
        "Install it with: pip install pyyaml"
    ) from e


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""


class ConfigManager:
    """Handles configuration loading and API key management."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default.
        """
        self.config_path = config_path or Path("config.yaml")
        self.config: Dict[str, Any] = {}
        self.api_keys: Dict[str, str] = {}
        
    def load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
                
            logger.info("Loaded configuration from %s", self.config_path)
            
            # Validate required sections
            if 'llm' not in self.config:
                raise ConfigurationError("Missing 'llm' section in configuration")
                
            return self.config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    def load_api_keys(self) -> Dict[str, str]:
        """
        Load API keys from environment file in home directory.
        
        Returns:
            Dictionary of API keys
            
        Raises:
            ConfigurationError: If API keys cannot be loaded
        """
        # Try multiple locations for API keys
        key_file_locations = [
            Path.home() / ".slide_extract_keys.env",
            Path.home() / ".config" / "slide-extract" / "keys.env",
            Path(".env"),  # Local fallback for development
        ]
        
        key_file = None
        for location in key_file_locations:
            if location.exists():
                key_file = location
                break
                
        if not key_file:
            # Try environment variables directly
            self.api_keys = self._load_from_environment()
            if self.api_keys:
                logger.info("Loaded API keys from environment variables")
                return self.api_keys
            else:
                raise ConfigurationError(
                    f"No API key file found in any of these locations: "
                    f"{', '.join(str(loc) for loc in key_file_locations)}\n"
                    f"Please create ~/.slide_extract_keys.env with your API keys."
                )
        
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if '=' not in line:
                        logger.warning("Invalid line %d in %s: %s", line_num, key_file, line)
                        continue
                        
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if key and value:
                        self.api_keys[key] = value
                        
            logger.info("Loaded API keys from %s", key_file)
            return self.api_keys
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load API keys from {key_file}: {e}") from e
    
    def _load_from_environment(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        env_keys = {}
        api_key_names = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 
            'GOOGLE_AI_API_KEY',
            'OPENROUTER_API_KEY'
        ]
        
        for key_name in api_key_names:
            if key_name in os.environ:
                env_keys[key_name] = os.environ[key_name]
                
        return env_keys
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration with API key.
        
        Returns:
            Complete LLM configuration with API key
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.config:
            self.load_configuration()
            
        if not self.api_keys:
            self.load_api_keys()
            
        llm_config = self.config.get('llm', {}).copy()
        provider = llm_config.get('provider')
        
        if not provider:
            raise ConfigurationError("No LLM provider specified in configuration")
            
        # Map provider to API key name
        api_key_mapping = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_AI_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY'
        }
        
        required_key = api_key_mapping.get(provider)
        if not required_key:
            raise ConfigurationError(f"Unknown LLM provider: {provider}")
            
        if required_key not in self.api_keys:
            raise ConfigurationError(
                f"Missing API key '{required_key}' for provider '{provider}'. "
                f"Please add it to your ~/.slide_extract_keys.env file."
            )
            
        llm_config['api_key'] = self.api_keys[required_key]
        
        # Set default values
        llm_config.setdefault('max_tokens', 4000)
        llm_config.setdefault('temperature', 0.3)
        
        return llm_config
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration options."""
        if not self.config:
            self.load_configuration()
            
        processing_config = self.config.get('processing', {})
        
        # Set defaults
        processing_config.setdefault('batch_size', 10)
        processing_config.setdefault('request_timeout', 60)
        processing_config.setdefault('max_retries', 3)
        processing_config.setdefault('parallel_processing', True)
        
        return processing_config
    
    def create_sample_key_file(self) -> Path:
        """
        Create a sample API key file in the user's home directory.
        
        Returns:
            Path to the created sample file
        """
        key_file_path = Path.home() / ".slide_extract_keys.env.sample"
        
        sample_content = """# slide-extract - API Keys Configuration
# 
# Copy this file to ~/.slide_extract_keys.env and add your actual API keys
# Keep this file secure and never commit it to version control!

# OpenAI API Key (for GPT models)
# Get yours at: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (for Claude models)  
# Get yours at: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Google AI API Key (for Gemini models)
# Get yours at: https://makersuite.google.com/app/apikey
GOOGLE_AI_API_KEY=your_google_ai_api_key_here

# OpenRouter API Key (for access to multiple models)
# Get yours at: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
"""
        
        with open(key_file_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
            
        # Make file readable only by user for security
        key_file_path.chmod(0o600)
        
        logger.info("Created sample API key file at %s", key_file_path)
        return key_file_path