# VB.NET Unit Test Generator

## Overview

The dotnet-unit-test-gen tool now supports **Visual Basic .NET** projects in addition to C# projects. This enhancement enables automatic generation of xUnit tests for VB.NET codebases with proper syntax handling.

## Key Features

### VB.NET-Specific Support

✅ **Automatic Language Detection**: Detects .vb files and generates VB.NET test syntax
✅ **Proper VB.NET Syntax**: Generates tests with correct VB.NET keywords and patterns
✅ **Attribute Parentheses Fix**: Auto-corrects `<Fact>` to `<Fact()>` (critical VB.NET requirement)
✅ **VB.NET Patterns**: Understands `Sub`, `Function`, `End Sub`, `Nothing`, `AndAlso`, `OrElse`
✅ **Mixed Projects**: Can process projects with both C# and VB.NET files

### Auto-Fixes for VB.NET

The generator automatically detects and fixes common VB.NET test errors:

1. **Missing Parentheses on Attributes**: `<Fact>` → `<Fact()>`
2. **Missing Imports Statements**: Adds `Imports Moq`, `Imports FluentAssertions`
3. **C# Syntax Leakage**: Warns about `null`, `&&`, `||` in VB.NET code

## Installation

Same as the original tool:

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` file with your API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Generate Tests for VB.NET Project

```bash
# Generate tests for ALL VB.NET controllers
python generate_tests_vbnet.py /path/to/PaymentAPI/Controllers \
  -o /path/to/PaymentAPI.Tests.Unit/Controllers \
  --language vbnet

# Generate tests for specific VB.NET controllers (pattern match)
python generate_tests_vbnet.py /path/to/PaymentAPI/Controllers \
  -o /path/to/PaymentAPI.Tests.Unit/Controllers \
  --language vbnet \
  --pattern ".*Controller$"

# Process both C# and VB.NET files
python generate_tests_vbnet.py /path/to/project \
  -o /path/to/tests \
  --language both
```

### PaymentAPI Example

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen
source venv/bin/activate

# Generate tests for PaymentController.vb
python generate_tests_vbnet.py \
  /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI \
  -o /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI.Tests.Unit \
  --language vbnet \
  --pattern "^PaymentController$" \
  --force
```

### Dry Run (Preview)

```bash
# See what would be generated without creating files
python generate_tests_vbnet.py /path/to/project \
  --dry-run \
  --language vbnet
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `PROJECT_DIR` | Path to source code directory (required) |
| `-o, --output-dir` | Output directory for test files |
| `--dry-run` | Analyze only, don't generate files |
| `-f, --force` | Overwrite existing test files |
| `-n, --max-classes` | Maximum number of classes to process |
| `-p, --pattern` | Regex pattern to match class names |
| `-l, --language` | Language filter: `csharp`, `vbnet`, or `both` |

## VB.NET Test Syntax Examples

### Generated Test Structure

```vbnet
Imports Xunit
Imports Moq
Imports FluentAssertions
Imports System.Threading.Tasks
Imports PaymentDataModel
Imports PaymentManager

Namespace PaymentAPI.Controllers.Tests
    Public Class PaymentControllerTests
        ''' <summary>
        ''' Tests that GetWalletTokenList returns tokens for valid person
        ''' </summary>
        <Fact()>
        Public Sub GetWalletTokenList_ValidPersonId_ReturnsTokens()
            ' Arrange
            Dim mockManager = New Mock(Of PaymentManager.PaymentManager)()
            Dim request = New ByLocationAndPersonRequest() With {
                .personId = 12345,
                .locationId = 1
            }
            Dim expectedResponse = New WalletTokenResponse() With {
                .Successful = True
            }
            mockManager.Setup(Function(m) m.GetWalletTokenList(request)).Returns(expectedResponse)

            Dim controller = New PaymentController()
            ' Note: VB.NET controllers often get manager from helper

            ' Act
            Dim result = controller.GetWalletTokenList(request)

            ' Assert
            result.Should().NotBeNothing()
            result.StatusCode.Should().Be(HttpStatusCode.OK)
        End Sub

        ''' <summary>
        ''' Tests that GetWalletTokenList handles Nothing request
        ''' </summary>
        <Fact()>
        Public Sub GetWalletTokenList_NothingRequest_ReturnsBadRequest()
            ' Arrange
            Dim controller = New PaymentController()

            ' Act
            Dim result = controller.GetWalletTokenList(Nothing)

            ' Assert
            result.Should().NotBeNothing()
            result.StatusCode.Should().Be(HttpStatusCode.BadRequest)
        End Sub
    End Class
End Namespace
```

### Key VB.NET Syntax Differences

| Concept | C# | VB.NET |
|---------|----|----|
| **Attribute** | `[Fact]` | `<Fact()>` (parentheses required) |
| **Null** | `null` | `Nothing` |
| **Method (void)** | `void Method()` | `Sub Method()` |
| **Method (return)** | `int Method()` | `Function Method() As Integer` |
| **Variable** | `var x = 5;` | `Dim x = 5` or `Dim x As Integer = 5` |
| **End Statement** | `}` | `End Sub`, `End Function`, `End Class` |
| **Logical AND** | `&&` | `AndAlso` |
| **Logical OR** | `\|\|` | `OrElse` |
| **Property** | `public string Name { get; set; }` | `Public Property Name As String` |

## Output

### Console Output

```
🤖 .NET Unit Test Generator (C# + VB.NET)

📁 Scanning /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI...
✓ Found 158 source files

✓ Found 19 classes needing tests
  • C# classes: 0
  • VB.NET classes: 19

📝 Generating tests to /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI.Tests.Unit...

✓ Generated PaymentControllerTests.vb (vbnet)
  ✓ Auto-fixed: Fixed attribute: <Fact> → <Fact()>, Added missing Imports: Moq
✓ Generated SecurityControllerTests.vb (vbnet)
✓ Generated AdminControllerTests.vb (vbnet)

====================================================================
📊 Generation Summary

Classes Analyzed       19
C# Files              0
VB.NET Files          19
Tests Generated       19
Tests Skipped         0
Tokens Used           48,234
Estimated Cost        $1.87

✓ Auto-Fixes Applied:
  • Fixed attribute: 19 file(s)
  • Added missing Imports: 12 file(s)

⚠️  Warnings (Review These):
  • ⚠️  Found 'null': 3 file(s)
```

### Generated Files

- `PaymentControllerTests.vb` - Tests for PaymentController.vb
- `SecurityControllerTests.vb` - Tests for SecurityController.vb
- `EcommerceControllerTests.vb` - Tests for EcommerceController.vb
- ... (one test file per controller)

## Pattern Learning (Future Enhancement)

The pattern learner can be updated to support VB.NET compilation errors:

```bash
# After generating tests, learn from VB.NET compilation errors
python langchain_pattern_learner_vbnet.py \
  /path/to/source \
  /path/to/tests
```

This will automatically:
1. Compile VB.NET tests
2. Analyze BC#### (VB.NET compiler errors)
3. Learn patterns like property names, type mappings
4. Cache patterns for next run

## Cost

Same as C# generation:
- **Initial Generation**: ~$1.50-$2.00 for 20 controllers
- **Pattern Learning**: ~$0.50 per run
- **Break-even**: After 3-5 projects

## Troubleshooting

### Common Issues

**Issue**: Tests have C# syntax mixed with VB.NET
**Fix**: Regenerate with `--force` flag, check AI model output

**Issue**: Attribute errors like `BC30205: End of statement expected`
**Fix**: Auto-fix should handle this, but verify all attributes have `()`

**Issue**: "Nothing is not defined" errors
**Fix**: Check for leaked `null` keywords (warnings will flag this)

**Issue**: Mocking doesn't work in VB.NET tests
**Fix**: Ensure `Imports Moq` is present, use `New Mock(Of IInterface)()`

### Debug Mode

```bash
# Enable verbose LiteLLM logging
export LITELLM_LOG=DEBUG
python generate_tests_vbnet.py /path/to/project --dry-run
```

## Comparison: C# vs VB.NET Generation

| Feature | C# | VB.NET |
|---------|----|----|
| File Extension | `.cs` | `.vb` |
| Attribute Syntax | `[Fact]` | `<Fact()>` |
| Comment Style | `//` | `'` |
| Null Value | `null` | `Nothing` |
| Lambda Syntax | `x => x.Id` | `Function(x) x.Id` |
| String Concat | `+` | `+` or `&` |
| Case Sensitivity | Sensitive | Insensitive by default |

## Integration with PaymentAPI Project

### Step 1: Generate Tests

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen
source venv/bin/activate

python generate_tests_vbnet.py \
  /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI/Controllers \
  -o /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI.Tests.Unit/Controllers \
  --language vbnet \
  --force
```

### Step 2: Add to Project

```bash
cd /mnt/d/Dev2/michaeljr/PaymentAPI-original

# Add all generated test files to test project
# (Manual step - update .vbproj file)
```

### Step 3: Compile and Run

```bash
cd PaymentAPI.Tests.Unit
dotnet build
dotnet test
```

### Step 4: Learn Patterns (if errors occur)

```bash
python /mnt/d/dev2/dotnet-unit-test-gen/langchain_pattern_learner_vbnet.py \
  /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI \
  /mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI.Tests.Unit
```

## Next Steps

1. ✅ Generate tests for PaymentController (most complex)
2. ✅ Generate tests for SecurityController
3. ✅ Generate tests for remaining 17 controllers
4. ⏳ Compile and fix any remaining errors
5. ⏳ Implement VB.NET pattern learner
6. ⏳ Iterate until >60% test coverage

## Contributing

To extend VB.NET support:

1. **Add new auto-fixes**: Edit `auto_fix_vbnet_errors()` in `generate_tests_vbnet.py`
2. **Improve parsing**: Update `_parse_vbnet_class()` for better method detection
3. **Add patterns**: Contribute VB.NET-specific patterns to pattern learner

## License

Same as main dotnet-unit-test-gen project (MIT License)

---

**Created**: 2025-10-25
**Author**: Claude Code (AI Assistant)
**For Project**: PaymentAPI Code Review - Test Coverage Enhancement
