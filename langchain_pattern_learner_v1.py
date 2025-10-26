#!/usr/bin/env python3
"""
LangChain 1.0 Pattern Learning Agent

Automatically discovers and seeds patterns from compilation errors.
Updated for LangChain 1.0 API.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from generate_tests import ProjectPatternCache

console = Console()


@dataclass
class CompilationError:
    """Represents a single compilation error"""
    file: str
    line: int
    column: int
    code: str
    message: str
    context: Optional[str] = None


class PatternLearningAgentV1:
    """
    LangChain 1.0 agent that learns patterns from compilation errors.

    This agent:
    1. Compiles generated tests
    2. Analyzes errors to identify patterns
    3. Seeds patterns automatically
    4. Iterates until errors are minimized
    """

    def __init__(self, project_dir: Path, test_dir: Path, pattern_cache: ProjectPatternCache):
        self.project_dir = project_dir
        self.test_dir = test_dir
        self.pattern_cache = pattern_cache
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.errors_history: List[List[CompilationError]] = []
        self.current_errors: List[CompilationError] = []

        # Create agent with tools
        self.agent = self._create_agent()

    def _create_agent(self):
        """Create the LangChain 1.0 agent with tools"""

        # Define tools using the new @tool decorator
        @tool
        def compile_tests(query: str = "") -> str:
            """Compile all test files and return compilation errors.

            Returns: Number of errors found and summary of error types.
            """
            return self._compile_tests(query)

        @tool
        def analyze_error_pattern(error_query: str) -> str:
            """Analyze a specific error to determine if it represents a learnable pattern.

            Args:
                error_query: Error code (e.g., 'CS0117') or error message fragment

            Returns: Pattern type and suggested values.
            """
            return self._analyze_error_pattern(error_query)

        @tool
        def seed_pattern(pattern_json: str) -> str:
            """Add a new pattern to the cache.

            Args:
                pattern_json: JSON string with 'type', 'context', and 'value'
                Example: '{"type": "property_name", "context": "ClipboardContent.Content", "value": "Data"}'

            Returns: Success or error message.
            """
            return self._seed_pattern(pattern_json)

        @tool
        def get_error_details(query: str) -> str:
            """Get detailed information about a specific error code or file.

            Args:
                query: Error code (e.g., 'CS0117') or file name

            Returns: All errors matching the criteria with context.
            """
            return self._get_error_details(query)

        @tool
        def list_current_patterns(query: str = "") -> str:
            """List all currently cached patterns.

            Returns: All patterns in the cache with their types and values.
            """
            return self._list_patterns(query)

        tools = [
            compile_tests,
            analyze_error_pattern,
            seed_pattern,
            get_error_details,
            list_current_patterns
        ]

        # Create agent using new API
        agent = create_react_agent(self.llm, tools)
        return agent

    def _compile_tests(self, _: str = "") -> str:
        """Compile all tests and return error summary"""
        console.print("[cyan]🔨 Compiling tests...[/cyan]")

        try:
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=self.test_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse errors
            errors = self._parse_compilation_output(result.stdout + result.stderr)
            self.current_errors = errors
            self.errors_history.append(errors)

            if not errors:
                return "✅ Build succeeded! No compilation errors found."

            # Categorize errors
            error_summary = self._categorize_errors(errors)

            summary = f"❌ Build failed with {len(errors)} error(s):\n\n"
            for category, count in error_summary.items():
                summary += f"  • {category}: {count} occurrence(s)\n"

            return summary

        except subprocess.TimeoutExpired:
            return "⏱️ Compilation timed out after 120 seconds"
        except Exception as e:
            return f"❌ Error during compilation: {str(e)}"

    def _parse_compilation_output(self, output: str) -> List[CompilationError]:
        """Parse dotnet build output to extract errors"""
        errors = []
        error_pattern = r'([^(]+)\((\d+),(\d+)\):\s*error\s+(\w+):\s*(.+)'

        for line in output.split('\n'):
            match = re.search(error_pattern, line)
            if match:
                file_path = match.group(1).strip()
                errors.append(CompilationError(
                    file=Path(file_path).name,
                    line=int(match.group(2)),
                    column=int(match.group(3)),
                    code=match.group(4),
                    message=match.group(5).strip()
                ))

        return errors

    def _categorize_errors(self, errors: List[CompilationError]) -> Dict[str, int]:
        """Categorize errors by type"""
        categories = {}

        for error in errors:
            if error.code == 'CS0246':
                category = f"Missing type: {self._extract_type_name(error.message)}"
            elif error.code == 'CS0117':
                category = f"Missing member: {self._extract_member_name(error.message)}"
            elif error.code == 'CS1061':
                category = f"Missing definition: {self._extract_definition(error.message)}"
            elif error.code == 'CS0104':
                category = f"Ambiguous type: {self._extract_ambiguous_type(error.message)}"
            elif error.code in ['CS1503', 'CS0029']:
                category = "Type mismatch"
            elif error.code == 'CS0854':
                category = "Expression tree issue"
            else:
                category = f"Error {error.code}"

            categories[category] = categories.get(category, 0) + 1

        return categories

    def _extract_type_name(self, message: str) -> str:
        match = re.search(r"name '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_member_name(self, message: str) -> str:
        match = re.search(r"definition for '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_definition(self, message: str) -> str:
        match = re.search(r"definition for '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_ambiguous_type(self, message: str) -> str:
        match = re.search(r"'(\w+)' is an ambiguous", message)
        return match.group(1) if match else "unknown"

    def _analyze_error_pattern(self, error_query: str) -> str:
        """Analyze specific errors to identify patterns"""
        if not self.current_errors:
            return "No compilation errors available. Run compile_tests first."

        matching_errors = [
            e for e in self.current_errors
            if error_query.lower() in e.code.lower() or error_query.lower() in e.message.lower()
        ]

        if not matching_errors:
            return f"No errors matching '{error_query}' found."

        analysis = f"Found {len(matching_errors)} matching error(s). Analysis:\n\n"

        for i, error in enumerate(matching_errors[:5], 1):
            analysis += f"{i}. {error.file}:{error.line}\n"
            analysis += f"   Code: {error.code}\n"
            analysis += f"   Message: {error.message}\n"

            suggestion = self._suggest_pattern(error)
            if suggestion:
                analysis += f"   💡 Suggested pattern: {suggestion}\n"

            analysis += "\n"

        return analysis

    def _suggest_pattern(self, error: CompilationError) -> Optional[str]:
        """Suggest a pattern type based on error"""
        if error.code == 'CS0117':
            match = re.search(r"'(\w+)' does not contain a definition for '(\w+)'", error.message)
            if match:
                class_name = match.group(1)
                member_name = match.group(2)
                return f'property_name: "{class_name}.{member_name}" → "ActualPropertyName"'

        elif error.code == 'CS0104':
            match = re.search(r"'(\w+)' is an ambiguous reference between '([^']+)' and '([^']+)'", error.message)
            if match:
                type_name = match.group(1)
                option1 = match.group(2)
                return f'hint: "Use {option1} instead of {type_name}"'

        return None

    def _seed_pattern(self, pattern_json: str) -> str:
        """Seed a new pattern"""
        import json

        try:
            pattern_data = json.loads(pattern_json)
            pattern_type = pattern_data['type']
            context = pattern_data['context']
            value = pattern_data['value']

            self.pattern_cache.add_pattern(pattern_type, context, value)

            return f"✅ Pattern added: {pattern_type} | {context} → {value}"

        except json.JSONDecodeError:
            return f"❌ Invalid JSON: {pattern_json}"
        except KeyError as e:
            return f"❌ Missing required field: {e}"
        except Exception as e:
            return f"❌ Error seeding pattern: {str(e)}"

    def _get_error_details(self, query: str) -> str:
        """Get detailed error information"""
        if not self.current_errors:
            return "No compilation errors available. Run compile_tests first."

        matching_errors = [
            e for e in self.current_errors
            if query.lower() in e.code.lower() or
               query.lower() in e.file.lower() or
               query.lower() in e.message.lower()
        ]

        if not matching_errors:
            return f"No errors matching '{query}' found."

        details = f"Found {len(matching_errors)} error(s) matching '{query}':\n\n"

        for error in matching_errors[:10]:
            details += f"File: {error.file}:{error.line}:{error.column}\n"
            details += f"Code: {error.code}\n"
            details += f"Message: {error.message}\n"
            details += "-" * 60 + "\n"

        return details

    def _list_patterns(self, _: str = "") -> str:
        """List all current patterns"""
        if not self.pattern_cache.patterns:
            return "No patterns cached yet."

        output = f"Found {len(self.pattern_cache.patterns)} pattern(s):\n\n"

        for i, pattern in enumerate(self.pattern_cache.patterns, 1):
            output += f"{i}. Type: {pattern['pattern_type']}\n"
            output += f"   Context: {pattern['context']}\n"
            output += f"   Value: {pattern['value']}\n\n"

        return output

    def run(self, max_iterations: int = 3) -> Dict[str, any]:
        """
        Run the pattern learning agent.

        Returns:
            Dictionary with results including patterns learned, errors remaining, etc.
        """
        console.print("\n[bold cyan]🤖 Starting Pattern Learning Agent (LangChain 1.0)[/bold cyan]\n")

        initial_patterns = len(self.pattern_cache.patterns)

        # Goal for the agent
        goal = f"""
        You are a pattern learning expert for .NET unit test generation.

        Your task:
        1. Use compile_tests to compile the tests in {self.test_dir}
        2. Analyze compilation errors to identify common patterns
        3. For each pattern you identify, use seed_pattern to add it
        4. Focus on high-frequency errors first (property names, type ambiguities)
        5. After seeding patterns, compile again to see if errors decreased
        6. Iterate up to {max_iterations} times
        7. Report what patterns you learned and remaining error count

        Pattern types you can seed:
        - property_name: Wrong property name (e.g., "ClipboardContent.Content" → "Data")
        - return_type: Wrong return type (e.g., "PagedResult" → "DataPagedResult")
        - enum_values: Valid enum values (e.g., "ConnectionType" → "P2P,Relay")
        - hint: General guidance (e.g., "Use RemoteC.Api.Services.ConnectionInfo")

        Current patterns already cached: {len(self.pattern_cache.patterns)}

        Start by using compile_tests to see the current errors!
        """

        try:
            # Invoke agent with the goal and increased recursion limit
            result = self.agent.invoke(
                {"messages": [("user", goal)]},
                {"recursion_limit": 100}  # Increased to allow more tool calls
            )

            # Extract the final message
            messages = result.get("messages", [])
            final_message = messages[-1].content if messages else "No response"

            patterns_learned = len(self.pattern_cache.patterns) - initial_patterns

            console.print(f"\n[green]✓ Pattern learning complete![/green]")
            console.print(f"[green]✓ Learned {patterns_learned} new pattern(s)[/green]\n")

            return {
                "success": True,
                "patterns_learned": patterns_learned,
                "total_patterns": len(self.pattern_cache.patterns),
                "agent_output": final_message,
                "error_history": self.errors_history
            }

        except Exception as e:
            console.print(f"[red]❌ Error during pattern learning: {str(e)}[/red]")
            return {
                "success": False,
                "error": str(e),
                "patterns_learned": len(self.pattern_cache.patterns) - initial_patterns
            }


def main():
    """Test the pattern learning agent"""
    import sys

    if len(sys.argv) < 3:
        console.print("[yellow]Usage: python langchain_pattern_learner_v1.py PROJECT_DIR TEST_DIR[/yellow]")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    test_dir = Path(sys.argv[2])

    if not project_dir.exists():
        console.print(f"[red]Error: Project directory not found: {project_dir}[/red]")
        sys.exit(1)

    if not test_dir.exists():
        console.print(f"[red]Error: Test directory not found: {test_dir}[/red]")
        sys.exit(1)

    # Initialize pattern cache
    pattern_cache = ProjectPatternCache(project_dir)

    # Create and run agent
    agent = PatternLearningAgentV1(project_dir, test_dir, pattern_cache)
    result = agent.run(max_iterations=3)

    console.print("\n[bold]Results:[/bold]")
    console.print(result)


if __name__ == "__main__":
    main()
