"""
Base Language Handler Interface

Abstract base class for language-specific handlers (C#, VB.NET, Java, Python, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class MethodInfo:
    """Information about a method/function"""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]  # [{"name": "id", "type": "int"}, ...]
    is_async: bool = False
    is_public: bool = True
    decorators: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Language-agnostic class/component information"""
    name: str
    namespace: str
    file_path: Path
    source_code: str
    methods: List[MethodInfo]
    dependencies: List[str]  # Constructor dependencies
    base_class: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    is_controller: bool = False
    is_service: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)  # Language-specific metadata


@dataclass
class TestFileInfo:
    """Information about generated test file"""
    source_file: Path
    test_file: Path
    class_name: str
    test_class_name: str
    test_framework: str


class BaseLanguageHandler(ABC):
    """
    Abstract base class for language handlers

    Implementations must provide:
    - File detection and filtering
    - Source code parsing
    - Test prompt generation
    - Test file naming
    - Syntax auto-fixing (optional)
    """

    def __init__(self):
        """Initialize language handler"""
        pass

    @abstractmethod
    def get_language_name(self) -> str:
        """
        Return language display name

        Returns:
            Language name (e.g., 'C#', 'VB.NET', 'Java')
        """
        pass

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """
        Return supported file extensions

        Returns:
            List of extensions (e.g., ['.cs', '.csx'])
        """
        pass

    @abstractmethod
    def get_test_framework(self) -> str:
        """
        Return default test framework name

        Returns:
            Framework name (e.g., 'xunit', 'jest', 'junit', 'pytest')
        """
        pass

    @abstractmethod
    def detect_files(self, path: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Find all testable files in directory

        Args:
            path: Root directory to search
            pattern: Optional regex pattern to filter files (e.g., '.*Controller$')

        Returns:
            List of source files to generate tests for
        """
        pass

    @abstractmethod
    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse source file and extract class information

        Args:
            file_path: Path to source file

        Returns:
            ClassInfo object or None if parsing fails
        """
        pass

    @abstractmethod
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
            Formatted prompt string for AI completion
        """
        pass

    @abstractmethod
    def get_test_file_path(self, source_path: Path, output_dir: Path) -> Path:
        """
        Determine output path for test file

        Args:
            source_path: Path to source file
            output_dir: Base output directory for tests

        Returns:
            Path where test file should be written
        """
        pass

    def has_existing_tests(self, source_path: Path, output_dir: Path) -> bool:
        """
        Check if tests already exist for source file

        Args:
            source_path: Path to source file
            output_dir: Test output directory

        Returns:
            True if test file exists
        """
        test_path = self.get_test_file_path(source_path, output_dir)
        return test_path.exists()

    def auto_fix_syntax(self, code: str) -> tuple[str, List[str], List[str]]:
        """
        Auto-fix common syntax issues (optional)

        Default implementation returns code unchanged.
        Override in subclass for language-specific fixes.

        Args:
            code: Generated test code

        Returns:
            Tuple of (fixed_code, warnings, errors)
        """
        return code, [], []

    def get_import_statements(self, patterns: Dict[str, Any]) -> List[str]:
        """
        Get language-specific import statements

        Can be overridden to include pattern-based imports.

        Args:
            patterns: Learned patterns for this project

        Returns:
            List of import statements
        """
        return []

    def is_complex_class(self, class_info: ClassInfo) -> bool:
        """
        Determine if class is complex (affects model selection)

        Default heuristic:
        - >3 methods OR
        - >2 dependencies

        Args:
            class_info: Parsed class information

        Returns:
            True if class is considered complex
        """
        return len(class_info.methods) > 3 or len(class_info.dependencies) > 2

    def get_test_class_name(self, class_name: str) -> str:
        """
        Generate test class name from source class name

        Default: Append 'Tests' suffix

        Args:
            class_name: Source class name

        Returns:
            Test class name
        """
        return f"{class_name}Tests"


class LanguageError(Exception):
    """Base exception for language handler errors"""
    pass


class ParseError(LanguageError):
    """Error parsing source file"""
    pass


class UnsupportedLanguageError(LanguageError):
    """Language not supported"""
    pass
