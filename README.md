# .NET Unit Test Generator

AI-powered unit test generator for .NET projects using LiteLLM (OpenAI/GitHub Copilot).

## Features

- ✅ **Multi-Model Support** - OpenAI GPT-4/3.5 with automatic fallback
- ✅ **Smart Analysis** - Detects Controllers, Services, and components
- ✅ **Cost Optimization** - Uses cheaper models for simple classes
- ✅ **xUnit Support** - Generates tests with Moq and FluentAssertions
- ✅ **Existing Test Detection** - Skips classes that already have tests
- ✅ **Dry Run Mode** - Preview what will be generated
- ✅ **Pattern Filtering** - Generate tests for specific classes only
- ✅ **Cost Tracking** - Real-time token usage and cost estimation

## Installation

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.template .env
# Edit .env and add your OPENAI_API_KEY
```

## Quick Start

### Basic Usage

```bash
# Generate tests for a .NET project
python generate_tests.py /path/to/your/project

# Specify output directory
python generate_tests.py /path/to/project -o /path/to/project.Tests

# Dry run (analyze only, no generation)
python generate_tests.py /path/to/project --dry-run

# Generate tests for specific classes only
python generate_tests.py /path/to/project -p "Controller|Service"

# Limit number of classes
python generate_tests.py /path/to/project -n 10

# Force overwrite existing tests
python generate_tests.py /path/to/project --force
```

### RemoteC Example

```bash
# Generate tests for RemoteC.Api controllers
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
    -o /mnt/d/dev2/remotec/tests/RemoteC.Api.Tests \
    -p "Controller" \
    -n 5

# Generate tests for RemoteC.Host services
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Host \
    -o /mnt/d/dev2/remotec/tests/RemoteC.Host.Tests \
    -p "Service"
```

## Configuration

Edit `.env` file:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-...

# Optional: Model Selection
PRIMARY_MODEL=gpt-4-turbo-preview    # For complex classes
FALLBACK_MODEL=gpt-3.5-turbo         # Fallback if primary fails
SIMPLE_MODEL=gpt-3.5-turbo           # For simple classes (cost optimization)

# Optional: Generation Settings
MAX_TOKENS=2000
TEMPERATURE=0.2
TEST_FRAMEWORK=xunit

# Optional: Rate Limiting
MAX_REQUESTS_PER_MINUTE=50
RETRY_ATTEMPTS=3
```

## Output

Generated tests include:

- **Complete test class** with proper namespace
- **xUnit test methods** following AAA pattern (Arrange, Act, Assert)
- **Moq mocks** for all dependencies
- **FluentAssertions** for readable assertions
- **XML documentation** explaining what each test validates
- **Happy path tests** for normal operation
- **Edge case tests** for boundary conditions
- **Error tests** for exception handling

### Example Output

```csharp
using Xunit;
using Moq;
using FluentAssertions;
using System.Threading.Tasks;

namespace RemoteC.Api.Controllers.Tests
{
    /// <summary>
    /// Unit tests for SessionsController
    /// </summary>
    public class SessionsControllerTests
    {
        private readonly Mock<ISessionService> _mockSessionService;
        private readonly SessionsController _controller;

        public SessionsControllerTests()
        {
            _mockSessionService = new Mock<ISessionService>();
            _controller = new SessionsController(_mockSessionService.Object);
        }

        /// <summary>
        /// Validates that CreateSession returns 200 OK with session data when successful
        /// </summary>
        [Fact]
        public async Task CreateSession_ValidRequest_ReturnsOkWithSession()
        {
            // Arrange
            var request = new CreateSessionRequest { /* ... */ };
            var expectedSession = new Session { /* ... */ };
            _mockSessionService
                .Setup(x => x.CreateSessionAsync(It.IsAny<CreateSessionRequest>()))
                .ReturnsAsync(expectedSession);

            // Act
            var result = await _controller.CreateSession(request);

            // Assert
            result.Should().BeOfType<OkObjectResult>();
            var okResult = result as OkObjectResult;
            okResult.Value.Should().BeEquivalentTo(expectedSession);
        }

        // ... more tests
    }
}
```

## Cost Estimates

Based on OpenAI pricing (2025):

| Model | Input | Output | Avg Cost per Class |
|-------|-------|--------|-------------------|
| GPT-4 Turbo | $0.01/1K | $0.03/1K | $0.05-0.15 |
| GPT-3.5 Turbo | $0.0005/1K | $0.0015/1K | $0.002-0.008 |

**Example**: Generating tests for 50 classes:
- With GPT-4: ~$2.50-7.50
- With GPT-3.5: ~$0.10-0.40

The tool automatically uses GPT-3.5 for simple classes to minimize cost.

## Command-Line Options

```
Usage: generate_tests.py [OPTIONS] PROJECT_DIR

  Generate unit tests for .NET projects using AI

Arguments:
  PROJECT_DIR  Path to .NET project directory  [required]

Options:
  -o, --output-dir PATH   Output directory for test files
  --dry-run              Analyze only, do not generate tests
  -f, --force            Overwrite existing test files
  -n, --max-classes INT  Maximum number of classes to process
  -p, --pattern TEXT     Only process classes matching pattern (regex)
  --help                 Show this message and exit.
```

## Advanced Features

### Model Fallback

If the primary model fails, automatically falls back to the fallback model:

```
Primary: gpt-4-turbo-preview ❌ Failed
Fallback: gpt-3.5-turbo ✅ Success
```

### Cost Optimization

Automatically uses cheaper models for simple classes:

- **Simple class**: ≤3 methods, ≤2 dependencies → GPT-3.5 Turbo
- **Complex class**: >3 methods or >2 dependencies → GPT-4 Turbo

### Existing Test Detection

Skips classes that already have tests:

```
✅ SessionService.cs → No tests found, generate
⏭️  AuthService.cs → AuthServiceTests.cs exists, skip
```

Use `--force` to regenerate existing tests.

## Troubleshooting

### API Key Not Found

```bash
❌ OPENAI_API_KEY not found in .env file
```

**Solution**: Create `.env` file with your OpenAI API key.

### Rate Limit Exceeded

```
⚠️  gpt-4-turbo-preview failed: Rate limit exceeded
```

**Solution**: The tool automatically retries with exponential backoff. If persistent, reduce `MAX_REQUESTS_PER_MINUTE` in `.env`.

### Model Not Available

```
⚠️  gpt-4-turbo-preview failed: Model not found
```

**Solution**: Update `PRIMARY_MODEL` in `.env` to a model you have access to (e.g., `gpt-4` or `gpt-3.5-turbo`).

## Integration with CI/CD

### GitHub Actions

```yaml
name: Generate Unit Tests

on:
  push:
    paths:
      - 'src/**/*.cs'

jobs:
  generate-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd /path/to/dotnet-unit-test-gen
          pip install -r requirements.txt

      - name: Generate tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python generate_tests.py /path/to/project -o tests/

      - name: Commit tests
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add tests/
          git commit -m "🤖 Auto-generate unit tests"
          git push
```

## Best Practices

1. **Start Small**: Use `--dry-run` first to see what will be generated
2. **Use Patterns**: Generate tests incrementally with `-p "Controller"`, then `-p "Service"`
3. **Review Output**: Always review generated tests before committing
4. **Cost Control**: Set `-n 10` to limit classes when experimenting
5. **Existing Tests**: Use default behavior (skip existing) to avoid overwrites

## Roadmap

- [ ] Support for NUnit and MSTest frameworks
- [ ] Integration test generation
- [ ] Test data builder generation
- [ ] Coverage report integration
- [ ] GitHub Copilot API support (when available)
- [ ] Batch processing with rate limiting
- [ ] Custom prompt templates

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

---

**Created**: 2025-10-22
**Author**: AI-Assisted Development Team
