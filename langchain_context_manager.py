#!/usr/bin/env python3
"""
LangChain-powered Cross-File Context Manager

Maintains context across test file generation to avoid repeating mistakes.
"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import HumanMessage, AIMessage
from rich.console import Console

from generate_tests import ProjectPatternCache, get_llm, ClassInfo

console = Console()


@dataclass
class GenerationContext:
    """Context from a successfully generated test"""
    class_name: str
    file_name: str
    patterns_used: List[str]
    compilation_success: bool
    errors_encountered: List[str]
    timestamp: datetime


class CrossFileContextManager:
    """
    Manages context across multiple test file generations.

    This manager:
    1. Tracks patterns that worked in previous files
    2. Tracks errors encountered and how they were fixed
    3. Provides cumulative context to LLM for each new file
    4. Learns from successes and failures
    """

    def __init__(self, project_dir: Path, pattern_cache: ProjectPatternCache):
        self.project_dir = project_dir
        self.pattern_cache = pattern_cache
        self.llm = get_llm()

        # Context memory (summarizes conversation to stay within token limits)
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=3000,  # Keep context manageable
            return_messages=True,
            memory_key="chat_history"
        )

        # Track generation contexts
        self.generation_history: List[GenerationContext] = []

        # Track discovered patterns during generation
        self.session_patterns: Dict[str, int] = {}

    def record_generation(
        self,
        class_info: ClassInfo,
        file_name: str,
        patterns_used: List[str],
        compilation_success: bool,
        errors: List[str] = None
    ):
        """
        Record a completed test generation.

        Args:
            class_info: Information about the generated class
            file_name: Name of generated test file
            patterns_used: List of patterns applied during generation
            compilation_success: Whether the generated test compiled successfully
            errors: List of compilation errors if any
        """
        context = GenerationContext(
            class_name=class_info.name,
            file_name=file_name,
            patterns_used=patterns_used,
            compilation_success=compilation_success,
            errors_encountered=errors or [],
            timestamp=datetime.now()
        )

        self.generation_history.append(context)

        # Update pattern usage counts
        for pattern in patterns_used:
            self.session_patterns[pattern] = self.session_patterns.get(pattern, 0) + 1

        # Add to conversation memory
        self._update_memory(context)

    def get_context_for_class(self, class_info: ClassInfo) -> str:
        """
        Get relevant context for generating a new test class.

        Args:
            class_info: Information about the class to generate tests for

        Returns:
            Formatted context string to include in generation prompt
        """
        context_parts = []

        # 1. Summary of previous generations
        if self.generation_history:
            success_count = sum(1 for ctx in self.generation_history if ctx.compilation_success)
            total_count = len(self.generation_history)

            context_parts.append(f"## Session Progress")
            context_parts.append(f"Generated {total_count} test(s) so far, {success_count} compiled successfully.")
            context_parts.append("")

        # 2. Common patterns discovered this session
        if self.session_patterns:
            context_parts.append("## Patterns That Worked This Session")
            sorted_patterns = sorted(self.session_patterns.items(), key=lambda x: x[1], reverse=True)
            for pattern, count in sorted_patterns[:5]:  # Top 5
                context_parts.append(f"- {pattern} (used {count}x)")
            context_parts.append("")

        # 3. Common errors to avoid
        error_categories = self._get_common_errors()
        if error_categories:
            context_parts.append("## Common Errors to Avoid")
            for error_type, count in error_categories[:3]:  # Top 3
                context_parts.append(f"- {error_type} (occurred {count}x)")
            context_parts.append("")

        # 4. Similar class patterns
        similar_contexts = self._get_similar_class_contexts(class_info)
        if similar_contexts:
            context_parts.append("## Similar Classes We've Generated")
            for ctx in similar_contexts[:2]:  # Top 2 most similar
                context_parts.append(f"- {ctx.class_name}:")
                if ctx.compilation_success:
                    context_parts.append(f"  ✓ Compiled successfully")
                    if ctx.patterns_used:
                        context_parts.append(f"  Used: {', '.join(ctx.patterns_used[:3])}")
                else:
                    context_parts.append(f"  ✗ Had {len(ctx.errors_encountered)} error(s)")
            context_parts.append("")

        # 5. Cached patterns
        if self.pattern_cache.patterns:
            context_parts.append("## Cached Patterns (High Priority)")
            for pattern in self.pattern_cache.patterns[:5]:  # Top 5
                context_parts.append(
                    f"- {pattern['pattern_type']}: {pattern['context']} → {pattern['value']}"
                )
            context_parts.append("")

        return "\n".join(context_parts) if context_parts else ""

    def get_memory_context(self) -> str:
        """Get summarized memory context from all previous generations"""
        try:
            # Get memory variables (includes summarized history)
            memory_vars = self.memory.load_memory_variables({})
            chat_history = memory_vars.get("chat_history", [])

            if not chat_history:
                return ""

            # Format chat history
            context = "## Conversation History (Summarized)\n\n"
            for msg in chat_history[-5:]:  # Last 5 messages
                if isinstance(msg, HumanMessage):
                    context += f"Task: {msg.content[:100]}...\n"
                elif isinstance(msg, AIMessage):
                    context += f"Result: {msg.content[:100]}...\n"

            return context

        except Exception as e:
            console.print(f"[yellow]Warning: Could not load memory context: {str(e)}[/yellow]")
            return ""

    def _update_memory(self, context: GenerationContext):
        """Update conversation memory with generation results"""
        # Human message: what we asked for
        human_msg = f"Generate test for {context.class_name}"

        # AI message: what we learned
        if context.compilation_success:
            ai_msg = f"Successfully generated {context.file_name}. "
            if context.patterns_used:
                ai_msg += f"Used patterns: {', '.join(context.patterns_used)}. "
            ai_msg += "Compiled without errors."
        else:
            ai_msg = f"Generated {context.file_name} with {len(context.errors_encountered)} error(s). "
            if context.errors_encountered:
                # Summarize errors
                error_types = set()
                for error in context.errors_encountered:
                    # Extract error type (e.g., CS0117 from "CS0117: Type not found")
                    if 'CS' in error:
                        error_type = error.split(':')[0].strip()
                        error_types.add(error_type)
                ai_msg += f"Error types: {', '.join(error_types)}. "

        self.memory.save_context(
            {"input": human_msg},
            {"output": ai_msg}
        )

    def _get_common_errors(self) -> List[tuple]:
        """Get most common error types across all generations"""
        error_counts = {}

        for context in self.generation_history:
            for error in context.errors_encountered:
                # Extract error category
                if 'CS' in error:
                    error_type = error.split(':')[0].strip()
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

    def _get_similar_class_contexts(self, class_info: ClassInfo) -> List[GenerationContext]:
        """
        Find contexts from similar classes.

        Similarity based on:
        - Same naming pattern (e.g., both end with "Controller")
        - Similar dependencies
        """
        similar = []

        for context in self.generation_history:
            similarity_score = 0

            # Check naming pattern
            if class_info.name.endswith("Controller") and context.class_name.endswith("Controller"):
                similarity_score += 2

            # Check if base classes match
            if class_info.base_classes:
                # Simple check if any base class name appears in context class name
                for base_class in class_info.base_classes:
                    if base_class.lower() in context.class_name.lower():
                        similarity_score += 1

            if similarity_score > 0:
                similar.append((similarity_score, context))

        # Sort by similarity score and return contexts
        similar.sort(key=lambda x: x[0], reverse=True)
        return [ctx for score, ctx in similar]

    def get_statistics(self) -> Dict[str, any]:
        """Get statistics about the generation session"""
        if not self.generation_history:
            return {
                "total_generated": 0,
                "compilation_success_rate": 0.0,
                "patterns_discovered": 0
            }

        success_count = sum(1 for ctx in self.generation_history if ctx.compilation_success)
        total_errors = sum(len(ctx.errors_encountered) for ctx in self.generation_history)

        return {
            "total_generated": len(self.generation_history),
            "successful_compilations": success_count,
            "failed_compilations": len(self.generation_history) - success_count,
            "compilation_success_rate": (success_count / len(self.generation_history)) * 100,
            "total_errors_encountered": total_errors,
            "average_errors_per_file": total_errors / len(self.generation_history) if self.generation_history else 0,
            "patterns_discovered": len(self.session_patterns),
            "most_used_patterns": sorted(
                self.session_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def save_session_report(self, output_path: Path):
        """Save a detailed session report"""
        stats = self.get_statistics()

        report = f"""# Test Generation Session Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Project**: {self.project_dir}

## Summary

- **Total Tests Generated**: {stats['total_generated']}
- **Successful Compilations**: {stats['successful_compilations']}
- **Failed Compilations**: {stats['failed_compilations']}
- **Success Rate**: {stats['compilation_success_rate']:.1f}%
- **Average Errors per File**: {stats['average_errors_per_file']:.1f}

## Patterns Discovered This Session

"""
        if self.session_patterns:
            for pattern, count in stats['most_used_patterns']:
                report += f"- {pattern}: used {count} time(s)\n"
        else:
            report += "No new patterns discovered.\n"

        report += "\n## Common Errors\n\n"
        error_categories = self._get_common_errors()
        if error_categories:
            for error_type, count in error_categories:
                report += f"- {error_type}: {count} occurrence(s)\n"
        else:
            report += "No errors encountered.\n"

        report += "\n## Generation History\n\n"
        for i, ctx in enumerate(self.generation_history, 1):
            status = "✓" if ctx.compilation_success else "✗"
            report += f"{i}. {status} {ctx.class_name} ({ctx.file_name})\n"
            if ctx.errors_encountered:
                report += f"   Errors: {len(ctx.errors_encountered)}\n"

        output_path.write_text(report)
        console.print(f"[green]✓ Session report saved to: {output_path}[/green]")


def main():
    """Test the context manager"""
    from generate_tests import ProjectPatternCache, ClassInfo

    project_dir = Path("/mnt/d/dev2/remotec/src/RemoteC.Api")
    pattern_cache = ProjectPatternCache(project_dir)

    manager = CrossFileContextManager(project_dir, pattern_cache)

    # Simulate some generations
    class1 = ClassInfo(
        name="DevicesController",
        namespace="RemoteC.Api.Controllers",
        file_path=Path("Controllers/DevicesController.cs"),
        source_code="",
        base_classes=["ControllerBase"],
        is_controller=True,
        is_service=False
    )

    manager.record_generation(
        class1,
        "DevicesControllerTests.cs",
        patterns_used=["DataPagedResult<DeviceDto>", "IDeviceRepository"],
        compilation_success=True
    )

    # Get context for next generation
    context = manager.get_context_for_class(class1)
    console.print("\n[bold]Context for next generation:[/bold]")
    console.print(context)

    # Get statistics
    stats = manager.get_statistics()
    console.print("\n[bold]Statistics:[/bold]")
    console.print(stats)


if __name__ == "__main__":
    main()
