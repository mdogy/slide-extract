# AI-Powered Presentation Note Generator

A robust, production-quality command-line interface (CLI) script for generating AI-powered speaker notes from PDF presentation slides using user-defined prompts.

## Project Overview

This Python CLI tool processes PDF presentation slides and generates speaker notes or summaries for each slide based on a user-provided prompt. The tool follows modern software engineering best practices with comprehensive logging, rigorous testing, and clean, maintainable code.

## Features

- **AI-Powered Analysis**: Uses advanced LLM models (GPT, Claude, Gemini) for intelligent slide analysis
- **Multiple LLM Support**: Compatible with OpenAI, Anthropic, Google AI, and OpenRouter
- **PDF Processing**: Extract text content from each page of PDF presentation files
- **Prompt Integration**: Load custom generation prompts from Markdown files
- **Flexible Output**: Direct output to stdout or save to specified files
- **Secure API Key Management**: Best-practice API key storage outside the repository
- **Comprehensive Logging**: Detailed logging with configurable verbosity levels
- **Error Handling**: Robust error handling with graceful fallback to placeholder mode
- **Well Tested**: Comprehensive unit test suite with high coverage

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd slide-extract
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows
   venv\\Scripts\\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## LLM Configuration and API Keys

### Step 1: Choose Your LLM Provider

This tool supports multiple LLM providers. Choose one and obtain an API key:

#### OpenAI (GPT Models)
- Visit: https://platform.openai.com/api-keys
- Create an account and generate an API key
- Models available: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`

#### Anthropic (Claude Models)
- Visit: https://console.anthropic.com/
- Create an account and generate an API key
- Models available: `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`

#### Google AI (Gemini Models)
- Visit: https://makersuite.google.com/app/apikey
- Create an account and generate an API key
- Models available: `gemini-1.5-pro`, `gemini-1.5-flash`

#### OpenRouter (Multiple Model Access)
- Visit: https://openrouter.ai/keys
- Provides access to models from multiple providers through a single API
- Models available: Various OpenAI, Anthropic, Google, and other models

### Step 2: Set Up API Keys

**IMPORTANT**: Never commit API keys to your repository. Store them securely in your home directory.

1. **Create the API key file** in your home directory:
   ```bash
   # Create the secure key file
   touch ~/.slide_extract_keys.env
   chmod 600 ~/.slide_extract_keys.env  # Make it readable only by you
   ```

2. **Add your API keys** to `~/.slide_extract_keys.env`:
   ```bash
   # Add your API keys (only include the ones you plan to use)
   echo "OPENAI_API_KEY=your_openai_api_key_here" >> ~/.slide_extract_keys.env
   echo "ANTHROPIC_API_KEY=your_anthropic_api_key_here" >> ~/.slide_extract_keys.env
   echo "GOOGLE_AI_API_KEY=your_google_ai_api_key_here" >> ~/.slide_extract_keys.env
   echo "OPENROUTER_API_KEY=your_openrouter_api_key_here" >> ~/.slide_extract_keys.env
   ```

   Or edit the file directly:
   ```bash
   nano ~/.slide_extract_keys.env
   ```

   Example content:
   ```
   # Only include the keys you actually have
   OPENAI_API_KEY=sk-proj-abcdef123456789...
   ANTHROPIC_API_KEY=sk-ant-api03-abcdef123...
   GOOGLE_AI_API_KEY=AIzaSyAbCdEf123456789...
   OPENROUTER_API_KEY=sk-or-v1-abcdef123...
   ```

### Step 3: Configure Your LLM Model

Edit the `config.yaml` file in the project directory to specify which model to use:

```yaml
# Example: Using OpenAI GPT-4o
llm:
  provider: "openai"
  model: "gpt-4o"
  max_tokens: 4000
  temperature: 0.3
```

Or uncomment one of the pre-configured options in `config.yaml`:

```yaml
# For Anthropic Claude
# llm:
#   provider: "anthropic"
#   model: "claude-3-5-sonnet-20241022"
#   max_tokens: 4000
#   temperature: 0.3

# For Google Gemini
# llm:
#   provider: "google"
#   model: "gemini-1.5-pro"
#   max_tokens: 4000
#   temperature: 0.3

# For OpenRouter
# llm:
#   provider: "openrouter"
#   model: "anthropic/claude-3-5-sonnet"
#   max_tokens: 4000
#   temperature: 0.3
#   base_url: "https://openrouter.ai/api/v1"
```

## Usage

### Command Line Interface

The script provides a comprehensive CLI with the following options:

```bash
python src/main.py [OPTIONS]
```

### Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--input` | `-i` | Yes | Path(s) to input PDF slide deck files |
| `--prompt` | `-p` | Yes | Path to Markdown file containing the generation prompt |
| `--output` | `-o` | No | Path to output Markdown file (default: stdout) |
| `--config` | `-c` | No | Path to configuration file (default: config.yaml) |
| `--verbose` | `-v` | No | Enable verbose logging (DEBUG level) |
| `--no-ai` | | No | Use placeholder mode without AI (for testing) |
| `--version` | | No | Show version information |

### Usage Examples

1. **Basic AI-powered analysis with default configuration:**
   ```bash
   python src/main.py -i presentation.pdf -p src/default_prompt.md
   ```

2. **Process multiple PDFs with file output:**
   ```bash
   python src/main.py -i slide1.pdf slide2.pdf slide3.pdf -p src/default_prompt.md -o notes.md
   ```

3. **Use custom configuration file:**
   ```bash
   python src/main.py -i presentation.pdf -p src/default_prompt.md -c my_config.yaml -o notes.md
   ```

4. **Enable verbose logging:**
   ```bash
   python src/main.py -i presentation.pdf -p src/default_prompt.md -v -o detailed_notes.md
   ```

5. **Test mode without AI (placeholder mode):**
   ```bash
   python src/main.py -i presentation.pdf -p src/default_prompt.md --no-ai -o test_notes.md
   ```

6. **Using long-form arguments:**
   ```bash
   python src/main.py --input presentation.pdf --prompt src/default_prompt.md --output notes.md --verbose
   ```

### Using the Default Prompt

The tool includes a comprehensive default prompt at `src/default_prompt.md` that instructs the AI to generate:

- **Slide Text**: Exact transcription of slide content
- **Images/Diagrams**: Detailed descriptions of visual elements
- **Topics**: Key concepts covered
- **Narration**: Comprehensive speaker notes in an educational tone

### Custom Prompt Files

You can also create custom prompts. Here's a simplified example:

```markdown
# Custom Analysis Prompt

Analyze each slide and provide:
1. A summary of the main points
2. Suggested talking points for an instructor
3. Key terms that should be defined
4. Questions students might ask

Use a conversational, engaging tone appropriate for university-level instruction.
```

### Example Output

With AI enabled, the tool generates comprehensive, structured analysis for each slide:

```markdown
# Notes for presentation.pdf

#### Slide: Introduction to Machine Learning

**Slide Number:** 1

**Slide Text:**
Introduction to Machine Learning
- What is ML?
- Types of learning algorithms  
- Applications in industry

**Slide Images/Diagrams:**
The slide contains a simple title layout with three bullet points. The background uses a clean, professional design with the course branding.

**Slide Topics:**
*   Machine Learning Definition
*   Algorithm Classification
*   Industrial Applications
*   Course Introduction

**Slide Narration:**
"Welcome everyone to our introduction to machine learning. Today we're going to start with the fundamentals - answering that basic question: what exactly is machine learning? We'll explore the different types of learning algorithms available to us, from supervised to unsupervised learning, and we'll look at real-world applications across various industries. This foundational knowledge will set us up perfectly for diving deeper into specific algorithms and techniques in the coming lectures."

---
PROMPT: Please generate comprehensive speaker notes for the following slide content...

SLIDE CONTENT: Supervised Learning
- Training with labeled data
- Classification vs Regression
- Common algorithms

--- END NOTES ---
```

## Development

### Project Structure

```
slide-extract/
├── src/
│   ├── __init__.py
│   ├── main.py              # Main CLI script and argument parsing
│   ├── pdf_processor.py     # PDF text extraction functionality
│   └── note_generator.py    # Note generation logic (placeholder implementation)
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   ├── test_pdf_processor.py
│   └── test_note_generator.py
├── .gitignore
├── README.md
└── requirements.txt
```

### Code Quality Tools

The project uses several tools to maintain code quality:

- **black**: Code formatting
- **pylint**: Code linting and static analysis
- **pytest**: Testing framework
- **pytest-cov**: Test coverage measurement

### Running Tests

1. **Run all tests:**
   ```bash
   pytest
   ```

2. **Run tests with coverage report:**
   ```bash
   pytest --cov=src --cov-report=html --cov-report=term
   ```

3. **Run specific test file:**
   ```bash
   pytest tests/test_pdf_processor.py -v
   ```

4. **Generate detailed coverage report:**
   ```bash
   pytest --cov=src --cov-report=html
   # Open htmlcov/index.html in your browser
   ```

### Code Formatting and Linting

1. **Format code with black:**
   ```bash
   black src/ tests/
   ```

2. **Run pylint checks:**
   ```bash
   pylint src/
   ```

3. **Run both formatting and linting:**
   ```bash
   black src/ tests/ && pylint src/
   ```

## Testing Instructions

The project includes a comprehensive test suite with the following coverage:

### Test Categories

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **Error Handling Tests**: Test error conditions and edge cases
- **Mock Tests**: Test external dependency interactions

### Coverage Goals

- **Target Coverage**: 90%+ line coverage
- **Critical Paths**: 100% coverage for main business logic
- **Error Handling**: Complete coverage of exception paths

### Running Coverage Analysis

1. **Install coverage dependencies** (included in requirements.txt):
   ```bash
   pip install pytest-cov
   ```

2. **Generate coverage report**:
   ```bash
   pytest --cov=src --cov-report=term-missing --cov-report=html
   ```

3. **View detailed HTML report**:
   ```bash
   # Open htmlcov/index.html in your web browser
   open htmlcov/index.html  # macOS
   start htmlcov/index.html  # Windows
   xdg-open htmlcov/index.html  # Linux
   ```

## Logging

The application uses Python's built-in logging module with the following configuration:

### Log Levels
- **INFO**: General operational messages (default)
- **DEBUG**: Detailed diagnostic information (enabled with `-v` flag)

### Log Outputs
- **File**: All logs written to `script_run.log` in the current directory
- **Console**: INFO and DEBUG messages to stderr (separate from main program output)

### Log Format
```
2024-01-15 10:30:45,123 - src.pdf_processor - INFO - Processing PDF: presentation.pdf
2024-01-15 10:30:45,456 - src.note_generator - DEBUG - Generating notes for slide 1
```

## Error Handling

The application provides comprehensive error handling for common scenarios:

- **File Not Found**: Clear messages for missing PDF or prompt files
- **Permission Errors**: Informative messages for file access issues
- **Invalid PDF Files**: Specific errors for corrupted or invalid PDFs
- **Empty Content**: Validation for empty prompt files or PDFs
- **Processing Errors**: Detailed error information for PDF processing failures

## Dependencies

### Core Dependencies
- **PyMuPDF (fitz)**: PDF text extraction
- **argparse**: Command-line argument parsing (built-in)
- **logging**: Application logging (built-in)
- **pathlib**: File path handling (built-in)

### Development Dependencies
- **pytest**: Testing framework
- **pytest-mock**: Mocking utilities for tests
- **pytest-cov**: Test coverage measurement
- **black**: Code formatting
- **pylint**: Code linting and analysis

## Contributing

1. Follow the existing code style and conventions
2. Add tests for any new functionality  
3. Ensure all tests pass and maintain coverage above 90%
4. Format code with black before submitting
5. Run pylint to check for any issues
6. Test with multiple LLM providers when adding LLM-related features
7. Update configuration examples and documentation for new features

## Advanced Configuration

### Processing Options

You can customize processing behavior in `config.yaml`:

```yaml
processing:
  batch_size: 10              # Slides per batch
  request_timeout: 60         # Request timeout (seconds)
  max_retries: 3              # Retry attempts
  parallel_processing: true   # Enable parallel processing

logging:
  level: "INFO"              # Log level
  log_llm_details: false     # Include request/response details
```

### Cost Management

- **OpenAI**: Costs vary by model (~$0.01-0.06 per 1K tokens)
- **Anthropic**: Similar pricing structure to OpenAI
- **Google AI**: Generally lower cost, with generous free tiers
- **OpenRouter**: Varies by model, often competitive pricing

To manage costs:
- Start with smaller, cheaper models for testing
- Use `max_tokens` to limit response length
- Monitor usage through provider dashboards
- Consider using Google AI or OpenRouter for cost optimization

## License

This project is provided as-is for educational and development purposes.

## Troubleshooting

### Common Issues

1. **"No API key found" error**:
   - Ensure your API key file exists: `~/.slide_extract_keys.env`
   - Verify the key format matches your provider
   - Check file permissions: `chmod 600 ~/.slide_extract_keys.env`

2. **"LLM connection test failed"**:
   - Verify your API key is valid and has sufficient credits/quota
   - Check your internet connection
   - Try a different model in `config.yaml`
   - The tool will automatically fall back to placeholder mode

3. **"Configuration file not found"**:
   - Ensure `config.yaml` exists in your project directory
   - Or specify a custom config file with `--config path/to/config.yaml`

4. **Rate limiting issues**:
   - Reduce the batch size in `config.yaml`
   - Increase request timeout
   - Some providers have strict rate limits for new accounts

### Testing Without API Keys

You can test the tool without setting up API keys:

```bash
python src/main.py -i presentation.pdf -p src/default_prompt.md --no-ai -o test_output.md
```

This runs in placeholder mode and generates formatted output without AI analysis.

## Security Best Practices

- **Never commit API keys** to version control
- Store API keys in your home directory with restricted permissions (`chmod 600`)
- Use environment-specific API keys (separate keys for development/production)
- Regularly rotate your API keys
- Monitor API usage and costs through provider dashboards
- Consider using API key rotation and secrets management tools in production