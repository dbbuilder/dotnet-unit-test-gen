#!/usr/bin/env python3
"""
Helper script to manually add patterns to project cache
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from generate_tests import ProjectPatternCache
from rich.console import Console

console = Console()

def main():
    if len(sys.argv) < 5:
        console.print("[yellow]Usage: python add_pattern.py PROJECT_DIR PATTERN_TYPE CONTEXT VALUE[/yellow]")
        console.print("\nExamples:")
        console.print("  python add_pattern.py /path/to/RemoteC.Api return_type 'IDeviceRepository.GetUserDevicesAsync' 'DataPagedResult<DeviceDto>'")
        console.print("  python add_pattern.py /path/to/RemoteC.Api enum_values 'ConnectionType' 'P2P,Relay,Direct'")
        console.print("  python add_pattern.py /path/to/RemoteC.Api property_mapping 'SessionStatsDto.TotalSessions' 'TodaysSessions'")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    pattern_type = sys.argv[2]
    context = sys.argv[3]
    value = sys.argv[4]

    if not project_dir.exists():
        console.print(f"[red]Error: Project directory not found: {project_dir}[/red]")
        sys.exit(1)

    # Load/create pattern cache
    cache = ProjectPatternCache(project_dir)

    # Add pattern
    cache.add_pattern(pattern_type, context, value)

    console.print(f"[green]✓ Added pattern to cache:[/green]")
    console.print(f"  Type: {pattern_type}")
    console.print(f"  Context: {context}")
    console.print(f"  Value: {value}")
    console.print(f"\nCache location: {cache.cache_dir}")
    console.print(f"Total patterns: {len(cache.patterns)}")

if __name__ == "__main__":
    main()
