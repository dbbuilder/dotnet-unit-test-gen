"""
Pattern Cache Module

Manages learned patterns for projects (extracted from generate_tests.py)
"""

import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class ProjectPattern:
    """A learned pattern for a specific project"""
    pattern_type: str  # 'return_type', 'enum_value', 'property_name', 'hint'
    context: str  # 'IDeviceRepository.GetUserDevicesAsync', 'ConnectionType', etc.
    value: str  # 'DataPagedResult<DeviceDto>', 'P2P,Relay,Direct', etc.
    confidence: float = 1.0  # How confident we are (based on frequency)
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())


class ProjectPatternCache:
    """
    Caches learned patterns for a specific project

    Patterns are stored in .test-gen-cache/{project_hash}/patterns.json
    The project hash is derived from the absolute path to ensure uniqueness.
    """

    def __init__(self, project_dir: Path, cache_root: Path = None):
        """
        Initialize pattern cache

        Args:
            project_dir: Project directory
            cache_root: Optional cache root directory (default: .test-gen-cache)
        """
        self.project_dir = project_dir

        # Create cache directory in tool location
        if cache_root is None:
            cache_root = Path(__file__).parent.parent / ".test-gen-cache"
        self.cache_root = cache_root
        self.cache_root.mkdir(exist_ok=True)

        # Hash project path for unique cache key
        project_hash = hashlib.md5(str(project_dir.absolute()).encode()).hexdigest()[:12]
        self.cache_dir = self.cache_root / project_hash
        self.cache_dir.mkdir(exist_ok=True)

        # Store project info
        self.info_file = self.cache_dir / "project-info.json"
        self.patterns_file = self.cache_dir / "patterns.json"

        self._save_project_info()
        self.patterns: List[ProjectPattern] = self._load_patterns()

    def _save_project_info(self):
        """Save project metadata"""
        info = {
            "project_path": str(self.project_dir.absolute()),
            "project_name": self.project_dir.name,
            "last_updated": datetime.now().isoformat()
        }
        self.info_file.write_text(json.dumps(info, indent=2))

    def _load_patterns(self) -> List[ProjectPattern]:
        """Load cached patterns"""
        if not self.patterns_file.exists():
            return []

        try:
            data = json.loads(self.patterns_file.read_text())
            return [ProjectPattern(**p) for p in data]
        except:
            return []

    def save_patterns(self):
        """Save patterns to cache"""
        data = [
            {
                "pattern_type": p.pattern_type,
                "context": p.context,
                "value": p.value,
                "confidence": p.confidence,
                "last_seen": p.last_seen
            }
            for p in self.patterns
        ]
        self.patterns_file.write_text(json.dumps(data, indent=2))

    def add_pattern(self, pattern_type: str, context: str, value: str):
        """
        Add or update a pattern

        Args:
            pattern_type: Type of pattern (return_type, enum_values, property_name, hint)
            context: Context where pattern applies
            value: Pattern value
        """
        # Check if pattern exists
        for p in self.patterns:
            if p.pattern_type == pattern_type and p.context == context:
                p.value = value
                p.last_seen = datetime.now().isoformat()
                p.confidence = min(1.0, p.confidence + 0.1)  # Increase confidence
                self.save_patterns()
                return

        # Add new pattern
        self.patterns.append(ProjectPattern(pattern_type, context, value))
        self.save_patterns()

    def get_context_string(self) -> str:
        """
        Get formatted string of all patterns for inclusion in prompts

        Returns:
            Formatted pattern context string
        """
        if not self.patterns:
            return ""

        # Group patterns by type
        grouped: Dict[str, List[ProjectPattern]] = {}
        for p in self.patterns:
            if p.pattern_type not in grouped:
                grouped[p.pattern_type] = []
            grouped[p.pattern_type].append(p)

        lines = ["\n\n**Project-Specific Patterns (IMPORTANT - use these!):**\n"]

        for pattern_type, patterns in grouped.items():
            type_label = pattern_type.replace('_', ' ').title()
            lines.append(f"\n**{type_label}:**")
            for p in patterns[:10]:  # Limit to 10 per type
                if p.pattern_type == 'hint':
                    lines.append(f"- {p.value}")
                else:
                    lines.append(f"- {p.context} → {p.value}")

        return '\n'.join(lines)

    def get_patterns_by_type(self, pattern_type: str) -> List[ProjectPattern]:
        """
        Get all patterns of a specific type

        Args:
            pattern_type: Type of pattern to retrieve

        Returns:
            List of matching patterns
        """
        return [p for p in self.patterns if p.pattern_type == pattern_type]

    def get_pattern_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get patterns as dictionary grouped by type

        Returns:
            Dict with pattern types as keys and pattern lists as values
        """
        result: Dict[str, List[Dict[str, Any]]] = {}

        for p in self.patterns:
            if p.pattern_type not in result:
                result[p.pattern_type] = []

            result[p.pattern_type].append({
                "context": p.context,
                "value": p.value,
                "confidence": p.confidence
            })

        return result

    def clear(self):
        """Clear all patterns"""
        self.patterns = []
        self.save_patterns()

    def count(self) -> int:
        """Get total number of patterns"""
        return len(self.patterns)

    def get_cache_path(self) -> Path:
        """Get path to cache directory"""
        return self.cache_dir

    def __repr__(self) -> str:
        """String representation"""
        return f"ProjectPatternCache(project={self.project_dir.name}, patterns={len(self.patterns)})"
