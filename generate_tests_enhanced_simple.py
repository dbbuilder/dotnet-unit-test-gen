#!/usr/bin/env python3
"""
Simplified Enhanced .NET Unit Test Generator with LangChain Integration

This version works with the existing generate_tests.py and adds LangChain features on top.
"""

import argparse
import subprocess
from pathlib import Path
from rich.console import Console

from langchain_pattern_learner import PatternLearningAgent
from langchain_refinement import IterativeRefinementChain
from generate_tests import ProjectPatternCache

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
        help="Automatically learn patterns from compilation errors"
    )
    parser.add_argument(
        "--auto-refine",
        action="store_true",
        help="Automatically refine tests with compilation errors"
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

    # Initialize pattern cache
    pattern_cache = ProjectPatternCache(args.project_dir)

    # Load cached patterns
    if pattern_cache.patterns:
        console.print(f"[cyan]📚 Loaded {len(pattern_cache.patterns)} cached pattern(s)[/cyan]\n")

    # PHASE 0: Run standard generator
    console.print("[bold cyan]PHASE 0: Generating Tests[/bold cyan]")
    console.print("="*60 + "\n")

    gen_cmd = [
        "python", "generate_tests.py",
        str(args.project_dir),
        "-o", str(args.output)
    ]

    if args.pattern:
        gen_cmd.extend(["-p", args.pattern])

    if args.force:
        gen_cmd.append("--force")

    try:
        result = subprocess.run(gen_cmd, check=True, capture_output=False)
        console.print("\n[green]✓ Initial generation complete[/green]\n")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]✗ Generation failed: {e}[/red]")
        return 1

    # PHASE 1: Auto-Learn Patterns (if enabled)
    if args.auto_learn:
        console.print("\n" + "="*60)
        console.print("[bold cyan]PHASE 1: Automatic Pattern Learning[/bold cyan]")
        console.print("="*60 + "\n")

        try:
            agent = PatternLearningAgent(args.project_dir, args.output, pattern_cache)
            learn_result = agent.run(max_iterations=args.max_learn_iterations)

            if learn_result["success"] and learn_result["patterns_learned"] > 0:
                console.print(f"\n[green]✓ Learned {learn_result['patterns_learned']} new pattern(s)[/green]")

                # Regenerate with new patterns
                console.print("\n[cyan]🔄 Regenerating tests with new patterns...[/cyan]")
                regen_cmd = gen_cmd.copy()
                if "--force" not in regen_cmd:
                    regen_cmd.append("--force")

                subprocess.run(regen_cmd, check=True, capture_output=False)
                console.print("[green]✓ Regeneration complete[/green]")

        except Exception as e:
            console.print(f"[yellow]⚠ Pattern learning encountered an error: {e}[/yellow]")
            console.print("[yellow]Continuing with refinement phase...[/yellow]")

    # PHASE 2: Auto-Refine Tests (if enabled)
    if args.auto_refine:
        console.print("\n" + "="*60)
        console.print("[bold cyan]PHASE 2: Automatic Test Refinement[/bold cyan]")
        console.print("="*60 + "\n")

        try:
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

        except Exception as e:
            console.print(f"[yellow]⚠ Refinement encountered an error: {e}[/yellow]")

    # Final summary
    console.print("\n" + "="*60)
    console.print("[bold]📊 Final Summary[/bold]")
    console.print("="*60 + "\n")

    console.print(f"[green]✓ Tests written to: {args.output}[/green]")
    console.print(f"\n[bold green]🎉 Enhanced generation complete![/bold green]\n")

    return 0


if __name__ == "__main__":
    exit(main())
