#!/usr/bin/env python3
"""
LangChain-powered Pattern Learning Agent

Automatically discovers and seeds patterns from compilation errors.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import ConversationSummaryMemory
from langchain.chat_models import ChatOpenAI
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from generate_tests import ProjectPatternCache, get_llm

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


class PatternLearningAgent:
    """
    LangChain agent that learns patterns from compilation errors.

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
        self.llm = get_llm()
        self.errors_history: List[List[CompilationError]] = []

        # Initialize LangChain memory
        self.memory = ConversationSummaryMemory(
            llm=self.llm,
            max_token_limit=2000,
            return_messages=True
        )

        # Create tools
        self.tools = self._create_tools()

        # Initialize agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            max_iterations=15,
            early_stopping_method="generate"
        )

    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent"""
        return [
            Tool(
                name="CompileTests",
                func=self._compile_tests,
                description=(
                    "Compile all test files and return compilation errors. "
                    "Returns: Number of errors found and summary of error types."
                )
            ),
            Tool(
                name="AnalyzeErrorPattern",
                func=self._analyze_error_pattern,
                description=(
                    "Analyze a specific error to determine if it represents a learnable pattern. "
                    "Input: Error code (e.g., 'CS0117') or error message fragment. "
                    "Returns: Pattern type (property_name, return_type, enum_values, hint) and suggested values."
                )
            ),
            Tool(
                name="SeedPattern",
                func=self._seed_pattern,
                description=(
                    "Add a new pattern to the cache. "
                    "Input: JSON string with 'type', 'context', and 'value'. "
                    "Example: '{\"type\": \"property_name\", \"context\": \"ClipboardContent.Content\", \"value\": \"Data\"}'"
                )
            ),
            Tool(
                name="GetErrorDetails",
                func=self._get_error_details,
                description=(
                    "Get detailed information about a specific error code or file. "
                    "Input: Error code (e.g., 'CS0117') or file name. "
                    "Returns: All errors matching the criteria with context."
                )
            ),
            Tool(
                name="ListCurrentPatterns",
                func=self._list_patterns,
                description=(
                    "List all currently cached patterns. "
                    "Returns: All patterns in the cache with their types and values."
                )
            ),
        ]

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

        # Pattern: /path/to/file.cs(line,column): error CODE: message
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
            # Determine category based on error code and message
            if error.code == 'CS0246':  # Type not found
                category = f"Missing type: {self._extract_type_name(error.message)}"
            elif error.code == 'CS0117':  # Member not found
                category = f"Missing member: {self._extract_member_name(error.message)}"
            elif error.code == 'CS1061':  # Missing definition
                category = f"Missing definition: {self._extract_definition(error.message)}"
            elif error.code == 'CS0104':  # Ambiguous reference
                category = f"Ambiguous type: {self._extract_ambiguous_type(error.message)}"
            elif error.code in ['CS1503', 'CS0029']:  # Type mismatch
                category = "Type mismatch"
            elif error.code == 'CS0854':  # Expression tree limitation
                category = "Expression tree issue"
            else:
                category = f"Error {error.code}"

            categories[category] = categories.get(category, 0) + 1

        return categories

    def _extract_type_name(self, message: str) -> str:
        """Extract type name from error message"""
        match = re.search(r"name '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_member_name(self, message: str) -> str:
        """Extract member name from error message"""
        match = re.search(r"definition for '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_definition(self, message: str) -> str:
        """Extract definition from error message"""
        match = re.search(r"definition for '(\w+)'", message)
        return match.group(1) if match else "unknown"

    def _extract_ambiguous_type(self, message: str) -> str:
        """Extract ambiguous type from error message"""
        match = re.search(r"'(\w+)' is an ambiguous", message)
        return match.group(1) if match else "unknown"

    def _analyze_error_pattern(self, error_query: str) -> str:
        """Analyze specific errors to identify patterns"""
        if not self.errors_history:
            return "No compilation errors available. Run CompileTests first."

        current_errors = self.errors_history[-1]
        matching_errors = [
            e for e in current_errors
            if error_query.lower() in e.code.lower() or error_query.lower() in e.message.lower()
        ]

        if not matching_errors:
            return f"No errors matching '{error_query}' found."

        # Analyze first few matching errors
        analysis = f"Found {len(matching_errors)} matching error(s). Analysis:\n\n"

        for i, error in enumerate(matching_errors[:5], 1):
            analysis += f"{i}. {error.file}:{error.line}\n"
            analysis += f"   Code: {error.code}\n"
            analysis += f"   Message: {error.message}\n"

            # Suggest pattern type
            suggestion = self._suggest_pattern(error)
            if suggestion:
                analysis += f"   💡 Suggested pattern: {suggestion}\n"

            analysis += "\n"

        return analysis

    def _suggest_pattern(self, error: CompilationError) -> Optional[str]:
        """Suggest a pattern type based on error"""
        if error.code == 'CS0117':  # Member not found
            # Extract class.member from message
            match = re.search(r"'(\w+)' does not contain a definition for '(\w+)'", error.message)
            if match:
                class_name = match.group(1)
                member_name = match.group(2)
                return f'property_name: "{class_name}.{member_name}" → "ActualPropertyName"'

        elif error.code == 'CS0104':  # Ambiguous reference
            match = re.search(r"'(\w+)' is an ambiguous reference between '([^']+)' and '([^']+)'", error.message)
            if match:
                type_name = match.group(1)
                option1 = match.group(2)
                option2 = match.group(3)
                return f'hint: "Use {option1} instead of {option2} for {type_name}"'

        elif error.code == 'CS0246':  # Type not found
            match = re.search(r"name '(\w+)' could not be found", error.message)
            if match:
                type_name = match.group(1)
                return f'hint: "Add using statement for {type_name} or use correct type name"'

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
        if not self.errors_history:
            return "No compilation errors available. Run CompileTests first."

        current_errors = self.errors_history[-1]
        matching_errors = [
            e for e in current_errors
            if query.lower() in e.code.lower() or
               query.lower() in e.file.lower() or
               query.lower() in e.message.lower()
        ]

        if not matching_errors:
            return f"No errors matching '{query}' found."

        details = f"Found {len(matching_errors)} error(s) matching '{query}':\n\n"

        for error in matching_errors[:10]:  # Limit to 10
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
        console.print("\n[bold cyan]🤖 Starting Pattern Learning Agent[/bold cyan]\n")

        initial_patterns = len(self.pattern_cache.patterns)

        # Run agent with goal
        goal = f"""
        You are a pattern learning expert for .NET unit test generation.

        Your task:
        1. Compile the tests in {self.test_dir}
        2. Analyze compilation errors to identify common patterns
        3. For each pattern you identify, seed it using SeedPattern
        4. Focus on high-frequency errors first (property names, type ambiguities, missing types)
        5. After seeding patterns, compile again to see if errors decreased
        6. Iterate up to {max_iterations} times
        7. Report what patterns you learned and remaining error count

        Pattern types you can seed:
        - property_name: Wrong property name (e.g., "ClipboardContent.Content" → "Data")
        - return_type: Wrong return type (e.g., "PagedResult" → "DataPagedResult")
        - enum_values: Valid enum values (e.g., "ConnectionType" → "P2P,Relay")
        - hint: General guidance (e.g., "Use RemoteC.Api.Services.ConnectionInfo not Microsoft.AspNetCore.Http.ConnectionInfo")

        Current patterns already cached: {len(self.pattern_cache.patterns)}

        Start by compiling tests and analyzing errors!
        """

        try:
            result = self.agent.run(goal)

            patterns_learned = len(self.pattern_cache.patterns) - initial_patterns

            console.print(f"\n[green]✓ Pattern learning complete![/green]")
            console.print(f"[green]✓ Learned {patterns_learned} new pattern(s)[/green]\n")

            return {
                "success": True,
                "patterns_learned": patterns_learned,
                "total_patterns": len(self.pattern_cache.patterns),
                "agent_output": result,
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
        console.print("[yellow]Usage: python langchain_pattern_learner.py PROJECT_DIR TEST_DIR[/yellow]")
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
    agent = PatternLearningAgent(project_dir, test_dir, pattern_cache)
    result = agent.run(max_iterations=3)

    console.print("\n[bold]Results:[/bold]")
    console.print(result)


if __name__ == "__main__":
    main()
