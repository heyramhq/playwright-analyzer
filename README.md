# Playwright Test Report Analyzer 🤖

An AI-powered tool that analyzes Playwright test reports to provide intelligent insights, failure analysis, and actionable recommendations. The tool uses PydanticAI with OpenAI-compatible models to understand test failures and inject the analysis directly into your Playwright HTML reports.

## Features ✨

- **Automatic Test Report Parsing**: Extracts test results from Playwright HTML reports
- **AI-Powered Analysis**: Uses reasoning models to analyze failures and identify patterns
- **Failure Root Cause Analysis**: Identifies why tests failed with categorization
- **Pattern Recognition**: Detects common failure patterns across multiple tests
- **Flaky Test Detection**: Identifies tests with intermittent failures
- **Performance Insights**: Highlights slow tests and performance issues
- **HTML Report Enhancement**: Injects AI insights directly into the Playwright report
- **Flexible Model Support**: Works with OpenAI, Ollama, or any OpenAI-compatible API

## Prerequisites 🔧

- Python 3.9 or higher
- [UV](https://github.com/astral-sh/uv) package manager

### Installing UV

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using Homebrew on macOS
brew install uv
```

## Installation 📦

```bash
# Navigate to the analyzer directory
cd playwright-analyzer

# Install dependencies using UV
uv sync

# For development dependencies
uv sync --dev
```

## Configuration ⚙️

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```env
# For OpenAI
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4o-mini

# For local models (e.g., Ollama)
OPENAI_API_BASE=http://localhost:11434/v1
MODEL_NAME=llama3.2
```

## Usage 🚀

### Basic Usage

After running your Playwright tests:

```bash
# Run Playwright tests first
pnpm test:e2e

# Analyze the report
cd playwright-analyzer
uv sync

# Use the CLI command
uv run playwright-analyzer --help
```

### Command Line Options

```bash
uv run playwright-analyzer --help

Options:
  --report PATH      Path to Playwright HTML report (default: ../playwright-report/index.html)
  --context PATH     Path to context file (default: ../CONTEXT-TEST.md)
  --model NAME       Model name (default: from .env or gpt-4o-mini)
  --api-key KEY      API key (default: from .env)
  --api-base URL     API base URL (default: from .env or OpenAI)
  --no-inject        Don't inject insights into HTML report
```

### Examples

```bash
# Use GPT-4 for more detailed analysis
uv run playwright-analyzer --model gpt-4o

# Use local Ollama model
uv run playwright-analyzer --model llama3.2 --api-base http://localhost:11434/v1

# Analyze without modifying the HTML report
uv run playwright-analyzer --no-inject

# Custom report path
uv run playwright-analyzer --report /path/to/playwright-report/index.html
```

## Integration with CI/CD 🔄

Add to your GitHub Actions workflow:

```yaml
- name: Run Playwright Tests
  run: pnpm test:e2e
  continue-on-error: true

- name: Install UV
  if: always()
  uses: astral-sh/setup-uv@v2
  with:
    enable-cache: true
    cache-dependency-glob: "playwright-analyzer/pyproject.toml"

- name: Analyze Test Report
  if: always()
  run: |
    cd playwright-analyzer
    uv sync
    uv run playwright-analyzer
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

- name: Upload Enhanced Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report-with-insights
    path: playwright-report/
```

## Output 📊

The analyzer provides:

### 1. Console Output
- Test summary statistics
- Detailed failure analysis
- Recommendations and patterns
- Risk areas and performance issues

### 2. Enhanced HTML Report
The original Playwright report is enhanced with:
- AI insights section with visual metrics
- Failure analysis with root causes
- Recommendations panel
- Common patterns detection
- Flaky test identification

### 3. JSON Export
Insights are also saved to `playwright-report/ai-insights.json` for programmatic access.

## Architecture 🏗️

```
playwright-analyzer/
├── src/
│   └── playwright_analyzer/
│       ├── __init__.py          # Package initialization
│       ├── analyze_report.py    # Main CLI entry point
│       ├── report_parser.py     # Parses Playwright HTML reports
│       ├── agent.py            # PydanticAI agent for analysis
│       └── report_injector.py  # Injects insights into HTML
├── pyproject.toml              # UV/Python project configuration
├── .python-version             # Python version for UV
├── .env.example                # Environment template
└── README.md                   # This file
```

## How It Works 🔍

1. **Report Parsing**: Extracts test data from Playwright's embedded JSON
2. **Context Loading**: Loads application context (optional)
3. **AI Analysis**: Sends failure data to AI model for analysis
4. **Insight Generation**: Creates structured insights with PydanticAI
5. **HTML Injection**: Adds insights to the original report
6. **Export**: Saves insights as JSON for further processing

## Models Supported 🤖

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- **Anthropic**: Claude (via OpenAI-compatible API)
- **Ollama**: Llama, Mistral, CodeLlama (local)
- **Any OpenAI-compatible API**

## Features in Detail 📝

### Failure Analysis
- Categorizes failures (UI, Network, Timing, Logic)
- Identifies root causes
- Provides specific fix suggestions
- Assesses impact level

### Pattern Detection
- Groups similar failures
- Identifies systemic issues
- Detects configuration problems
- Highlights regression patterns

### Performance Insights
- Identifies slow tests
- Detects timeout issues
- Suggests optimization opportunities
- Monitors test duration trends

### Flaky Test Detection
- Identifies tests with retries
- Detects intermittent failures
- Suggests stabilization strategies
- Tracks flakiness patterns

## Development 🧪

### Running Tests

```bash
# Run tests with UV
uv run pytest

# Run with coverage
uv run pytest --cov

# Format code
uv run black .

# Lint code
uv run ruff check .
```

### Installing Development Dependencies

```bash
# Install all dependencies including dev
uv sync --dev
```

## Troubleshooting 🛠️

### "Report file not found"
- Ensure Playwright tests have been run: `pnpm test:e2e`
- Check the report path: `ls ../playwright-report/index.html`

### "API key is required"
- Set `OPENAI_API_KEY` in `.env` file
- Or use `--api-key` argument
- Or use a local model with `--api-base`

### "Could not extract test data"
- Ensure you're using a recent version of Playwright
- Check that the HTML report contains embedded JSON data

### "Module not found" errors
- Ensure UV is installed: `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Run `uv sync` to install dependencies
- Use `uv run` prefix for all Python commands

## Contributing 🤝

Contributions are welcome! Areas for improvement:
- Support for more test frameworks
- Additional analysis patterns
- Performance optimizations
- More model integrations

## License 📄

MIT