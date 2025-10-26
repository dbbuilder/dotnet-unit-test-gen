"""
C# Language Handler

Provides C# source code parsing, test generation prompts, and auto-fixing
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base_language import (
    BaseLanguageHandler,
    ClassInfo,
    MethodInfo,
    ParseError
)


class CSharpLanguageHandler(BaseLanguageHandler):
    """
    C# language handler for .NET projects

    Supports:
    - C# source file parsing (classes, methods, dependencies)
    - xUnit test generation prompts
    - DTO and enum discovery
    - Auto-fixing common test errors
    """

    # Regex patterns for C# parsing
    NAMESPACE_PATTERN = r'namespace\s+([\w\.]+)'
    CLASS_PATTERN = r'public\s+(?:sealed\s+)?(?:partial\s+)?(?:abstract\s+)?class\s+(\w+)'
    METHOD_PATTERN = r'public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:Task<?[\w<>]*>?|IActionResult|ActionResult<[\w<>]+>|void|[\w<>]+)\s+(\w+)\s*\('
    DEPENDENCY_PATTERN = r'private\s+readonly\s+(I\w+)\s+_'
    DTO_PATTERN = r'\b(\w+Dto)\b'
    ENUM_PATTERN = r'\b(\w+(?:Type|Status|Mode|State|Level|Kind))\b'

    def __init__(self, test_framework: str = "xunit"):
        """
        Initialize C# language handler

        Args:
            test_framework: Test framework to use (default: xunit)
        """
        super().__init__()
        self.test_framework = test_framework
        self.dto_cache: Dict[str, str] = {}

    def get_language_name(self) -> str:
        """Return language display name"""
        return "C#"

    def get_file_extensions(self) -> List[str]:
        """Return supported file extensions"""
        return ['.cs', '.csx']

    def get_test_framework(self) -> str:
        """Return test framework name"""
        return self.test_framework

    def detect_files(self, path: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Find all C# source files in directory

        Args:
            path: Root directory to search
            pattern: Optional regex pattern to filter classes (e.g., '.*Controller$')

        Returns:
            List of C# source files
        """
        cs_files = []

        for cs_file in path.rglob("*.cs"):
            # Skip test files, bin, obj, migrations
            if any(x in str(cs_file) for x in ["/bin/", "/obj/", "Test.cs", "Tests.cs", "/Migrations/"]):
                continue

            # If pattern specified, check if class name matches
            if pattern:
                class_info = self.parse_class(cs_file)
                if class_info and re.search(pattern, class_info.name):
                    cs_files.append(cs_file)
            else:
                cs_files.append(cs_file)

        return cs_files

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse C# file and extract class information

        Args:
            file_path: Path to C# source file

        Returns:
            ClassInfo object or None if parsing fails
        """
        try:
            source = file_path.read_text(encoding='utf-8')

            # Extract namespace
            namespace_match = re.search(self.NAMESPACE_PATTERN, source)
            namespace = namespace_match.group(1) if namespace_match else "Unknown"

            # Extract class name (public classes only)
            class_match = re.search(self.CLASS_PATTERN, source)
            if not class_match:
                return None

            class_name = class_match.group(1)

            # Extract public methods
            method_matches = re.findall(self.METHOD_PATTERN, source)
            methods = [
                MethodInfo(
                    name=method_name,
                    return_type="unknown",  # Could enhance parsing to extract return type
                    parameters=[],  # Could enhance parsing to extract parameters
                    is_async="async" in source,  # Simple heuristic
                    is_public=True
                )
                for method_name in method_matches
            ]

            # Extract dependencies (constructor injection)
            dependency_matches = re.findall(self.DEPENDENCY_PATTERN, source)
            dependencies = dependency_matches

            # Determine class type
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
                is_service=is_service,
                metadata={}
            )

        except Exception as e:
            raise ParseError(f"Error parsing {file_path}: {e}")

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        existing_tests: Optional[str] = None
    ) -> str:
        """
        Generate AI prompt for test generation

        Args:
            class_info: Parsed class information
            patterns: Learned patterns for this project
            existing_tests: Optional existing tests for reference

        Returns:
            Formatted prompt string
        """
        # Truncate source if too large
        max_source_len = 8000
        source = class_info.source_code
        if len(source) > max_source_len:
            source = source[:max_source_len] + "\n// ... (truncated)"

        # Find related DTOs and Enums
        dto_context = self._find_related_dtos(class_info)
        enum_context = self._find_related_enums(class_info)

        # Format patterns
        pattern_context = self._format_patterns(patterns) if patterns else ""

        # Build prompt
        prompt = f"""You are an expert .NET test engineer. Generate comprehensive unit tests for the following C# class.

**Class to Test:**
```csharp
{source}
```
{dto_context}{enum_context}{pattern_context}
**Requirements:**
1. Use {self.test_framework.upper()} testing framework
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

    def get_test_file_path(self, source_path: Path, output_dir: Path) -> Path:
        """
        Determine output path for test file

        Args:
            source_path: Path to source file
            output_dir: Base output directory for tests

        Returns:
            Path where test file should be written
        """
        # Get class name from source
        class_info = self.parse_class(source_path)
        if not class_info:
            # Fallback: use filename
            test_filename = source_path.stem + "Tests.cs"
        else:
            test_filename = class_info.name + "Tests.cs"

        # Create subdirectory structure matching source
        # e.g., Controllers/SessionsController.cs -> Controllers/SessionsControllerTests.cs
        relative_path = source_path.parent.name
        if relative_path and relative_path not in [".", source_path.parent.parent.name]:
            test_dir = output_dir / relative_path
            test_dir.mkdir(parents=True, exist_ok=True)
            return test_dir / test_filename
        else:
            return output_dir / test_filename

    def auto_fix_syntax(self, code: str) -> tuple[str, List[str], List[str]]:
        """
        Auto-fix common C# test syntax issues

        Args:
            code: Generated test code

        Returns:
            Tuple of (fixed_code, warnings, errors)
        """
        fixes_applied = []
        warnings = []

        # 1. Add missing using statements
        missing_usings = []

        if 'IWebHostEnvironment' in code and 'using Microsoft.AspNetCore.Hosting;' not in code:
            missing_usings.append('using Microsoft.AspNetCore.Hosting;')
            fixes_applied.append("Added missing using: Microsoft.AspNetCore.Hosting")

        if 'ILogger' in code and 'using Microsoft.Extensions.Logging;' not in code:
            missing_usings.append('using Microsoft.Extensions.Logging;')
            fixes_applied.append("Added missing using: Microsoft.Extensions.Logging")

        if 'IConfiguration' in code and 'using Microsoft.Extensions.Configuration;' not in code:
            missing_usings.append('using Microsoft.Extensions.Configuration;')
            fixes_applied.append("Added missing using: Microsoft.Extensions.Configuration")

        # Insert missing usings after existing usings
        if missing_usings:
            # Find the last using statement
            using_pattern = r'(using\s+[\w\.]+;)'
            matches = list(re.finditer(using_pattern, code))
            if matches:
                last_using = matches[-1]
                insert_pos = last_using.end()
                code = code[:insert_pos] + '\n' + '\n'.join(missing_usings) + code[insert_pos:]

        # 2. Detect warnings (don't auto-fix, just warn)
        if 'PagedResult' in code and 'DataPagedResult' not in code:
            warnings.append("⚠️  PagedResult might need to be DataPagedResult")

        return code, fixes_applied, warnings

    def _find_related_dtos(self, class_info: ClassInfo) -> str:
        """Find DTOs referenced in the class"""
        # Extract DTO type names from source code
        dto_names = set(re.findall(self.DTO_PATTERN, class_info.source_code))

        if not dto_names:
            return ""

        dto_definitions = []

        # Search for DTO files in common locations
        project_dir = class_info.file_path.parent
        search_paths = [
            project_dir.parent / "Shared" / "Models",
            project_dir / "Models",
            project_dir / "DTOs",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for cs_file in search_path.rglob("*.cs"):
                # Use cache
                if cs_file.name in self.dto_cache:
                    content = self.dto_cache[cs_file.name]
                else:
                    try:
                        content = cs_file.read_text(encoding='utf-8', errors='ignore')
                        self.dto_cache[cs_file.name] = content
                    except:
                        continue

                # Extract matching DTO class definitions
                for dto_name in dto_names:
                    pattern = rf'public\s+class\s+{dto_name}\s*{{[^}}]*(?:{{[^}}]*}}[^}}]*)*}}'
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        dto_def = matches[0]
                        if len(dto_def) < 1000:  # Limit size
                            dto_definitions.append(f"// {dto_name} definition\n{dto_def}")

        if dto_definitions:
            return "\n\n**Related DTOs:**\n```csharp\n" + "\n\n".join(dto_definitions[:5]) + "\n```\n"

        return ""

    def _find_related_enums(self, class_info: ClassInfo) -> str:
        """Find enums referenced in the class"""
        # Extract enum type names from source code
        enum_names = set(re.findall(self.ENUM_PATTERN, class_info.source_code))

        if not enum_names:
            return ""

        enum_definitions = []

        # Search for enum files in common locations
        project_dir = class_info.file_path.parent
        search_paths = [
            project_dir.parent / "Shared" / "Models",
            project_dir.parent / "Shared" / "Enums",
            project_dir / "Models",
            project_dir / "Enums",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for cs_file in search_path.rglob("*.cs"):
                # Use cache
                if cs_file.name in self.dto_cache:
                    content = self.dto_cache[cs_file.name]
                else:
                    try:
                        content = cs_file.read_text(encoding='utf-8', errors='ignore')
                        self.dto_cache[cs_file.name] = content
                    except:
                        continue

                # Extract matching enum definitions
                for enum_name in enum_names:
                    pattern = rf'public\s+enum\s+{enum_name}\s*{{[^}}]*}}'
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        enum_def = matches[0]
                        # Clean up whitespace
                        enum_def = re.sub(r'\s+', ' ', enum_def)
                        enum_def = re.sub(r'\s*{\s*', ' { ', enum_def)
                        enum_def = re.sub(r'\s*}\s*', ' }', enum_def)
                        if len(enum_def) < 500:
                            enum_definitions.append(f"// {enum_name} definition\n{enum_def}")

        if enum_definitions:
            return "\n\n**Related Enums:**\n```csharp\n" + "\n\n".join(enum_definitions[:5]) + "\n```\n"

        return ""

    def _format_patterns(self, patterns: Dict[str, Any]) -> str:
        """Format patterns for inclusion in prompt"""
        if not patterns:
            return ""

        pattern_lines = []

        # Format each pattern type
        for pattern_type, pattern_list in patterns.items():
            if pattern_list:
                pattern_lines.append(f"\n**{pattern_type.replace('_', ' ').title()}:**")
                for pattern in pattern_list[:10]:  # Limit to 10 per type
                    if isinstance(pattern, dict):
                        context = pattern.get('context', '')
                        value = pattern.get('value', '')
                        pattern_lines.append(f"- {context} → {value}")
                    else:
                        pattern_lines.append(f"- {pattern}")

        if pattern_lines:
            return "\n\n**Project-Specific Patterns (use these!):**" + '\n'.join(pattern_lines) + "\n"

        return ""

    def extract_code_from_response(self, response: str) -> str:
        """
        Extract C# code from AI response (may contain markdown)

        Args:
            response: AI response text

        Returns:
            Extracted C# code
        """
        # Try to find ```csharp blocks
        pattern = r'```(?:csharp|cs|c#)?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # If no code blocks, return as-is
        return response.strip()
