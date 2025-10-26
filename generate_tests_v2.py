#!/usr/bin/env python3
"""
Test Generator v2 - Modular Architecture

Uses the new provider/language/orchestrator system
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import TestGenerationOrchestrator
from providers.provider_factory import ProviderFactory
from languages.csharp_language import CSharpLanguageHandler
from languages.vbnet_language import VBNetLanguageHandler
from languages.vuejs_language import VueJSLanguageHandler
from languages.tsql_language import TSQLLanguageHandler
from patterns.pattern_cache import ProjectPatternCache

console = Console()


@click.command()
@click.argument('project_dir', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-o', '--output-dir',
    type=click.Path(path_type=Path),
    help='Output directory for test files (default: project_dir/../Tests)'
)
@click.option(
    '--provider',
    type=click.Choice(['openai', 'claude', 'gemini'], case_sensitive=False),
    default='openai',
    help='AI provider to use (default: openai with GPT-4o mini)'
)
@click.option(
    '--model',
    type=str,
    help='Override model (e.g., gpt-4o, gpt-4o-mini, claude-3-5-haiku-20241022)'
)
@click.option(
    '--language',
    type=click.Choice(['csharp', 'vbnet', 'vuejs', 'tsql'], case_sensitive=False),
    default='csharp',
    help='Source language (default: csharp)'
)
@click.option(
    '--test-framework',
    type=click.Choice(['xunit', 'nunit', 'mstest'], case_sensitive=False),
    default='xunit',
    help='Test framework to use (default: xunit)'
)
@click.option(
    '-p', '--pattern',
    type=str,
    help='Regex pattern to filter classes (e.g., ".*Controller$")'
)
@click.option(
    '-f', '--force',
    is_flag=True,
    help='Overwrite existing test files'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Analyze only, do not generate tests'
)
@click.option(
    '--cost-comparison',
    is_flag=True,
    help='Show cost comparison across providers'
)
@click.option(
    '-n', '--max-files',
    type=int,
    help='Maximum number of files to process (for testing)'
)
def main(
    project_dir: Path,
    output_dir: Optional[Path],
    provider: str,
    model: Optional[str],
    language: str,
    test_framework: str,
    pattern: Optional[str],
    force: bool,
    dry_run: bool,
    cost_comparison: bool,
    max_files: Optional[int]
):
    """
    Generate unit tests for .NET projects using AI

    EXAMPLES:

    \b
    # Basic usage (uses GPT-4o mini by default)
    python generate_tests_v2.py /path/to/project

    \b
    # Specify output directory
    python generate_tests_v2.py /path/to/project -o /path/to/tests

    \b
    # Use different provider
    python generate_tests_v2.py /path/to/project --provider claude
    python generate_tests_v2.py /path/to/project --provider gemini

    \b
    # Filter by pattern (controllers only)
    python generate_tests_v2.py /path/to/project -p ".*Controller$"

    \b
    # Dry run (estimate cost, don't generate)
    python generate_tests_v2.py /path/to/project --dry-run

    \b
    # Show cost comparison
    python generate_tests_v2.py /path/to/project --cost-comparison

    \b
    # Force overwrite existing tests
    python generate_tests_v2.py /path/to/project --force
    """
    # Load environment variables
    load_dotenv()

    # Show cost comparison if requested
    if cost_comparison:
        console.print("\n[bold cyan]Cost Comparison Across Providers[/bold cyan]\n")
        ProviderFactory.print_cost_comparison(100000, 50000)
        console.print("\n[bold]Recommendation:[/bold] Use OpenAI GPT-4o mini (default)")
        console.print("See COST-COMPARISON.md for detailed analysis\n")
        return

    # Determine output directory
    if not output_dir:
        output_dir = project_dir.parent / f"{project_dir.name}.Tests"

    # Create AI provider
    try:
        ai_provider = ProviderFactory.create_provider(provider, model=model)
        console.print(f"[green]✓[/green] Using provider: [cyan]{ai_provider.get_name()}[/cyan]")
        console.print(f"[green]✓[/green] Pricing: [yellow]{ai_provider.get_cost_summary()}[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to create provider:[/red] {e}")
        console.print("[yellow]Hint: Check your API key in .env file[/yellow]")
        sys.exit(1)

    # Create language handler
    if language == 'csharp':
        language_handler = CSharpLanguageHandler()
    elif language == 'vbnet':
        language_handler = VBNetLanguageHandler()
    elif language == 'vuejs':
        language_handler = VueJSLanguageHandler()
    elif language == 'tsql':
        language_handler = TSQLLanguageHandler()
    else:
        console.print(f"[red]✗ Unsupported language:[/red] {language}")
        sys.exit(1)

    console.print(f"[green]✓[/green] Language: [cyan]{language.upper()}[/cyan]")
    console.print(f"[green]✓[/green] Test Framework: [cyan]{test_framework.upper()}[/cyan]")

    # Create pattern cache
    pattern_cache = ProjectPatternCache(project_dir)
    console.print(f"[green]✓[/green] Pattern cache: [cyan]{pattern_cache.count()} patterns loaded[/cyan]")

    # Create orchestrator
    orchestrator = TestGenerationOrchestrator(
        project_dir=project_dir,
        output_dir=output_dir,
        provider=ai_provider,
        language_handler=language_handler,
        pattern_cache=pattern_cache
    )

    # Generate tests
    try:
        stats = orchestrator.generate_tests(
            pattern=pattern,
            force=force,
            dry_run=dry_run
        )

        # Exit with appropriate code
        if stats.failed > 0 and not dry_run:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Generation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        import traceback
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
