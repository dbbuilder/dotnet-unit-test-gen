#!/usr/bin/env python3
"""
.NET Unit Test Generator using LiteLLM
Supports OpenAI API and GitHub Copilot with automatic fallback
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
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
class TestStats:
    """Statistics for test generation"""
    classes_analyzed: int = 0
    tests_generated: int = 0
    tests_skipped: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


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

    def __init__(self, stats: TestStats):
        self.stats = stats
        # Configure LiteLLM
        litellm.set_verbose = False
        if OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    def generate_test_prompt(self, class_info: ClassInfo, framework: str = "xunit") -> str:
        """Generate the prompt for test generation"""

        # Truncate source if too large
        max_source_len = 8000
        source = class_info.source_code
        if len(source) > max_source_len:
            source = source[:max_source_len] + "\n// ... (truncated)"

        prompt = f"""You are an expert .NET test engineer. Generate comprehensive unit tests for the following C# class.

**Class to Test:**
```csharp
{source}
```

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
    generator = TestGenerator(stats)

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

    if stats.errors:
        console.print("\n[red]Errors:[/red]")
        for error in stats.errors[:10]:  # Show first 10 errors
            console.print(f"  • {error}")

    console.print(f"\n[green]✓ Tests written to: {output_dir}[/green]")


if __name__ == "__main__":
    main()
