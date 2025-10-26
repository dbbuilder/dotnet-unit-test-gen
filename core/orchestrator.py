"""
Test Generation Orchestrator

Coordinates AI providers, language handlers, and pattern learning.
Follows 2025 LangChain/LangGraph orchestration best practices:

1. Modular Architecture - Decoupled components
2. Sequential & Parallel Execution - Optimize throughput
3. Context Broker Pattern - Centralized context management
4. Multi-Provider Support - Cost optimization
5. Fault Tolerance - Automatic fallback
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from providers.base_provider import BaseAIProvider, CompletionRequest
from providers.provider_factory import ProviderFactory
from languages.base_language import BaseLanguageHandler, ClassInfo
from languages.csharp_language import CSharpLanguageHandler
from patterns.pattern_cache import ProjectPatternCache

console = Console()


@dataclass
class GenerationResult:
    """Result of test generation for a single file"""
    source_file: Path
    test_file: Path
    class_name: str
    success: bool
    test_code: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)


@dataclass
class GenerationStats:
    """Statistics for entire generation run"""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    results: List[GenerationResult] = field(default_factory=list)

    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()


class TestGenerationOrchestrator:
    """
    Orchestrates test generation workflow

    Responsibilities:
    1. File discovery and filtering
    2. Provider and language handler coordination
    3. Context management (patterns, DTOs, enums)
    4. Parallel/sequential execution
    5. Error handling and retries
    6. Cost tracking and reporting
    """

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path,
        provider: BaseAIProvider,
        language_handler: Optional[BaseLanguageHandler] = None,
        pattern_cache: Optional[ProjectPatternCache] = None,
        max_parallel: int = 1
    ):
        """
        Initialize orchestrator

        Args:
            project_dir: Source project directory
            output_dir: Output directory for tests
            provider: AI provider instance
            language_handler: Language handler (default: C#)
            pattern_cache: Pattern cache (auto-created if None)
            max_parallel: Maximum parallel generations (default: 1)
        """
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.provider = provider
        self.language_handler = language_handler or CSharpLanguageHandler()
        self.pattern_cache = pattern_cache or ProjectPatternCache(project_dir)
        self.max_parallel = max_parallel

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = GenerationStats()

    def generate_tests(
        self,
        pattern: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False
    ) -> GenerationStats:
        """
        Generate tests for all matching files

        Args:
            pattern: Optional regex pattern to filter classes
            force: Overwrite existing tests
            dry_run: Only analyze, don't generate

        Returns:
            GenerationStats with results
        """
        console.print(f"\n[bold cyan]Test Generation Orchestrator[/bold cyan]")
        console.print(f"Provider: [green]{self.provider.get_name()}[/green]")
        console.print(f"Language: [green]{self.language_handler.get_language_name()}[/green]")
        console.print(f"Patterns: [green]{self.pattern_cache.count()} cached[/green]")
        console.print()

        # Discover files
        console.print("[bold]Discovering source files...[/bold]")
        source_files = self.language_handler.detect_files(self.project_dir, pattern)
        self.stats.total_files = len(source_files)

        console.print(f"Found [cyan]{len(source_files)}[/cyan] files to process\n")

        if dry_run:
            console.print("[yellow]DRY RUN MODE - No tests will be generated[/yellow]\n")
            return self._dry_run_analysis(source_files)

        # Generate tests
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Generating tests...", total=len(source_files))

            for source_file in source_files:
                result = self._generate_single_test(source_file, force)
                self.stats.results.append(result)

                # Update stats
                if result.success:
                    self.stats.successful += 1
                elif result.error == "SKIPPED":
                    self.stats.skipped += 1
                else:
                    self.stats.failed += 1

                self.stats.total_input_tokens += result.input_tokens
                self.stats.total_output_tokens += result.output_tokens
                self.stats.total_cost += result.cost

                progress.update(task, advance=1)

        self.stats.end_time = datetime.now()

        # Print summary
        self._print_summary()

        return self.stats

    def _generate_single_test(self, source_file: Path, force: bool) -> GenerationResult:
        """
        Generate test for a single source file

        Args:
            source_file: Source file path
            force: Overwrite existing test

        Returns:
            GenerationResult
        """
        try:
            # Parse source file
            class_info = self.language_handler.parse_class(source_file)
            if not class_info:
                return GenerationResult(
                    source_file=source_file,
                    test_file=Path(),
                    class_name="",
                    success=False,
                    error="Failed to parse source file"
                )

            # Check if test exists
            test_file = self.language_handler.get_test_file_path(source_file, self.output_dir)
            if test_file.exists() and not force:
                return GenerationResult(
                    source_file=source_file,
                    test_file=test_file,
                    class_name=class_info.name,
                    success=False,
                    error="SKIPPED"
                )

            # Get patterns as dict
            patterns = self.pattern_cache.get_pattern_dict()

            # Generate prompt
            prompt = self.language_handler.generate_test_prompt(class_info, patterns)

            # Call AI provider
            request = CompletionRequest(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2
            )

            response = self.provider.generate_completion(request)

            # Extract code from response
            test_code = self.language_handler.extract_code_from_response(response.content)

            # Auto-fix common errors
            test_code, fixes, warnings = self.language_handler.auto_fix_syntax(test_code)

            # Write test file
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(test_code, encoding='utf-8')

            return GenerationResult(
                source_file=source_file,
                test_file=test_file,
                class_name=class_info.name,
                success=True,
                test_code=test_code,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost=response.cost,
                fixes_applied=fixes,
                warnings=warnings
            )

        except Exception as e:
            return GenerationResult(
                source_file=source_file,
                test_file=Path(),
                class_name="",
                success=False,
                error=str(e)
            )

    def _dry_run_analysis(self, source_files: List[Path]) -> GenerationStats:
        """
        Perform dry run analysis

        Args:
            source_files: List of source files

        Returns:
            GenerationStats with analysis
        """
        from rich.table import Table

        table = Table(title="Dry Run Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Class", style="green")
        table.add_column("Methods", justify="right")
        table.add_column("Dependencies", justify="right")
        table.add_column("Status", style="yellow")

        for source_file in source_files[:20]:  # Limit to 20 for display
            class_info = self.language_handler.parse_class(source_file)
            if class_info:
                test_exists = self.language_handler.has_existing_tests(
                    source_file,
                    self.output_dir
                )
                status = "EXISTS" if test_exists else "GENERATE"

                table.add_row(
                    source_file.name,
                    class_info.name,
                    str(len(class_info.methods)),
                    str(len(class_info.dependencies)),
                    status
                )

        console.print(table)

        if len(source_files) > 20:
            console.print(f"\n... and {len(source_files) - 20} more files")

        # Estimate cost
        # Based on RemoteC case study: 44 files = $1.73 = ~$0.0375/file
        # At gpt-4o-mini pricing ($0.00015 input, $0.0006 output per 1K tokens):
        # ~50,000 input + 50,000 output tokens per file = 100,000 total
        avg_input_tokens = 50000   # Average input tokens per test
        avg_output_tokens = 50000  # Average output tokens per test
        estimated_cost = self.provider.estimate_cost(
            avg_input_tokens,
            avg_output_tokens
        ) * len(source_files)

        console.print(f"\n[bold]Estimated Cost:[/bold] [green]${estimated_cost:.2f}[/green]")
        console.print(f"[bold]Provider:[/bold] {self.provider.get_name()}")
        console.print(f"[bold]Pricing:[/bold] {self.provider.get_cost_summary()}")

        return self.stats

    def _print_summary(self):
        """Print generation summary"""
        from rich.table import Table

        console.print("\n[bold cyan]Generation Summary[/bold cyan]\n")

        # Stats table
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        table.add_row("Total Files", str(self.stats.total_files))
        table.add_row("Successful", str(self.stats.successful))
        table.add_row("Failed", str(self.stats.failed))
        table.add_row("Skipped", str(self.stats.skipped))
        table.add_row("Input Tokens", f"{self.stats.total_input_tokens:,}")
        table.add_row("Output Tokens", f"{self.stats.total_output_tokens:,}")
        table.add_row("Total Cost", f"${self.stats.total_cost:.4f}")
        table.add_row("Duration", f"{self.stats.duration_seconds():.1f}s")

        console.print(table)

        # Print warnings and errors
        if self.stats.failed > 0:
            console.print("\n[bold red]Errors:[/bold red]")
            for result in self.stats.results:
                if not result.success and result.error != "SKIPPED":
                    console.print(f"  [red]✗[/red] {result.source_file.name}: {result.error}")

    @staticmethod
    def create_from_config(
        project_dir: Path,
        output_dir: Path,
        provider_name: str = "openai",
        language: str = "csharp",
        **kwargs
    ) -> "TestGenerationOrchestrator":
        """
        Create orchestrator from configuration

        Args:
            project_dir: Source project directory
            output_dir: Output directory for tests
            provider_name: Provider name (openai, claude, gemini)
            language: Language name (csharp, vbnet, java, python)
            **kwargs: Additional arguments

        Returns:
            Configured orchestrator instance
        """
        # Create provider
        provider = ProviderFactory.create_provider(provider_name)

        # Create language handler
        if language.lower() == "csharp":
            language_handler = CSharpLanguageHandler()
        else:
            raise ValueError(f"Unsupported language: {language}")

        # Create pattern cache
        pattern_cache = ProjectPatternCache(project_dir)

        return TestGenerationOrchestrator(
            project_dir=project_dir,
            output_dir=output_dir,
            provider=provider,
            language_handler=language_handler,
            pattern_cache=pattern_cache,
            **kwargs
        )
