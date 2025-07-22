# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI-powered CLI tool that extracts text from PDF presentation slides and generates comprehensive speaker notes using various LLM providers (OpenAI, Anthropic, Google AI, OpenRouter). The tool is designed with production-quality error handling, comprehensive logging, and fallback mechanisms.

## Installation and Setup

### Install as CLI Tool
```bash
# Install in development mode
pip install -e .

# Or install from source
pip install .

# After installation, use the 'slide-extract' command
slide-extract --help
```

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=slide_extract --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_pdf_processor.py -v

# Generate detailed coverage report (opens in browser)
pytest --cov=slide_extract --cov-report=html
```

### Code Quality
```bash
# Format code
black src/slide_extract/ tests/

# Run linting
pylint src/slide_extract/

# Run both formatting and linting
black src/slide_extract/ tests/ && pylint src/slide_extract/
```

### Running the Application
```bash
# Basic usage (outputs to stdout)
slide-extract -i presentation.pdf -p src/slide_extract/prompts/default_prompt.md

# With file output
slide-extract -i presentation.pdf -p src/slide_extract/prompts/default_prompt.md -o output.md

# Verbose logging
slide-extract -i presentation.pdf -p src/slide_extract/prompts/default_prompt.md -v

# Test mode without AI
slide-extract -i presentation.pdf -p src/slide_extract/prompts/default_prompt.md --no-ai

# Multiple PDFs
slide-extract -i slide1.pdf slide2.pdf -p src/slide_extract/prompts/default_prompt.md -o notes.md

# Development mode (run from source)
python -m slide_extract.scripts.main -i presentation.pdf -p src/slide_extract/prompts/default_prompt.md
```

## Architecture

### Core Components

**Main Application (`src/slide_extract/scripts/main.py`)**
- CLI argument parsing and application entry point
- Coordinates all other components
- Comprehensive error handling with graceful degradation
- Dual logging (file + console)

**PDF Processing (`src/slide_extract/core/pdf_processor.py`)**
- Uses PyMuPDF (fitz) to extract text from PDF pages
- Text cleaning and normalization
- Batch processing of multiple PDFs
- Error handling for corrupted/invalid PDFs

**LLM Integration (`src/slide_extract/core/llm_client.py`)**
- Unified interface for multiple LLM providers
- Provider-specific implementations for OpenAI, Anthropic, Google AI, OpenRouter
- Connection testing and error handling
- Configurable parameters (temperature, max_tokens)

**Note Generation (`src/slide_extract/core/note_generator.py`)**
- Orchestrates slide analysis using LLM client
- Fallback to placeholder mode when AI fails
- Structured output formatting
- File I/O for prompts and generated notes
- Progress indicators and streaming output for better debugging

**Configuration Management (`src/slide_extract/core/config_manager.py`)**
- YAML configuration loading
- Secure API key management from `~/.slide_extract_keys.env`
- Multiple key file locations support
- Environment variable fallback

### Key Architectural Patterns

**Error-First Design**: Application exits with clear error messages when AI is expected but not configured. Use --no-ai flag for placeholder mode.

**Installable CLI**: Installs as 'slide-extract' command via setup.py entry points.

**Modular Structure**: Uses proper src/slide_extract layout with organized subdirectories:
- `src/slide_extract/core/`: Core functionality (PDF processing, LLM integration, etc.)
- `src/slide_extract/scripts/`: Main CLI script
- `src/slide_extract/prompts/`: Default prompt templates

**Security**: API keys stored outside repository in home directory with restricted permissions. Configuration validates all required fields.

**Error Handling**: Each module has custom exception types (`PDFProcessingError`, `LLMError`, `NoteGenerationError`, `ConfigurationError`) with detailed error messages.

**Logging**: Structured logging with both file (`script_run.log`) and console output, configurable verbosity levels. Added progress indicators for LLM processing to aid debugging.

## Configuration

The application uses `config.yaml` for LLM configuration and `~/.slide_extract_keys.env` for API keys.

### API Key Setup
API keys are stored securely in the user's home directory:
- Primary location: `~/.slide_extract_keys.env`
- Fallback locations: `~/.config/slide_extract/keys.env`, `.env`
- Environment variables as final fallback

### LLM Provider Configuration
Edit `config.yaml` to switch between providers:
- OpenAI: GPT models
- Anthropic: Claude models  
- Google: Gemini models
- OpenRouter: Multiple model access

## Development Notes

### Dependencies
- **PyMuPDF**: PDF text extraction
- **PyYAML**: Configuration management
- **Provider SDKs**: openai, anthropic, google-generativeai, httpx
- **Testing**: pytest, pytest-mock, pytest-cov
- **Code Quality**: black, pylint

### Testing Strategy
- Unit tests for all core functionality
- Mock external dependencies (LLM APIs)
- Error condition testing
- Integration tests for component interaction
- Target 90%+ coverage for critical paths

### File Import Pattern
Uses try/except imports to support both module (`python -m slide_extract.main`) and direct execution (`python slide_extract/main.py`). Primary usage is via installed CLI command `slide-extract`.

### Error Recovery
- PDF processing errors stop execution (critical failure)
- LLM connection failures trigger automatic fallback to placeholder mode
- Individual slide analysis failures don't stop batch processing

### Security Considerations
- API keys never stored in repository
- Key files have restricted permissions (600)
- No sensitive data in logs unless explicitly enabled
- Configuration validation prevents malformed requests
- Exits with error code 1 when AI expected but not configured (prevents silent fallback to placeholders)