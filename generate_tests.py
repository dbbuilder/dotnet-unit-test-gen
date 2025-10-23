#!/usr/bin/env python3
"""
.NET Unit Test Generator using LiteLLM
Supports OpenAI API and GitHub Copilot with automatic fallback
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
    """Information about a C# class to test"""
    name: str
    namespace: str
    file_path: Path
    source_code: str
    methods: List[str]
    dependencies: List[str]
    is_controller: bool
    is_service: bool


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
    auto_fixes: Dict[str, int] = None  # Track which fixes were applied and how many times
    warnings: Dict[str, int] = None    # Track warnings found

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
        self.cs_files: List[Path] = []
        self.test_files: List[Path] = []

    def find_cs_files(self) -> List[Path]:
        """Find all C# source files in the project"""
        cs_files = []
        for pattern in ["**/*.cs"]:
            for file in self.project_dir.rglob(pattern):
                # Skip test files, bin, obj, migrations
                if any(x in str(file) for x in ["/bin/", "/obj/", "Test.cs", "Tests.cs", "/Migrations/"]):
                    if "Test" in str(file):
                        self.test_files.append(file)
                    continue
                cs_files.append(file)
        self.cs_files = cs_files
        return cs_files

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """Parse a C# file to extract class information"""
        try:
            source = file_path.read_text(encoding='utf-8')

            # Extract namespace
            namespace_match = re.search(r'namespace\s+([\w\.]+)', source)
            namespace = namespace_match.group(1) if namespace_match else "Unknown"

            # Extract class name (public classes only)
            class_match = re.search(r'public\s+(?:partial\s+)?class\s+(\w+)', source)
            if not class_match:
                return None

            class_name = class_match.group(1)

            # Extract public methods
            method_pattern = r'public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:Task<?[\w<>]*>?|[\w<>]+)\s+(\w+)\s*\('
            methods = re.findall(method_pattern, source)

            # Extract dependencies (constructor injection)
            dependency_pattern = r'private\s+readonly\s+I(\w+)\s+_'
            dependencies = re.findall(dependency_pattern, source)

            # Determine type
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
                is_service=is_service
            )
        except Exception as e:
            console.print(f"[yellow]⚠️  Error parsing {file_path}: {e}[/yellow]")
            return None

    def find_existing_tests(self, class_name: str) -> Optional[Path]:
        """Check if tests already exist for a class"""
        test_patterns = [
            f"{class_name}Tests.cs",
            f"{class_name}Test.cs",
            f"Test{class_name}.cs"
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
        self.dto_cache = {}  # Cache discovered DTOs
        # Configure LiteLLM
        litellm.set_verbose = False
        if OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    def find_related_dtos(self, class_info: ClassInfo) -> str:
        """Find DTOs referenced in the class and return their definitions"""
        if not self.project_dir:
            return ""

        # Extract DTO type names from source code
        dto_pattern = r'\b(\w+Dto)\b'
        dto_names = set(re.findall(dto_pattern, class_info.source_code))

        if not dto_names:
            return ""

        dto_definitions = []

        # Search for DTO files in common locations
        search_paths = [
            self.project_dir.parent / "RemoteC.Shared" / "Models",
            self.project_dir / "Models",
            self.project_dir / "DTOs",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for cs_file in search_path.rglob("*.cs"):
                if cs_file.name in self.dto_cache:
                    content = self.dto_cache[cs_file.name]
                else:
                    try:
                        content = cs_file.read_text(encoding='utf-8', errors='ignore')
                        self.dto_cache[cs_file.name] = content
                    except:
                        continue

                # Extract matching DTO class definitions
                for dto_name in dto_names:
                    pattern = rf'public\s+class\s+{dto_name}\s*{{[^}}]*(?:{{[^}}]*}}[^}}]*)*}}'
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        # Limit size to avoid token explosion
                        dto_def = matches[0]
                        if len(dto_def) < 1000:
                            dto_definitions.append(f"// {dto_name} definition\n{dto_def}")

        if dto_definitions:
            return "\n\n**Related DTOs:**\n```csharp\n" + "\n\n".join(dto_definitions[:5]) + "\n```\n"

        return ""

    def find_related_enums(self, class_info: ClassInfo) -> str:
        """Find enums referenced in the class and return their definitions"""
        if not self.project_dir:
            return ""

        # Extract enum type names from source code
        # Common patterns: SomethingType, SomethingStatus, SomethingMode, etc.
        enum_pattern = r'\b(\w+(?:Type|Status|Mode|State|Level|Kind))\b'
        enum_names = set(re.findall(enum_pattern, class_info.source_code))

        if not enum_names:
            return ""

        enum_definitions = []

        # Search for enum files in common locations
        search_paths = [
            self.project_dir.parent / "RemoteC.Shared" / "Models",
            self.project_dir.parent / "RemoteC.Shared" / "Enums",
            self.project_dir / "Models",
            self.project_dir / "Enums",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for cs_file in search_path.rglob("*.cs"):
                if cs_file.name in self.dto_cache:  # Reuse cache
                    content = self.dto_cache[cs_file.name]
                else:
                    try:
                        content = cs_file.read_text(encoding='utf-8', errors='ignore')
                        self.dto_cache[cs_file.name] = content
                    except:
                        continue

                # Extract matching enum definitions
                for enum_name in enum_names:
                    # Match: public enum EnumName { Value1, Value2, ... }
                    pattern = rf'public\s+enum\s+{enum_name}\s*{{[^}}]*}}'
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        enum_def = matches[0]
                        # Clean up whitespace for readability
                        enum_def = re.sub(r'\s+', ' ', enum_def)
                        enum_def = re.sub(r'\s*{\s*', ' { ', enum_def)
                        enum_def = re.sub(r'\s*}\s*', ' }', enum_def)
                        if len(enum_def) < 500:  # Limit size
                            enum_definitions.append(f"// {enum_name} definition\n{enum_def}")

        if enum_definitions:
            return "\n\n**Related Enums:**\n```csharp\n" + "\n\n".join(enum_definitions[:5]) + "\n```\n"

        return ""

    def generate_test_prompt(self, class_info: ClassInfo, framework: str = "xunit") -> str:
        """Generate the prompt for test generation"""

        # Truncate source if too large
        max_source_len = 8000
        source = class_info.source_code
        if len(source) > max_source_len:
            source = source[:max_source_len] + "\n// ... (truncated)"

        # Find related DTOs and Enums
        dto_context = self.find_related_dtos(class_info)
        enum_context = self.find_related_enums(class_info)

        # Get project-specific patterns (if available)
        pattern_context = self.pattern_cache.get_context_string() if self.pattern_cache else ""

        prompt = f"""You are an expert .NET test engineer. Generate comprehensive unit tests for the following C# class.

**Class to Test:**
```csharp
{source}
```
{dto_context}{enum_context}{pattern_context}
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

            # Calculate cost (approximate)
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
        # Pricing as of 2025 (approximate, adjust as needed)
        pricing = {
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},  # per 1K tokens
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }

        # Assume 50/50 split input/output
        avg_price = 0.0
        for model_key, prices in pricing.items():
            if model_key in model:
                avg_price = (prices["input"] + prices["output"]) / 2
                break

        return (tokens / 1000) * avg_price

    def extract_code_block(self, response: str) -> str:
        """Extract C# code from markdown code blocks"""
        # Try to find ```csharp blocks
        pattern = r'```(?:csharp|cs|c#)?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # If no code blocks, return as-is
        return response.strip()

    def auto_fix_common_errors(self, code: str, class_info: ClassInfo) -> tuple[str, list[str], list[str]]:
        """Detect and auto-fix common errors in generated tests

        Returns: (fixed_code, fixes_applied, warnings)
        """
        fixes_applied = []

        # 1. Check for missing using statements
        missing_usings = []

        # Check if IWebHostEnvironment is used but not imported
        if 'IWebHostEnvironment' in code and 'using Microsoft.AspNetCore.Hosting;' not in code:
            missing_usings.append('using Microsoft.AspNetCore.Hosting;')
            fixes_applied.append("Added missing using: Microsoft.AspNetCore.Hosting")

        # Check if IHubContext is used but not imported
        if 'IHubContext' in code and 'using Microsoft.AspNetCore.SignalR;' not in code:
            missing_usings.append('using Microsoft.AspNetCore.SignalR;')
            fixes_applied.append("Added missing using: Microsoft.AspNetCore.SignalR")

        # Check if IConfiguration is used but not imported
        if 'IConfiguration' in code and 'using Microsoft.Extensions.Configuration;' not in code:
            missing_usings.append('using Microsoft.Extensions.Configuration;')
            fixes_applied.append("Added missing using: Microsoft.Extensions.Configuration")

        # Check if IServiceProvider is used but not imported
        if 'IServiceProvider' in code and 'using System;' not in code:
            missing_usings.append('using System;')
            fixes_applied.append("Added missing using: System (for IServiceProvider)")

        # Insert missing usings after the first using statement
        if missing_usings:
            # Find the first using statement
            first_using_match = re.search(r'^using ', code, re.MULTILINE)
            if first_using_match:
                insert_pos = first_using_match.start()
                code = code[:insert_pos] + '\n'.join(missing_usings) + '\n' + code[insert_pos:]

        # 2. Detect common type mismatches and warn
        warnings = []

        # Check for PagedResult vs DataPagedResult
        if 'PagedResult<' in code and class_info.is_controller:
            warnings.append("⚠️  PagedResult might need to be DataPagedResult (check repository return types)")

        # Check for potential enum issues
        enum_pattern = r'(\w+Type|\w+Status)\.(\w+)'
        enum_matches = re.findall(enum_pattern, code)
        if enum_matches:
            for enum_type, enum_value in enum_matches:
                warnings.append(f"⚠️  Verify enum value: {enum_type}.{enum_value}")

        # Check for Dictionary return types in mocks
        if 'Dictionary<' in code and '.ReturnsAsync' in code:
            warnings.append("⚠️  Dictionary return type in mock - verify against actual method signature")

        # Add warnings as comments at the top if any
        if warnings:
            warning_block = "// AUTO-GENERATED TEST - REVIEW WARNINGS:\n"
            for warning in warnings:
                warning_block += f"// {warning}\n"
            warning_block += "//\n"

            # Insert after namespace declaration
            namespace_match = re.search(r'(namespace .*\n\{)', code, re.MULTILINE)
            if namespace_match:
                insert_pos = namespace_match.end()
                code = code[:insert_pos] + '\n' + warning_block + code[insert_pos:]

        return code, fixes_applied, warnings

    def generate_tests_for_class(self, class_info: ClassInfo) -> Optional[str]:
        """Generate tests for a single class"""
        try:
            # Determine if this is a simple class (use cheaper model)
            use_simple_model = len(class_info.methods) <= 3 and len(class_info.dependencies) <= 2

            prompt = self.generate_test_prompt(class_info, TEST_FRAMEWORK)
            response, tokens, cost = self.call_llm(prompt, use_simple_model)

            # Update stats
            self.stats.tokens_used += tokens
            self.stats.cost_usd += cost

            # Extract code
            test_code = self.extract_code_block(response)

            # Auto-fix common errors
            test_code, fixes, warnings = self.auto_fix_common_errors(test_code, class_info)

            # Track fixes and warnings in stats
            for fix in fixes:
                fix_key = fix.split(':')[0] if ':' in fix else fix
                self.stats.auto_fixes[fix_key] = self.stats.auto_fixes.get(fix_key, 0) + 1

            for warning in warnings:
                warning_key = warning.split('-')[0].strip() if '-' in warning else warning
                self.stats.warnings[warning_key] = self.stats.warnings.get(warning_key, 0) + 1

            # Log fixes if any were applied
            if fixes:
                console.print(f"[green]  ✓ Auto-fixed: {', '.join(fixes)}[/green]")

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
def main(project_dir: Path, output_dir: Optional[Path], dry_run: bool, force: bool, max_classes: Optional[int], pattern: Optional[str]):
    """
    Generate unit tests for .NET projects using AI

    Example:
        python generate_tests.py /path/to/project -o /path/to/tests
    """

    console.print(Panel.fit("🤖 .NET Unit Test Generator", style="bold blue"))

    # Validate configuration
    if not OPENAI_API_KEY:
        console.print("[red]❌ OPENAI_API_KEY not found in .env file[/red]")
        sys.exit(1)

    # Initialize
    analyzer = DotNetAnalyzer(project_dir)
    stats = TestStats()
    pattern_cache = ProjectPatternCache(project_dir)
    generator = TestGenerator(stats, project_dir, pattern_cache)

    # Show if we're using cached patterns
    if pattern_cache.patterns:
        console.print(f"[cyan]📚 Loaded {len(pattern_cache.patterns)} cached pattern(s) from previous runs[/cyan]")

    # Find C# files
    console.print(f"\n[cyan]📁 Scanning {project_dir}...[/cyan]")
    cs_files = analyzer.find_cs_files()
    console.print(f"[green]✓ Found {len(cs_files)} C# files[/green]")

    # Parse classes
    classes_to_test: List[ClassInfo] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing classes...", total=len(cs_files))

        for cs_file in cs_files:
            class_info = analyzer.parse_class(cs_file)
            if class_info and class_info.methods:
                # Apply pattern filter
                if pattern and not re.search(pattern, class_info.name):
                    progress.advance(task)
                    continue

                # Check if tests exist
                existing_tests = analyzer.find_existing_tests(class_info.name)
                if existing_tests and not force:
                    console.print(f"[yellow]⏭️  Skipping {class_info.name} (tests exist at {existing_tests.name})[/yellow]")
                    stats.tests_skipped += 1
                else:
                    classes_to_test.append(class_info)

                stats.classes_analyzed += 1
            progress.advance(task)

    # Apply max limit
    if max_classes and len(classes_to_test) > max_classes:
        classes_to_test = classes_to_test[:max_classes]
        console.print(f"[yellow]⚠️  Limited to {max_classes} classes[/yellow]")

    console.print(f"\n[green]✓ Found {len(classes_to_test)} classes needing tests[/green]")

    if dry_run:
        # Show what would be generated
        table = Table(title="Classes to Test")
        table.add_column("Class", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Methods", style="green")
        table.add_column("Dependencies", style="yellow")

        for class_info in classes_to_test:
            class_type = "Controller" if class_info.is_controller else "Service" if class_info.is_service else "Component"
            table.add_row(
                class_info.name,
                class_type,
                str(len(class_info.methods)),
                str(len(class_info.dependencies))
            )

        console.print(table)
        return

    # Determine output directory
    if not output_dir:
        # Create Tests directory next to source
        output_dir = project_dir.parent / f"{project_dir.name}.Tests"

    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[cyan]📝 Generating tests to {output_dir}...[/cyan]")

    # Generate tests
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
                # Write test file
                test_file_path = output_dir / f"{class_info.name}Tests.cs"
                test_file_path.write_text(test_code, encoding='utf-8')

                console.print(f"[green]✓ Generated {test_file_path.name}[/green]")
                stats.tests_generated += 1
            else:
                console.print(f"[red]✗ Failed to generate tests for {class_info.name}[/red]")

            progress.advance(task)

    # Print summary
    console.print("\n" + "="*60)
    console.print(Panel.fit("📊 Generation Summary", style="bold green"))

    summary_table = Table(show_header=False)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Classes Analyzed", str(stats.classes_analyzed))
    summary_table.add_row("Tests Generated", str(stats.tests_generated))
    summary_table.add_row("Tests Skipped", str(stats.tests_skipped))
    summary_table.add_row("Tokens Used", f"{stats.tokens_used:,}")
    summary_table.add_row("Estimated Cost", f"${stats.cost_usd:.4f}")

    if stats.errors:
        summary_table.add_row("Errors", str(len(stats.errors)), style="red")

    console.print(summary_table)

    # Show auto-fixes applied
    if stats.auto_fixes:
        console.print("\n[green]✓ Auto-Fixes Applied:[/green]")
        for fix_type, count in sorted(stats.auto_fixes.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  • {fix_type}: {count} file(s)")

    # Show warnings found
    if stats.warnings:
        console.print("\n[yellow]⚠️  Warnings (Review These):[/yellow]")
        for warning_type, count in sorted(stats.warnings.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  • {warning_type}: {count} file(s)")
        console.print("\n[dim]Warnings are embedded as comments in generated files for easy review[/dim]")

    if stats.errors:
        console.print("\n[red]Errors:[/red]")
        for error in stats.errors[:10]:  # Show first 10 errors
            console.print(f"  • {error}")

    console.print(f"\n[green]✓ Tests written to: {output_dir}[/green]")


if __name__ == "__main__":
    main()
