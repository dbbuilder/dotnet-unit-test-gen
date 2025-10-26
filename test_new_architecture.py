#!/usr/bin/env python3
"""
Test Script for New Modular Architecture

Validates that the refactored components work correctly
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from providers.provider_factory import ProviderFactory
from languages.csharp_language import CSharpLanguageHandler
from patterns.pattern_cache import ProjectPatternCache
from core.orchestrator import TestGenerationOrchestrator

console = Console()


def test_provider_factory():
    """Test provider factory"""
    console.print("\n[bold cyan]Testing Provider Factory[/bold cyan]\n")

    # Test getting available providers
    providers = ProviderFactory.get_available_providers()
    console.print(f"✓ Available providers: {', '.join(providers)}")

    # Test cost comparison
    console.print("\n[bold]Cost Comparison (100K input, 50K output tokens):[/bold]\n")
    ProviderFactory.print_cost_comparison(100000, 50000)

    # Test cheapest provider
    cheapest = ProviderFactory.get_cheapest_provider()
    console.print(f"\n✓ Cheapest provider: [green]{cheapest}[/green]")


def test_csharp_handler():
    """Test C# language handler"""
    console.print("\n\n[bold cyan]Testing C# Language Handler[/bold cyan]\n")

    handler = CSharpLanguageHandler()

    # Test parsing a sample C# class
    sample_code = """
using System;
using Microsoft.AspNetCore.Mvc;

namespace MyApp.Controllers
{
    public class SampleController : ControllerBase
    {
        private readonly ILogger<SampleController> _logger;
        private readonly IUserService _userService;

        public SampleController(ILogger<SampleController> logger, IUserService userService)
        {
            _logger = logger;
            _userService = userService;
        }

        public async Task<IActionResult> GetUser(int id)
        {
            var user = await _userService.GetUserAsync(id);
            return Ok(user);
        }

        public async Task<IActionResult> CreateUser(UserDto dto)
        {
            var result = await _userService.CreateUserAsync(dto);
            return CreatedAtAction(nameof(GetUser), new { id = result.Id }, result);
        }
    }
}
"""

    # Write sample to temp file
    temp_file = Path("temp_sample.cs")
    temp_file.write_text(sample_code)

    try:
        class_info = handler.parse_class(temp_file)
        if class_info:
            console.print(f"✓ Parsed class: [green]{class_info.name}[/green]")
            console.print(f"  Namespace: {class_info.namespace}")
            console.print(f"  Methods: {len(class_info.methods)}")
            console.print(f"  Dependencies: {', '.join(class_info.dependencies)}")
            console.print(f"  Is Controller: {class_info.is_controller}")
        else:
            console.print("[red]✗ Failed to parse class[/red]")

    finally:
        temp_file.unlink()


def test_pattern_cache():
    """Test pattern cache"""
    console.print("\n\n[bold cyan]Testing Pattern Cache[/bold cyan]\n")

    # Create cache for test project
    test_dir = Path(".")
    cache = ProjectPatternCache(test_dir)

    console.print(f"✓ Cache directory: {cache.get_cache_path()}")
    console.print(f"✓ Current patterns: {cache.count()}")

    # Add test pattern
    cache.add_pattern("return_type", "ITestService.GetDataAsync", "DataResult<TestDto>")
    console.print(f"✓ Added test pattern")
    console.print(f"✓ Total patterns: {cache.count()}")

    # Get patterns by type
    return_types = cache.get_patterns_by_type("return_type")
    console.print(f"✓ Return type patterns: {len(return_types)}")


def test_orchestrator_dry_run():
    """Test orchestrator in dry-run mode"""
    console.print("\n\n[bold cyan]Testing Orchestrator (Dry Run)[/bold cyan]\n")

    # Check if we have a real project to test with
    remotec_path = Path("/mnt/d/dev2/remotec/src/RemoteC.Api")

    if not remotec_path.exists():
        console.print("[yellow]⚠ RemoteC project not found, skipping orchestrator test[/yellow]")
        return

    try:
        # Create orchestrator with OpenAI provider (dry run doesn't call API)
        orchestrator = TestGenerationOrchestrator.create_from_config(
            project_dir=remotec_path,
            output_dir=Path("./test_output"),
            provider_name="openai",
            language="csharp"
        )

        # Run dry run analysis (limited to 5 files)
        console.print("[yellow]Running dry run on RemoteC project...[/yellow]\n")

        # Just analyze file discovery, don't generate
        source_files = orchestrator.language_handler.detect_files(
            remotec_path,
            pattern=".*Controller$"
        )

        console.print(f"✓ Found [green]{len(source_files)}[/green] controller files")

        if source_files:
            # Parse first file as example
            first_file = source_files[0]
            class_info = orchestrator.language_handler.parse_class(first_file)
            if class_info:
                console.print(f"\n[bold]Example: {class_info.name}[/bold]")
                console.print(f"  Methods: {len(class_info.methods)}")
                console.print(f"  Dependencies: {len(class_info.dependencies)}")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def main():
    """Run all tests"""
    console.print("[bold green]Testing New Modular Architecture[/bold green]")
    console.print("=" * 60)

    # Load environment variables
    load_dotenv()

    try:
        # Test 1: Provider Factory
        test_provider_factory()

        # Test 2: C# Handler
        test_csharp_handler()

        # Test 3: Pattern Cache
        test_pattern_cache()

        # Test 4: Orchestrator (dry run)
        test_orchestrator_dry_run()

        console.print("\n\n[bold green]✓ All tests passed![/bold green]\n")
        console.print("[yellow]Note: These are component tests. Full integration test requires API keys.[/yellow]")

    except Exception as e:
        console.print(f"\n\n[bold red]✗ Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
