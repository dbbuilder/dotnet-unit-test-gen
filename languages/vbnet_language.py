"""
VB.NET Language Handler

Provides VB.NET-specific parsing and test generation capabilities
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base_language import (
    BaseLanguageHandler,
    ClassInfo,
    MethodInfo
)


class VBNetLanguageHandler(BaseLanguageHandler):
    """
    VB.NET language handler

    Supports:
    - VB.NET syntax parsing
    - Automatic attribute parentheses fixes (<Fact> → <Fact()>)
    - VB.NET-specific patterns (Sub, Function, Nothing, AndAlso, OrElse)
    - Mixed C#/VB.NET projects
    """

    def get_file_extensions(self) -> List[str]:
        """Return VB.NET file extensions"""
        return ['.vb']

    def get_test_file_extension(self) -> str:
        """Return test file extension"""
        return '.vb'

    def get_test_framework_default(self) -> str:
        """Return default test framework"""
        return 'xunit'

    def detect_files(self, project_dir: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Find all VB.NET source files in project

        Args:
            project_dir: Project directory to search
            pattern: Optional regex pattern to filter class names

        Returns:
            List of VB.NET source file paths
        """
        vb_files = []

        # Find all .vb files
        for vb_file in project_dir.rglob('*.vb'):
            # Skip test files, bin, obj directories
            if any(exclude in str(vb_file) for exclude in ['bin', 'obj', 'Test', '.Test']):
                continue

            # If pattern specified, check if file matches
            if pattern:
                content = vb_file.read_text(encoding='utf-8', errors='ignore')
                # Extract class name
                class_match = re.search(r'Public Class\s+(\w+)', content, re.IGNORECASE)
                if class_match and not re.search(pattern, class_match.group(1)):
                    continue

            vb_files.append(vb_file)

        return sorted(vb_files, key=lambda p: p.name)

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse VB.NET class from source file

        Args:
            file_path: Path to VB.NET source file

        Returns:
            ClassInfo object or None if parsing fails
        """
        try:
            source_code = file_path.read_text(encoding='utf-8', errors='ignore')

            # Extract namespace
            namespace_match = re.search(r'Namespace\s+([\w.]+)', source_code, re.IGNORECASE)
            namespace = namespace_match.group(1) if namespace_match else 'Tests'

            # Extract class name
            class_match = re.search(r'Public Class\s+(\w+)', source_code, re.IGNORECASE)
            if not class_match:
                return None

            class_name = class_match.group(1)

            # Extract methods
            methods = self._extract_methods(source_code)

            # Extract dependencies (constructor parameters)
            dependencies = self._extract_dependencies(source_code)

            # Determine if this is a controller
            is_controller = 'Controller' in class_name or 'Inherits.*Controller' in source_code

            return ClassInfo(
                name=class_name,
                namespace=namespace,
                file_path=file_path,
                source_code=source_code,
                methods=methods,
                dependencies=dependencies,
                is_controller=is_controller,
                language='vbnet'
            )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _extract_methods(self, source_code: str) -> List[MethodInfo]:
        """Extract public methods from VB.NET source code"""
        methods = []

        # Match VB.NET function declarations
        # Public Function GetUser(id As Integer) As Task(Of ActionResult)
        function_pattern = r'Public\s+(Async\s+)?(Function|Sub)\s+(\w+)\s*\(([^)]*)\)\s*(?:As\s+([^\n]+))?'

        for match in re.finditer(function_pattern, source_code, re.IGNORECASE):
            is_async = match.group(1) is not None
            method_type = match.group(2).lower()
            method_name = match.group(3)
            params_str = match.group(4)
            return_type = match.group(5).strip() if match.group(5) else 'void'

            # Skip constructors
            if method_name == 'New':
                continue

            # Parse parameters
            parameters = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    # VB.NET parameter: name As Type
                    param_match = re.match(r'(\w+)\s+As\s+([^\s,]+)', param, re.IGNORECASE)
                    if param_match:
                        parameters.append({
                            'name': param_match.group(1),
                            'type': param_match.group(2)
                        })

            methods.append(MethodInfo(
                name=method_name,
                return_type=return_type,
                parameters=parameters,
                is_async=is_async,
                is_public=True
            ))

        return methods

    def _extract_dependencies(self, source_code: str) -> List[str]:
        """Extract constructor dependencies from VB.NET code"""
        dependencies = []

        # Find constructor: Public Sub New(logger As ILogger, service As IUserService)
        constructor_pattern = r'Public\s+Sub\s+New\s*\(([^)]+)\)'
        constructor_match = re.search(constructor_pattern, source_code, re.IGNORECASE)

        if constructor_match:
            params_str = constructor_match.group(1)
            for param in params_str.split(','):
                param = param.strip()
                # Extract type: name As Type
                param_match = re.match(r'\w+\s+As\s+([^\s,]+)', param, re.IGNORECASE)
                if param_match:
                    dep_type = param_match.group(1)
                    # Only include interfaces and known service types
                    if dep_type.startswith('I') or 'Service' in dep_type or 'Repository' in dep_type:
                        dependencies.append(dep_type)

        return dependencies

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        test_framework: str = 'xunit',
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI prompt for VB.NET test generation

        Args:
            class_info: Parsed class information
            patterns: Learned patterns from pattern cache
            test_framework: Test framework to use (xunit, nunit, mstest)
            context: Additional context (DTOs, enums, etc.)

        Returns:
            Formatted prompt string
        """
        # Build context sections
        dto_context = ""
        if context and context.get('dtos'):
            dto_context = "\n\n**Available DTOs:**\n" + "\n".join(
                f"- {dto}" for dto in context['dtos'][:10]
            )

        enum_context = ""
        if context and context.get('enums'):
            enum_context = "\n\n**Available Enums:**\n" + "\n".join(
                f"- {enum}" for enum in context['enums'][:10]
            )

        pattern_context = ""
        if patterns:
            pattern_list = []
            for pattern_type, pattern_items in patterns.items():
                if pattern_items:
                    pattern_list.append(f"\n**{pattern_type}:**")
                    for item in list(pattern_items)[:5]:
                        pattern_list.append(f"- {item.get('context', '')}: {item.get('value', '')}")
            if pattern_list:
                pattern_context = "\n\n**Learned Patterns:**" + "\n".join(pattern_list)

        # Framework-specific instructions
        framework_imports = self._get_framework_imports(test_framework)
        framework_attributes = self._get_framework_attributes(test_framework)

        prompt = f"""Generate comprehensive VB.NET xUnit unit tests for the following class.

**CRITICAL VB.NET SYNTAX REQUIREMENTS:**
1. Use VB.NET syntax exclusively (NO C# syntax)
2. ALL attributes MUST have parentheses: <Fact()>, <Theory()>, <InlineData()>
3. Use "Nothing" instead of "null"
4. Use "AndAlso" instead of "&&"
5. Use "OrElse" instead of "||"
6. Use "As" for type declarations
7. Use "Sub" for void methods, "Function" for returning methods
8. Use "End Sub" and "End Function" to close methods
9. Use "Inherits" instead of ":"
10. Use proper VB.NET string concatenation with "&"

**Source Class:**
```vbnet
{class_info.source_code}
```

**Class Details:**
- Name: {class_info.name}
- Namespace: {class_info.namespace}
- Methods: {len(class_info.methods)}
- Dependencies: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}
{dto_context}
{enum_context}
{pattern_context}

**Test Framework:** {test_framework}

**Required Imports:**
```vbnet
{framework_imports}
```

**Test Requirements:**
1. Generate a test class named `{class_info.name}Tests`
2. Use proper VB.NET test syntax with {test_framework}
3. Create comprehensive tests for ALL public methods
4. Mock all dependencies using Moq
5. Use FluentAssertions for assertions (.Should())
6. Follow Arrange-Act-Assert pattern
7. Include edge cases and error handling tests
8. Use proper async/await for async methods

**VB.NET Test Attributes ({test_framework}):**
{framework_attributes}

**Example VB.NET Test Structure:**
```vbnet
Imports Xunit
Imports Moq
Imports FluentAssertions
Imports System.Threading.Tasks

Namespace {class_info.namespace}.Tests
    Public Class {class_info.name}Tests
        Private ReadOnly _mockService As Mock(Of IService)
        Private ReadOnly _controller As {class_info.name}

        Public Sub New()
            _mockService = New Mock(Of IService)()
            _controller = New {class_info.name}(_mockService.Object)
        End Sub

        <Fact()>
        Public Async Function MethodName_Scenario_ExpectedResult() As Task
            ' Arrange
            Dim expectedData = New DataResult()
            _mockService.Setup(Function(x) x.GetDataAsync()).ReturnsAsync(expectedData)

            ' Act
            Dim result = Await _controller.MethodName()

            ' Assert
            result.Should().NotBeNull()
            result.Should().BeOfType(Of OkObjectResult)()
        End Function
    End Class
End Namespace
```

**IMPORTANT:**
- Use VB.NET syntax ONLY
- ALL attributes must have empty parentheses: <Fact()>, not <Fact>
- Use "Nothing" not "null"
- Use "AndAlso" not "&&"
- Use "Function" with "As Task" for async methods
- Properly close all blocks with "End Sub", "End Function", "End Namespace", "End Class"

Generate the complete test file now:"""

        return prompt

    def _get_framework_imports(self, framework: str) -> str:
        """Get framework-specific import statements"""
        base_imports = """Imports Moq
Imports FluentAssertions
Imports System
Imports System.Threading.Tasks"""

        if framework == 'xunit':
            return f"{base_imports}\nImports Xunit"
        elif framework == 'nunit':
            return f"{base_imports}\nImports NUnit.Framework"
        elif framework == 'mstest':
            return f"{base_imports}\nImports Microsoft.VisualStudio.TestTools.UnitTesting"
        else:
            return base_imports

    def _get_framework_attributes(self, framework: str) -> str:
        """Get framework-specific attribute examples"""
        if framework == 'xunit':
            return """- <Fact()> - Simple test
- <Theory()> - Parameterized test
- <InlineData()> - Test data"""
        elif framework == 'nunit':
            return """- <Test()> - Simple test
- <TestCase()> - Parameterized test
- <SetUp()> - Setup method
- <TearDown()> - Cleanup method"""
        elif framework == 'mstest':
            return """- <TestMethod()> - Simple test
- <DataRow()> - Test data
- <TestInitialize()> - Setup method
- <TestCleanup()> - Cleanup method"""
        else:
            return ""

    def auto_fix_syntax(self, test_code: str, class_info: ClassInfo) -> str:
        """
        Auto-fix common VB.NET test syntax issues

        Args:
            test_code: Generated test code
            class_info: Original class info

        Returns:
            Fixed test code
        """
        fixed_code = test_code

        # Fix 1: Add parentheses to attributes
        # <Fact> → <Fact()>
        fixed_code = re.sub(r'<(Fact|Theory|Test|TestMethod|InlineData|TestCase|DataRow)>',
                           r'<\1()>', fixed_code)

        # Fix 2: Replace null with Nothing
        fixed_code = re.sub(r'\bnull\b', 'Nothing', fixed_code)

        # Fix 3: Replace && with AndAlso
        fixed_code = re.sub(r'&&', 'AndAlso', fixed_code)

        # Fix 4: Replace || with OrElse
        fixed_code = re.sub(r'\|\|', 'OrElse', fixed_code)

        # Fix 5: Ensure proper namespace closing
        if 'Namespace ' in fixed_code and 'End Namespace' not in fixed_code:
            fixed_code += '\nEnd Namespace\n'

        # Fix 6: Warn about C# syntax leakage
        csharp_patterns = [
            (r'\{', 'Opening brace { (use proper VB.NET block syntax)'),
            (r'\}', 'Closing brace } (use End Sub/End Function)'),
            (r';$', 'Semicolon at end of line (VB.NET does not use semicolons)'),
        ]

        for pattern, warning in csharp_patterns:
            if re.search(pattern, fixed_code, re.MULTILINE):
                print(f"  ⚠ Warning: Detected {warning}")

        return fixed_code

    def get_test_class_name(self, class_name: str) -> str:
        """Generate test class name"""
        return f"{class_name}Tests"

    def get_test_namespace(self, namespace: str) -> str:
        """Generate test namespace"""
        return f"{namespace}.Tests"
