#!/usr/bin/env python3
"""
Enhanced .NET Unit Test Generator with LangChain Integration

This enhanced version includes:
1. Pattern Learning Agent (automatic pattern discovery from errors)
2. Iterative Refinement (auto-fix compilation errors)
3. Cross-File Context (learn from previous generations)
"""

import argparse
from pathlib import Path
from rich.console import Console

from generate_tests import (
    ProjectPatternCache,
    TestGenerator,
    GenerationStatistics,
    scan_csharp_files,
    get_llm
)
from langchain_pattern_learner import PatternLearningAgent
from langchain_refinement import IterativeRefinementChain
from langchain_context_manager import CrossFileContextManager

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced .NET Unit Test Generator with LangChain"
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the .NET project directory to analyze"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output directory for generated tests"
    )
    parser.add_argument(
        "-p", "--pattern",
        help="Regex pattern to filter classes (e.g., '.*Controller$')"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing test files"
    )
    parser.add_argument(
        "--auto-learn",
        action="store_true",
        help="Automatically learn patterns from compilation errors (LangChain Agent)"
    )
    parser.add_argument(
        "--auto-refine",
        action="store_true",
        help="Automatically refine tests with compilation errors (LangChain Refinement)"
    )
    parser.add_argument(
        "--use-context",
        action="store_true",
        help="Use cross-file context memory (LangChain Memory)"
    )
    parser.add_argument(
        "--max-refine-attempts",
        type=int,
        default=3,
        help="Maximum refinement attempts per file (default: 3)"
    )
    parser.add_argument(
        "--max-learn-iterations",
        type=int,
        default=3,
        help="Maximum pattern learning iterations (default: 3)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.project_dir.exists():
        console.print(f"[red]Error: Project directory not found: {args.project_dir}[/red]")
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold cyan]╭─────────────────────────────────────╮[/bold cyan]")
    console.print("[bold cyan]│ 🤖 Enhanced .NET Unit Test Generator│[/bold cyan]")
    console.print("[bold cyan]│    with LangChain Integration      │[/bold cyan]")
    console.print("[bold cyan]╰─────────────────────────────────────╯[/bold cyan]\n")

    # Initialize components
    pattern_cache = ProjectPatternCache(args.project_dir)
    stats = GenerationStatistics()

    # Load cached patterns
    if pattern_cache.patterns:
        console.print(f"[cyan]📚 Loaded {len(pattern_cache.patterns)} cached pattern(s) from previous runs[/cyan]\n")

    # Initialize context manager if requested
    context_manager = None
    if args.use_context:
        console.print("[cyan]🧠 Cross-file context memory: ENABLED[/cyan]")
        context_manager = CrossFileContextManager(args.project_dir, pattern_cache)

    # Scan project
    console.print(f"[cyan]📁 Scanning {args.project_dir}...[/cyan]")
    csharp_files = scan_csharp_files(args.project_dir)
    console.print(f"[green]✓ Found {len(csharp_files)} C# files[/green]")

    # Generate tests (using standard generator with optional context)
    generator = TestGenerator(stats, args.project_dir, pattern_cache, context_manager)

    console.print(f"\n[cyan]📝 Generating tests to {args.output}...[/cyan]")

    # Use standard generation
    from generate_tests import generate_all_tests
    generate_all_tests(
        args.project_dir,
        args.output,
        args.pattern,
        args.force,
        pattern_cache,
        stats,
        context_manager
    )

    console.print("\n[green]✓ Initial generation complete[/green]\n")

    # PHASE 1: Auto-Learn Patterns (if enabled)
    if args.auto_learn:
        console.print("\n" + "="*60)
        console.print("[bold cyan]PHASE 1: Automatic Pattern Learning[/bold cyan]")
        console.print("="*60 + "\n")

        agent = PatternLearningAgent(args.project_dir, args.output, pattern_cache)
        learn_result = agent.run(max_iterations=args.max_learn_iterations)

        if learn_result["success"]:
            console.print(f"\n[green]✓ Learned {learn_result['patterns_learned']} new pattern(s)[/green]")

            # If patterns were learned, regenerate tests
            if learn_result['patterns_learned'] > 0:
                console.print("\n[cyan]🔄 Regenerating tests with new patterns...[/cyan]")
                stats = GenerationStatistics()  # Reset stats
                generate_all_tests(
                    args.project_dir,
                    args.output,
                    args.pattern,
                    force=True,  # Always overwrite
                    pattern_cache=pattern_cache,
                    stats=stats,
                    context_manager=context_manager
                )
                console.print("[green]✓ Regeneration complete[/green]")

    # PHASE 2: Auto-Refine Tests (if enabled)
    if args.auto_refine:
        console.print("\n" + "="*60)
        console.print("[bold cyan]PHASE 2: Automatic Test Refinement[/bold cyan]")
        console.print("="*60 + "\n")

        refinement = IterativeRefinementChain(args.project_dir, pattern_cache)
        refine_result = refinement.refine_all_failed_files(
            args.output,
            max_attempts=args.max_refine_attempts
        )

        if refine_result["success"]:
            console.print(f"\n[green]✓ All tests compile successfully![/green]")
        elif refine_result["files_fixed"] > 0:
            console.print(
                f"\n[yellow]⚠ Fixed {refine_result['files_fixed']}/{refine_result['files_refined']} "
                f"file(s). {refine_result['files_remaining']} file(s) still have errors.[/yellow]"
            )

    # Final summary
    console.print("\n" + "="*60)
    console.print("[bold]📊 Final Summary[/bold]")
    console.print("="*60 + "\n")

    console.print(f"[green]✓ Tests written to: {args.output}[/green]")

    if args.use_context and context_manager:
        # Save session report
        report_path = args.output / "GENERATION_SESSION_REPORT.md"
        context_manager.save_session_report(report_path)

        # Print statistics
        session_stats = context_manager.get_statistics()
        console.print(f"\n[cyan]Session Statistics:[/cyan]")
        console.print(f"  Success Rate: {session_stats['compilation_success_rate']:.1f}%")
        console.print(f"  Average Errors per File: {session_stats['average_errors_per_file']:.1f}")

    console.print(f"\n[bold green]🎉 Enhanced generation complete![/bold green]\n")

    return 0


if __name__ == "__main__":
    exit(main())
