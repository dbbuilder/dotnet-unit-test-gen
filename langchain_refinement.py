#!/usr/bin/env python3
"""
LangChain-powered Iterative Refinement

Automatically fixes compilation errors in generated tests.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage
from rich.console import Console
from rich.progress import track

from generate_tests import ProjectPatternCache, get_llm

console = Console()


@dataclass
class FileError:
    """Represents compilation errors for a single file"""
    file_path: Path
    errors: List[str]
    error_count: int


class IterativeRefinementChain:
    """
    LangChain chain for iterative test refinement.

    This chain:
    1. Takes generated test code
    2. Compiles it to find errors
    3. Uses LLM to fix errors with context from previous attempts
    4. Iterates until compilation succeeds or max attempts reached
    """

    def __init__(self, project_dir: Path, pattern_cache: ProjectPatternCache):
        self.project_dir = project_dir
        self.pattern_cache = pattern_cache
        self.llm = get_llm()

        # Create refinement chain
        self.chain = self._create_refinement_chain()

    def _create_refinement_chain(self) -> LLMChain:
        """Create the refinement chain with conversation memory"""

        # Prompt template for refinement
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert .NET test refinement assistant.

Your job is to fix compilation errors in unit tests while maintaining:
- Test structure (AAA pattern: Arrange, Act, Assert)
- Moq syntax for mocking
- FluentAssertions syntax for assertions
- xUnit test framework conventions

Common fixes needed:
1. Missing using statements → Add appropriate using directives
2. Wrong property names → Use actual DTO property names
3. Wrong return types → Use correct types from repositories
4. Ambiguous types → Use fully qualified names or correct using statements
5. FluentAssertions syntax → Use correct assertion methods
6. Expression tree errors → Remove default parameters from mock setups

When fixing:
- Make MINIMAL changes (only what's needed to fix errors)
- Preserve test logic and intent
- Use patterns from the cache when available
- Add comments explaining non-obvious fixes

Available patterns:
{patterns}
"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """Fix the compilation errors in this test file.

File: {file_name}

Current test code:
```csharp
{test_code}
```

Compilation errors:
{errors}

Please provide the COMPLETE corrected test code (no explanations, just the code).
Make sure to:
1. Fix all compilation errors
2. Maintain the same test structure
3. Use patterns from the cache where applicable
4. Add minimal, necessary changes only
"""),
        ])

        # Memory for conversation history (last 3 exchanges)
        memory = ConversationBufferWindowMemory(
            k=3,
            return_messages=True,
            memory_key="history"
        )

        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=memory,
            verbose=True
        )

    def _compile_file(self, file_path: Path, test_dir: Path) -> List[str]:
        """Compile a single test file and return errors"""
        try:
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Extract errors for this specific file
            errors = []
            file_name = file_path.name

            for line in (result.stdout + result.stderr).split('\n'):
                if file_name in line and 'error' in line.lower():
                    # Extract just the error message
                    match = re.search(r'error\s+\w+:\s*(.+?)(?:\[|$)', line)
                    if match:
                        errors.append(match.group(1).strip())

            return errors

        except Exception as e:
            return [f"Compilation failed: {str(e)}"]

    def refine_file(self, file_path: Path, test_dir: Path, max_attempts: int = 3) -> Dict[str, any]:
        """
        Iteratively refine a single test file.

        Args:
            file_path: Path to the test file
            test_dir: Directory containing test project
            max_attempts: Maximum refinement attempts

        Returns:
            Dictionary with success status, attempts made, and final errors
        """
        console.print(f"\n[cyan]🔧 Refining {file_path.name}...[/cyan]")

        original_code = file_path.read_text()
        current_code = original_code

        # Get patterns as formatted string
        patterns_str = self._format_patterns()

        for attempt in range(1, max_attempts + 1):
            console.print(f"  [yellow]Attempt {attempt}/{max_attempts}[/yellow]")

            # Compile and get errors
            errors = self._compile_file(file_path, test_dir)

            if not errors:
                console.print(f"  [green]✓ Compilation successful![/green]")
                return {
                    "success": True,
                    "attempts": attempt,
                    "errors_remaining": 0,
                    "code_changed": current_code != original_code
                }

            console.print(f"  [red]✗ {len(errors)} error(s) found[/red]")

            # Use LLM to fix errors
            try:
                errors_formatted = "\n".join(f"{i+1}. {err}" for i, err in enumerate(errors[:10]))

                refined_code = self.chain.run(
                    file_name=file_path.name,
                    test_code=current_code,
                    errors=errors_formatted,
                    patterns=patterns_str
                )

                # Extract code from markdown if present
                refined_code = self._extract_code_from_markdown(refined_code)

                # Write refined code
                file_path.write_text(refined_code)
                current_code = refined_code

            except Exception as e:
                console.print(f"  [red]✗ Refinement failed: {str(e)}[/red]")
                # Restore original code
                file_path.write_text(original_code)
                return {
                    "success": False,
                    "attempts": attempt,
                    "errors_remaining": len(errors),
                    "error": str(e)
                }

        # Max attempts reached
        final_errors = self._compile_file(file_path, test_dir)
        console.print(f"  [yellow]⚠ Max attempts reached. {len(final_errors)} error(s) remaining[/yellow]")

        return {
            "success": len(final_errors) == 0,
            "attempts": max_attempts,
            "errors_remaining": len(final_errors),
            "final_errors": final_errors
        }

    def refine_all_failed_files(self, test_dir: Path, max_attempts: int = 3) -> Dict[str, any]:
        """
        Refine all files with compilation errors.

        Args:
            test_dir: Directory containing test project
            max_attempts: Maximum refinement attempts per file

        Returns:
            Dictionary with overall results
        """
        console.print("\n[bold cyan]🔧 Starting Iterative Refinement[/bold cyan]")

        # First, compile to find all failed files
        console.print("[cyan]Finding files with errors...[/cyan]")
        failed_files = self._get_failed_files(test_dir)

        if not failed_files:
            console.print("[green]✓ All tests compile successfully![/green]")
            return {
                "success": True,
                "files_refined": 0,
                "files_fixed": 0,
                "files_remaining": 0
            }

        console.print(f"[yellow]Found {len(failed_files)} file(s) with errors[/yellow]\n")

        # Refine each failed file
        results = []
        files_fixed = 0

        for file_error in track(failed_files, description="Refining files..."):
            result = self.refine_file(file_error.file_path, test_dir, max_attempts)
            results.append({
                "file": file_error.file_path.name,
                **result
            })

            if result["success"]:
                files_fixed += 1

        # Summary
        console.print(f"\n[bold]Refinement Summary:[/bold]")
        console.print(f"  Files with errors: {len(failed_files)}")
        console.print(f"  Files fixed: {files_fixed}")
        console.print(f"  Files remaining: {len(failed_files) - files_fixed}")

        return {
            "success": files_fixed == len(failed_files),
            "files_refined": len(failed_files),
            "files_fixed": files_fixed,
            "files_remaining": len(failed_files) - files_fixed,
            "details": results
        }

    def _get_failed_files(self, test_dir: Path) -> List[FileError]:
        """Get list of files with compilation errors"""
        try:
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse errors by file
            file_errors: Dict[str, List[str]] = {}

            for line in (result.stdout + result.stderr).split('\n'):
                if 'error' in line.lower():
                    # Extract file path
                    match = re.search(r'([^(]+\.cs)\(\d+,\d+\):', line)
                    if match:
                        file_path = match.group(1).strip()
                        file_name = Path(file_path).name

                        # Extract error message
                        error_match = re.search(r'error\s+\w+:\s*(.+?)(?:\[|$)', line)
                        if error_match:
                            error_msg = error_match.group(1).strip()

                            if file_name not in file_errors:
                                file_errors[file_name] = []
                            file_errors[file_name].append(error_msg)

            # Convert to FileError objects
            failed_files = []
            for file_name, errors in file_errors.items():
                file_path = test_dir / file_name
                if file_path.exists():
                    failed_files.append(FileError(
                        file_path=file_path,
                        errors=errors,
                        error_count=len(errors)
                    ))

            # Sort by error count (fix files with fewer errors first)
            failed_files.sort(key=lambda x: x.error_count)

            return failed_files

        except Exception as e:
            console.print(f"[red]Error getting failed files: {str(e)}[/red]")
            return []

    def _format_patterns(self) -> str:
        """Format cached patterns for prompt"""
        if not self.pattern_cache.patterns:
            return "No patterns cached yet."

        patterns_str = ""
        for pattern in self.pattern_cache.patterns:
            patterns_str += f"- {pattern['pattern_type']}: {pattern['context']} → {pattern['value']}\n"

        return patterns_str

    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract code from markdown code blocks if present"""
        # Check for ```csharp code blocks
        match = re.search(r'```(?:csharp|cs)?\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no code block, return as-is (assume it's already code)
        return text.strip()


def main():
    """Test the refinement chain"""
    import sys

    if len(sys.argv) < 3:
        console.print("[yellow]Usage: python langchain_refinement.py PROJECT_DIR TEST_DIR[/yellow]")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    test_dir = Path(sys.argv[2])

    if not project_dir.exists():
        console.print(f"[red]Error: Project directory not found: {project_dir}[/red]")
        sys.exit(1)

    if not test_dir.exists():
        console.print(f"[red]Error: Test directory not found: {test_dir}[/red]")
        sys.exit(1)

    # Initialize pattern cache and refinement chain
    pattern_cache = ProjectPatternCache(project_dir)
    refinement = IterativeRefinementChain(project_dir, pattern_cache)

    # Refine all failed files
    result = refinement.refine_all_failed_files(test_dir, max_attempts=3)

    console.print("\n[bold]Final Results:[/bold]")
    console.print(result)


if __name__ == "__main__":
    main()
