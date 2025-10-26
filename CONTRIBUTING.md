# Contributing to Universal AI Test Generator

Thank you for your interest in contributing! This project welcomes contributions from the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, AI provider)
- Relevant logs or error messages

### Suggesting Features

Feature suggestions are welcome! Please create an issue describing:
- The problem your feature solves
- Your proposed solution
- Any alternative solutions you've considered
- Example use cases

### Code Contributions

1. **Fork the repository** and create a new branch from `master`
2. **Make your changes** following the project's code style
3. **Add tests** if applicable
4. **Update documentation** for new features
5. **Submit a pull request** with a clear description of changes

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/dotnet-unit-test-gen.git
cd dotnet-unit-test-gen

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env
# Add your API keys to .env
```

### Coding Guidelines

- **Python Style**: Follow PEP 8
- **Type Hints**: Use type hints for function signatures
- **Documentation**: Add docstrings for classes and methods
- **Comments**: Comment complex logic
- **Modular**: Keep providers, languages, and orchestration separate

### Adding a New Language Handler

1. Create a new file in `languages/` (e.g., `golang_language.py`)
2. Inherit from `BaseLanguageHandler`
3. Implement required methods:
   - `get_file_extensions()`
   - `detect_files()`
   - `parse_class()`
   - `generate_test_prompt()`
   - `auto_fix_syntax()`
4. Add to `generate_tests_v2.py` language choices
5. Update README.md with new language support

### Adding a New AI Provider

1. Create a new file in `providers/` (e.g., `ollama_provider.py`)
2. Inherit from `BaseAIProvider`
3. Implement required methods:
   - `generate_test()`
   - `get_cost_estimate()`
   - `get_name()`
4. Add to `provider_factory.py`
5. Update documentation with pricing and setup

### Running Tests

```bash
# Run test suite
python -m pytest tests/

# Run specific test
python -m pytest tests/test_csharp_language.py

# Run with coverage
python -m pytest --cov=. tests/
```

### Pull Request Process

1. Ensure your PR has a clear title and description
2. Reference any related issues (#123)
3. Make sure all tests pass
4. Update README.md if adding features
5. Maintain backward compatibility when possible
6. One feature/fix per PR (unless closely related)

### Code Review

- Maintainers will review your PR within a few days
- Address feedback constructively
- Be patient - quality takes time
- Once approved, maintainers will merge

## Community

- Be respectful and constructive
- Help others when you can
- Share your use cases and success stories
- Report bugs and suggest improvements

## Questions?

Create an issue with the `question` label or reach out to the maintainers.

---

**Thank you for contributing!** Every contribution, no matter how small, helps make this project better.
