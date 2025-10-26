#!/usr/bin/env python3
"""
.NET Unit Test Generator using LiteLLM - VB.NET Support
Supports both C# and VB.NET projects with automatic language detection
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv
import litellm
from litellm import completion

# Initialize
console = Console()
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4-turbo-preview")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")
SIMPLE_MODEL = os.getenv("SIMPLE_MODEL", "gpt-3.5-turbo")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TEST_FRAMEWORK = os.getenv("TEST_FRAMEWORK", "xunit")


@dataclass
class ClassInfo:
    """Information about a .NET class to test"""
    name: str
    namespace: str
    file_path: Path
    source_code: str
    methods: List[str]
    dependencies: List[str]
    is_controller: bool
    is_service: bool
    language: str  # 'csharp' or 'vbnet'


@dataclass
class ProjectPattern:
    """A learned pattern for a specific project"""
    pattern_type: str  # 'return_type', 'enum_value', 'property_name', etc.
    context: str  # 'IDeviceRepository.GetUserDevicesAsync', 'ConnectionType', etc.
    value: str  # 'DataPagedResult<DeviceDto>', 'P2P,Relay,Direct', etc.
    confidence: float = 1.0  # How confident we are (based on frequency)
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())


class ProjectPatternCache:
    """Caches learned patterns for a specific project"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # Create cache directory in tool location
        cache_root = Path(__file__).parent / ".test-gen-cache"
        cache_root.mkdir(exist_ok=True)

        # Hash project path for unique cache key
        project_hash = hashlib.md5(str(project_dir.absolute()).encode()).hexdigest()[:12]
        self.cache_dir = cache_root / project_hash
        self.cache_dir.mkdir(exist_ok=True)

        # Store project info
        self.info_file = self.cache_dir / "project-info.json"
        self.patterns_file = self.cache_dir / "patterns.json"

        self._save_project_info()
        self.patterns: List[ProjectPattern] = self._load_patterns()

    def _save_project_info(self):
        """Save project metadata"""
        info = {
            "project_path": str(self.project_dir.absolute()),
            "project_name": self.project_dir.name,
            "last_updated": datetime.now().isoformat()
        }
        self.info_file.write_text(json.dumps(info, indent=2))

    def _load_patterns(self) -> List[ProjectPattern]:
        """Load cached patterns"""
        if not self.patterns_file.exists():
            return []

        try:
            data = json.loads(self.patterns_file.read_text())
            return [ProjectPattern(**p) for p in data]
        except:
            return []

    def save_patterns(self):
        """Save patterns to cache"""
        data = [
            {
                "pattern_type": p.pattern_type,
                "context": p.context,
                "value": p.value,
                "confidence": p.confidence,
                "last_seen": p.last_seen
            }
            for p in self.patterns
        ]
        self.patterns_file.write_text(json.dumps(data, indent=2))

    def add_pattern(self, pattern_type: str, context: str, value: str):
        """Add or update a pattern"""
        # Check if pattern exists
        for p in self.patterns:
            if p.pattern_type == pattern_type and p.context == context:
                p.value = value
                p.last_seen = datetime.now().isoformat()
                p.confidence = min(1.0, p.confidence + 0.1)  # Increase confidence
                self.save_patterns()
                return

        # Add new pattern
        self.patterns.append(ProjectPattern(pattern_type, context, value))
        self.save_patterns()

    def get_context_string(self) -> str:
        """Get patterns as a string for AI prompt"""
        if not self.patterns:
            return ""

        lines = ["\n**Project-Specific Patterns (Learned from Previous Runs):**"]
        lines.append("```")

        # Group by type
        by_type = {}
        for p in self.patterns:
            by_type.setdefault(p.pattern_type, []).append(p)

        for pattern_type, patterns in by_type.items():
            lines.append(f"\n// {pattern_type.replace('_', ' ').title()}:")
            for p in patterns:
                lines.append(f"// {p.context} → {p.value}")

        lines.append("```\n")
        return "\n".join(lines)


@dataclass
class TestStats:
    """Statistics for test generation"""
    classes_analyzed: int = 0
    tests_generated: int = 0
    tests_skipped: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    errors: List[str] = None
    auto_fixes: Dict[str, int] = None
    warnings: Dict[str, int] = None
    csharp_files: int = 0
    vbnet_files: int = 0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.auto_fixes is None:
            self.auto_fixes = {}
        if self.warnings is None:
            self.warnings = {}


class DotNetAnalyzer:
    """Analyzes .NET projects to find classes that need tests"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.source_files: List[Path] = []
        self.test_files: List[Path] = []

    def find_source_files(self) -> List[Path]:
        """Find all C# and VB.NET source files in the project"""
        source_files = []

        # Find C# files
        for file in self.project_dir.rglob("*.cs"):
            if any(x in str(file) for x in ["/bin/", "/obj/", "Test.cs", "Tests.cs", "/Migrations/"]):
                if "Test" in str(file):
                    self.test_files.append(file)
                continue
            source_files.append(file)

        # Find VB.NET files
        for file in self.project_dir.rglob("*.vb"):
            if any(x in str(file) for x in ["/bin/", "/obj/", "Test.vb", "Tests.vb", "/Migrations/"]):
                if "Test" in str(file):
                    self.test_files.append(file)
                continue
            source_files.append(file)

        self.source_files = source_files
        return source_files

    def detect_language(self, file_path: Path) -> str:
        """Detect if file is C# or VB.NET"""
        if file_path.suffix.lower() == '.cs':
            return 'csharp'
        elif file_path.suffix.lower() == '.vb':
            return 'vbnet'
        return 'unknown'

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """Parse a .NET file to extract class information"""
        language = self.detect_language(file_path)

        if language == 'csharp':
            return self._parse_csharp_class(file_path)
        elif language == 'vbnet':
            return self._parse_vbnet_class(file_path)

        return None

    def _parse_csharp_class(self, file_path: Path) -> Optional[ClassInfo]:
        """Parse a C# file"""
        try:
            source = file_path.read_text(encoding='utf-8')

            namespace_match = re.search(r'namespace\s+([\w\.]+)', source)
            namespace = namespace_match.group(1) if namespace_match else "Unknown"

            class_match = re.search(r'public\s+(?:partial\s+)?class\s+(\w+)', source)
            if not class_match:
                return None

            class_name = class_match.group(1)

            method_pattern = r'public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:Task<?[\w<>]*>?|[\w<>]+)\s+(\w+)\s*\('
            methods = re.findall(method_pattern, source)

            dependency_pattern = r'private\s+readonly\s+I(\w+)\s+_'
            dependencies = re.findall(dependency_pattern, source)

            is_controller = 'Controller' in class_name or ': ControllerBase' in source or ': Controller' in source
            is_service = 'Service' in class_name or 'Manager' in class_name or 'Repository' in class_name

            return ClassInfo(
                name=class_name,
                namespace=namespace,
                file_path=file_path,
                source_code=source,
                methods=methods,
                dependencies=dependencies,
                is_controller=is_controller,
                is_service=is_service,
                language='csharp'
            )
        except Exception as e:
            console.print(f"[yellow]⚠️  Error parsing {file_path}: {e}[/yellow]")
            return None

    def _parse_vbnet_class(self, file_path: Path) -> Optional[ClassInfo]:
        """Parse a VB.NET file"""
        try:
            source = file_path.read_text(encoding='utf-8')

            # Extract namespace
            namespace_match = re.search(r'Namespace\s+([\w\.]+)', source, re.IGNORECASE)
            namespace = namespace_match.group(1) if namespace_match else "Unknown"

            # Extract class name (Public Class)
            class_match = re.search(r'Public\s+(?:Partial\s+)?Class\s+(\w+)', source, re.IGNORECASE)
            if not class_match:
                return None

            class_name = class_match.group(1)

            # Extract public functions and subs
            # Pattern for: Public [Async] Function/Sub Name(...) As Type
            method_pattern = r'Public\s+(?:Async\s+)?(?:Function|Sub)\s+(\w+)\s*\('
            methods = re.findall(method_pattern, source, re.IGNORECASE)

            # Extract dependencies (injected via constructor or fields)
            # VB.NET pattern: Private ReadOnly _dependency As IDependency
            dependency_pattern = r'Private\s+ReadOnly\s+_\w+\s+As\s+I(\w+)'
            dependencies = re.findall(dependency_pattern, source, re.IGNORECASE)

            # Determine type
            is_controller = 'Controller' in class_name or 'Inherits ApiController' in source or 'Inherits ControllerBase' in source
            is_service = 'Service' in class_name or 'Manager' in class_name or 'Repository' in class_name

            return ClassInfo(
                name=class_name,
                namespace=namespace,
                file_path=file_path,
                source_code=source,
                methods=methods,
                dependencies=dependencies,
                is_controller=is_controller,
                is_service=is_service,
                language='vbnet'
            )
        except Exception as e:
            console.print(f"[yellow]⚠️  Error parsing {file_path}: {e}[/yellow]")
            return None

    def find_existing_tests(self, class_name: str, language: str) -> Optional[Path]:
        """Check if tests already exist for a class"""
        if language == 'csharp':
            test_patterns = [
                f"{class_name}Tests.cs",
                f"{class_name}Test.cs",
                f"Test{class_name}.cs"
            ]
        else:  # vbnet
            test_patterns = [
                f"{class_name}Tests.vb",
                f"{class_name}Test.vb",
                f"Test{class_name}.vb"
            ]

        for test_file in self.test_files:
            if any(pattern in test_file.name for pattern in test_patterns):
                return test_file
        return None


class TestGenerator:
    """Generates unit tests using LiteLLM"""

    def __init__(self, stats: TestStats, project_dir: Path = None, pattern_cache: ProjectPatternCache = None):
        self.stats = stats
        self.project_dir = project_dir
        self.pattern_cache = pattern_cache
        self.dto_cache = {}
        litellm.set_verbose = False
        if OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    def generate_test_prompt(self, class_info: ClassInfo, framework: str = "xunit") -> str:
        """Generate the prompt for test generation"""

        # Truncate source if too large
        max_source_len = 8000
        source = class_info.source_code
        if len(source) > max_source_len:
            source = source[:max_source_len] + "\n' ... (truncated)"

        # Get project-specific patterns (if available)
        pattern_context = self.pattern_cache.get_context_string() if self.pattern_cache else ""

        if class_info.language == 'vbnet':
            return self._generate_vbnet_test_prompt(class_info, source, pattern_context, framework)
        else:
            return self._generate_csharp_test_prompt(class_info, source, pattern_context, framework)

    def _generate_vbnet_test_prompt(self, class_info: ClassInfo, source: str, pattern_context: str, framework: str) -> str:
        """Generate prompt for VB.NET test generation"""

        # Detect if this is a data access class
        is_data_access = 'DataAccess' in class_info.name or 'DataBroker' in str(class_info.dependencies)

        prompt = f"""You are an expert .NET test engineer. Generate comprehensive unit tests for the following VB.NET class.

**CRITICAL VB.NET SYNTAX RULES:**
1. ALL attributes MUST have parentheses: <Fact()> NOT <Fact>
2. Use Sub for void methods, Function for return values
3. Use End Sub, End Function, End Class, End Namespace
4. Variables: Dim variable As Type
5. String comparison is case-insensitive by default
6. Use Nothing instead of null
7. Use AndAlso/OrElse for short-circuit logic (not &&/||)
8. Property syntax: Public Property Name As String

**Class to Test:**
```vbnet
{source}
```
{pattern_context}
**Requirements:**
1. Use {framework.upper()} testing framework
2. Use Moq for mocking dependencies: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}
3. Use FluentAssertions for assertions
4. Follow AAA pattern (Arrange, Act, Assert)
5. Test happy paths, edge cases, and error conditions
6. Include at least 3-5 tests per public method
7. Use descriptive test method names (e.g., MethodName_Condition_ExpectedResult)
8. Mock all dependencies properly - ESPECIALLY database calls
9. Add XML documentation comments explaining what each test validates

**Class Type:** {'Controller' if class_info.is_controller else 'Service' if class_info.is_service else 'DataAccess' if is_data_access else 'Component'}

{'**SPECIAL REQUIREMENTS FOR DATA ACCESS CLASSES:**' if is_data_access else ''}
{'- Mock DataBroker.RequestData() method to return test data' if is_data_access else ''}
{'- Mock stored procedure responses with proper Response objects' if is_data_access else ''}
{'- Set up mock data instead of requiring real database connections' if is_data_access else ''}
{'- Test that requests are built with correct parameters' if is_data_access else ''}
{'- Test that responses are properly mapped from mock data' if is_data_access else ''}
{'- Example: Dim mockBroker As New Mock(Of IDataBroker)()' if is_data_access else ''}
{'  mockBroker.Setup(Function(b) b.RequestData(It.IsAny(Of DataAccessRequest)())).Returns(mockResponse)' if is_data_access else ''}

**Output Format:**
- Complete VB.NET test class with all necessary Imports statements
- Proper namespace matching the source (with .Tests suffix)
- Test fixtures for setup/teardown if needed
- Well-organized test methods
- **REMEMBER**: All xUnit attributes MUST have parentheses: <Fact()> <Theory()> <InlineData()>

**Example VB.NET Test Structure:**
```vbnet
Imports Xunit
Imports Moq
Imports FluentAssertions
Imports System.Threading.Tasks

Namespace MyNamespace.Tests
    Public Class MyControllerTests
        <Fact()>
        Public Sub MethodName_Condition_ExpectedResult()
            ' Arrange
            Dim mockDependency = New Mock(Of IDependency)()
            Dim controller = New MyController(mockDependency.Object)

            ' Act
            Dim result = controller.MethodName()

            ' Assert
            result.Should().NotBeNothing()
        End Sub
    End Class
End Namespace
```

Generate ONLY the complete VB.NET test class code, no explanations."""

        return prompt

    def _generate_csharp_test_prompt(self, class_info: ClassInfo, source: str, pattern_context: str, framework: str) -> str:
        """Generate prompt for C# test generation (original implementation)"""

        prompt = f"""You are an expert .NET test engineer. Generate comprehensive unit tests for the following C# class.

**Class to Test:**
```csharp
{source}
```
{pattern_context}
**Requirements:**
1. Use {framework.upper()} testing framework
2. Use Moq for mocking dependencies: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}
3. Use FluentAssertions for assertions
4. Follow AAA pattern (Arrange, Act, Assert)
5. Test happy paths, edge cases, and error conditions
6. Include at least 3-5 tests per public method
7. Use descriptive test method names (e.g., MethodName_Condition_ExpectedResult)
8. Mock all dependencies properly
9. Add XML documentation comments explaining what each test validates

**Class Type:** {'Controller' if class_info.is_controller else 'Service' if class_info.is_service else 'Component'}

**Output Format:**
- Complete test class with all necessary using statements
- Proper namespace matching the source (with .Tests suffix)
- Test fixtures for setup/teardown if needed
- Well-organized test methods

Generate ONLY the complete test class code, no explanations."""

        return prompt

    def call_llm(self, prompt: str, use_simple_model: bool = False) -> Tuple[str, int, float]:
        """Call LiteLLM with fallback logic"""
        model = SIMPLE_MODEL if use_simple_model else PRIMARY_MODEL

        try:
            response = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens

            cost = self.calculate_cost(model, tokens)

            return content, tokens, cost

        except Exception as e:
            console.print(f"[yellow]⚠️  {model} failed: {e}. Trying fallback...[/yellow]")

            try:
                response = completion(
                    model=FALLBACK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                )

                content = response.choices[0].message.content
                tokens = response.usage.total_tokens
                cost = self.calculate_cost(FALLBACK_MODEL, tokens)

                return content, tokens, cost

            except Exception as fallback_error:
                raise Exception(f"All models failed. Primary: {e}, Fallback: {fallback_error}")

    def calculate_cost(self, model: str, tokens: int) -> float:
        """Calculate approximate cost based on model and tokens"""
        pricing = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},  # $0.15/$0.60 per 1M tokens
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }

        avg_price = 0.0
        for model_key, prices in pricing.items():
            if model_key in model:
                avg_price = (prices["input"] + prices["output"]) / 2
                break

        # Default to gpt-4o-mini pricing if model not found
        if avg_price == 0.0:
            avg_price = (pricing["gpt-4o-mini"]["input"] + pricing["gpt-4o-mini"]["output"]) / 2

        return (tokens / 1000) * avg_price

    def extract_code_block(self, response: str, language: str) -> str:
        """Extract code from markdown code blocks"""
        if language == 'vbnet':
            patterns = [r'```(?:vbnet|vb|visualbasic)?\n(.*?)\n```']
        else:
            patterns = [r'```(?:csharp|cs|c#)?\n(.*?)\n```']

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                return matches[0].strip()

        return response.strip()

    def auto_fix_vbnet_errors(self, code: str, class_info: ClassInfo) -> tuple[str, list[str], list[str]]:
        """Detect and auto-fix common VB.NET test errors"""
        fixes_applied = []
        warnings = []

        # 1. Fix missing parentheses on attributes
        attribute_fixes = [
            (r'<Fact>', '<Fact()>'),
            (r'<Theory>', '<Theory()>'),
            (r'<InlineData\(([^)]+)\)>', r'<InlineData(\1)>'),  # Already has parens, no change
            (r'<TestMethod>', '<TestMethod()>'),
            (r'<TestClass>', '<TestClass()>'),
        ]

        for old_pattern, new_pattern in attribute_fixes:
            if re.search(old_pattern, code):
                code = re.sub(old_pattern, new_pattern, code)
                fixes_applied.append(f"Fixed attribute: {old_pattern} → {new_pattern}")

        # 2. Check for missing Imports statements
        missing_imports = []

        if 'Moq' in code and 'Imports Moq' not in code:
            missing_imports.append('Imports Moq')
            fixes_applied.append("Added missing Imports: Moq")

        if 'FluentAssertions' in code and 'Imports FluentAssertions' not in code:
            missing_imports.append('Imports FluentAssertions')
            fixes_applied.append("Added missing Imports: FluentAssertions")

        if 'Task' in code and 'Imports System.Threading.Tasks' not in code:
            missing_imports.append('Imports System.Threading.Tasks')
            fixes_applied.append("Added missing Imports: System.Threading.Tasks")

        # Insert missing imports after first Imports statement
        if missing_imports:
            first_import_match = re.search(r'^Imports ', code, re.MULTILINE)
            if first_import_match:
                insert_pos = first_import_match.start()
                code = code[:insert_pos] + '\n'.join(missing_imports) + '\n' + code[insert_pos:]

        # 3. Warnings for common VB.NET issues
        if 'null' in code:
            warnings.append("⚠️  Found 'null' - should be 'Nothing' in VB.NET")

        if '&&' in code or '||' in code:
            warnings.append("⚠️  Found C# operators (&&/||) - use AndAlso/OrElse in VB.NET")

        if re.search(r'<\w+>', code):  # Attribute without parentheses
            warnings.append("⚠️  Potential attribute without parentheses - verify all attributes have ()")

        return code, fixes_applied, warnings

    def auto_fix_common_errors(self, code: str, class_info: ClassInfo) -> tuple[str, list[str], list[str]]:
        """Detect and auto-fix common errors in generated tests"""
        if class_info.language == 'vbnet':
            return self.auto_fix_vbnet_errors(code, class_info)

        # C# auto-fixes (original implementation)
        fixes_applied = []
        warnings = []

        missing_usings = []

        if 'IWebHostEnvironment' in code and 'using Microsoft.AspNetCore.Hosting;' not in code:
            missing_usings.append('using Microsoft.AspNetCore.Hosting;')
            fixes_applied.append("Added missing using: Microsoft.AspNetCore.Hosting")

        if 'IHubContext' in code and 'using Microsoft.AspNetCore.SignalR;' not in code:
            missing_usings.append('using Microsoft.AspNetCore.SignalR;')
            fixes_applied.append("Added missing using: Microsoft.AspNetCore.SignalR")

        if missing_usings:
            first_using_match = re.search(r'^using ', code, re.MULTILINE)
            if first_using_match:
                insert_pos = first_using_match.start()
                code = code[:insert_pos] + '\n'.join(missing_usings) + '\n' + code[insert_pos:]

        return code, fixes_applied, warnings

    def generate_tests_for_class(self, class_info: ClassInfo) -> Optional[str]:
        """Generate tests for a single class"""
        try:
            use_simple_model = len(class_info.methods) <= 3 and len(class_info.dependencies) <= 2

            prompt = self.generate_test_prompt(class_info, TEST_FRAMEWORK)
            response, tokens, cost = self.call_llm(prompt, use_simple_model)

            self.stats.tokens_used += tokens
            self.stats.cost_usd += cost

            test_code = self.extract_code_block(response, class_info.language)

            test_code, fixes, warnings = self.auto_fix_common_errors(test_code, class_info)

            for fix in fixes:
                fix_key = fix.split(':')[0] if ':' in fix else fix
                self.stats.auto_fixes[fix_key] = self.stats.auto_fixes.get(fix_key, 0) + 1

            for warning in warnings:
                warning_key = warning.split('-')[0].strip() if '-' in warning else warning
                self.stats.warnings[warning_key] = self.stats.warnings.get(warning_key, 0) + 1

            if fixes:
                console.print(f"[green]  ✓ Auto-fixed: {', '.join(fixes)}[/green]")

            if warnings:
                console.print(f"[yellow]  ⚠️  Warnings: {len(warnings)} issue(s) detected[/yellow]")

            return test_code

        except Exception as e:
            self.stats.errors.append(f"{class_info.name}: {str(e)}")
            console.print(f"[red]❌ Error generating tests for {class_info.name}: {e}[/red]")
            return None


@click.command()
@click.argument('project_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), help='Output directory for test files')
@click.option('--dry-run', is_flag=True, help='Analyze only, do not generate tests')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing test files')
@click.option('--max-classes', '-n', type=int, help='Maximum number of classes to process')
@click.option('--pattern', '-p', help='Only process classes matching pattern (regex)')
@click.option('--language', '-l', type=click.Choice(['csharp', 'vbnet', 'both']), default='both', help='Language to process')
def main(project_dir: Path, output_dir: Optional[Path], dry_run: bool, force: bool, max_classes: Optional[int], pattern: Optional[str], language: str):
    """
    Generate unit tests for .NET projects using AI (C# and VB.NET support)

    Example:
        python generate_tests_vbnet.py /path/to/project -o /path/to/tests --language vbnet
    """

    console.print(Panel.fit("🤖 .NET Unit Test Generator (C# + VB.NET)", style="bold blue"))

    if not OPENAI_API_KEY:
        console.print("[red]❌ OPENAI_API_KEY not found in .env file[/red]")
        sys.exit(1)

    analyzer = DotNetAnalyzer(project_dir)
    stats = TestStats()
    pattern_cache = ProjectPatternCache(project_dir)
    generator = TestGenerator(stats, project_dir, pattern_cache)

    if pattern_cache.patterns:
        console.print(f"[cyan]📚 Loaded {len(pattern_cache.patterns)} cached pattern(s) from previous runs[/cyan]")

    console.print(f"\n[cyan]📁 Scanning {project_dir}...[/cyan]")
    source_files = analyzer.find_source_files()
    console.print(f"[green]✓ Found {len(source_files)} source files[/green]")

    classes_to_test: List[ClassInfo] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing classes...", total=len(source_files))

        for source_file in source_files:
            class_info = analyzer.parse_class(source_file)
            if class_info and class_info.methods:
                # Track language stats
                if class_info.language == 'csharp':
                    stats.csharp_files += 1
                elif class_info.language == 'vbnet':
                    stats.vbnet_files += 1

                # Filter by language
                if language != 'both' and class_info.language != language:
                    progress.advance(task)
                    continue

                # Apply pattern filter
                if pattern and not re.search(pattern, class_info.name):
                    progress.advance(task)
                    continue

                existing_tests = analyzer.find_existing_tests(class_info.name, class_info.language)
                if existing_tests and not force:
                    console.print(f"[yellow]⏭️  Skipping {class_info.name} (tests exist at {existing_tests.name})[/yellow]")
                    stats.tests_skipped += 1
                else:
                    classes_to_test.append(class_info)

                stats.classes_analyzed += 1
            progress.advance(task)

    if max_classes and len(classes_to_test) > max_classes:
        classes_to_test = classes_to_test[:max_classes]
        console.print(f"[yellow]⚠️  Limited to {max_classes} classes[/yellow]")

    console.print(f"\n[green]✓ Found {len(classes_to_test)} classes needing tests[/green]")
    console.print(f"[cyan]  • C# classes: {stats.csharp_files}[/cyan]")
    console.print(f"[cyan]  • VB.NET classes: {stats.vbnet_files}[/cyan]")

    if dry_run:
        table = Table(title="Classes to Test")
        table.add_column("Class", style="cyan")
        table.add_column("Language", style="blue")
        table.add_column("Type", style="magenta")
        table.add_column("Methods", style="green")
        table.add_column("Dependencies", style="yellow")

        for class_info in classes_to_test:
            class_type = "Controller" if class_info.is_controller else "Service" if class_info.is_service else "Component"
            table.add_row(
                class_info.name,
                class_info.language.upper(),
                class_type,
                str(len(class_info.methods)),
                str(len(class_info.dependencies))
            )

        console.print(table)
        return

    if not output_dir:
        output_dir = project_dir.parent / f"{project_dir.name}.Tests"

    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[cyan]📝 Generating tests to {output_dir}...[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Generating tests...", total=len(classes_to_test))

        for class_info in classes_to_test:
            test_code = generator.generate_tests_for_class(class_info)

            if test_code:
                extension = '.vb' if class_info.language == 'vbnet' else '.cs'
                test_file_path = output_dir / f"{class_info.name}Tests{extension}"
                test_file_path.write_text(test_code, encoding='utf-8')

                console.print(f"[green]✓ Generated {test_file_path.name} ({class_info.language})[/green]")
                stats.tests_generated += 1
            else:
                console.print(f"[red]✗ Failed to generate tests for {class_info.name}[/red]")

            progress.advance(task)

    console.print("\n" + "="*60)
    console.print(Panel.fit("📊 Generation Summary", style="bold green"))

    summary_table = Table(show_header=False)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Classes Analyzed", str(stats.classes_analyzed))
    summary_table.add_row("C# Files", str(stats.csharp_files))
    summary_table.add_row("VB.NET Files", str(stats.vbnet_files))
    summary_table.add_row("Tests Generated", str(stats.tests_generated))
    summary_table.add_row("Tests Skipped", str(stats.tests_skipped))
    summary_table.add_row("Tokens Used", f"{stats.tokens_used:,}")
    summary_table.add_row("Estimated Cost", f"${stats.cost_usd:.4f}")

    if stats.errors:
        summary_table.add_row("Errors", str(len(stats.errors)), style="red")

    console.print(summary_table)

    if stats.auto_fixes:
        console.print("\n[green]✓ Auto-Fixes Applied:[/green]")
        for fix_type, count in sorted(stats.auto_fixes.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  • {fix_type}: {count} file(s)")

    if stats.warnings:
        console.print("\n[yellow]⚠️  Warnings (Review These):[/yellow]")
        for warning_type, count in sorted(stats.warnings.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  • {warning_type}: {count} file(s)")

    if stats.errors:
        console.print("\n[red]Errors:[/red]")
        for error in stats.errors[:10]:
            console.print(f"  • {error}")

    console.print(f"\n[green]✓ Tests written to: {output_dir}[/green]")


if __name__ == "__main__":
    main()
