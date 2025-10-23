# Quick Start Guide

## 1. Setup (One-time)

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen

# Run setup script
./setup.sh

# Configure API key
cp .env.template .env
# Edit .env and add your OPENAI_API_KEY
```

## 2. Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Generate tests for RemoteC.Api
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api
```

## 3. Common Commands

### Dry Run (Preview Only)
```bash
python generate_tests.py /path/to/project --dry-run
```

### Generate for Controllers Only
```bash
python generate_tests.py /path/to/project -p "Controller" -n 5
```

### Specify Output Directory
```bash
python generate_tests.py /path/to/project -o /path/to/tests
```

### Force Regenerate
```bash
python generate_tests.py /path/to/project --force
```

## 4. Real RemoteC Examples

### Generate tests for API controllers
```bash
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
    -o /mnt/d/dev2/remotec/tests/RemoteC.Api.Tests \
    -p "Controller" \
    -n 10
```

### Generate tests for Host services
```bash
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Host \
    -o /mnt/d/dev2/remotec/tests/RemoteC.Host.Tests \
    -p "Service"
```

### Generate tests for specific class
```bash
python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
    -p "SessionsController"
```

## 5. Output

Generated tests will include:

- ✅ xUnit test class with proper namespace
- ✅ Moq mocks for all dependencies
- ✅ FluentAssertions for readable assertions
- ✅ AAA pattern (Arrange, Act, Assert)
- ✅ Happy path + edge case + error tests
- ✅ XML documentation comments

## 6. Cost Estimates

| Scenario | Classes | Estimated Cost |
|----------|---------|----------------|
| 5 Controllers | 5 | $0.25-0.75 |
| 10 Services | 10 | $0.50-1.50 |
| 50 Mixed | 50 | $2.50-7.50 |

*Costs based on GPT-4 Turbo pricing. Actual costs may be lower due to automatic GPT-3.5 usage for simple classes.*

## 7. Troubleshooting

### "OPENAI_API_KEY not found"
```bash
cp .env.template .env
# Edit .env and add your API key
```

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Permission denied"
```bash
chmod +x setup.sh generate_tests.py example_usage.sh
```

## 8. Next Steps

- Review generated tests before committing
- Run tests to ensure they compile
- Adjust mocks/assertions as needed
- Add custom test cases for domain-specific logic

For full documentation, see [README.md](README.md).
