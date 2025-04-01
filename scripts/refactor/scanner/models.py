"""
Data models for the Dream.OS Intelligence Scanner.
Provides structured representations of code analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

@dataclass
class ImportInfo:
    """Information about module imports."""
    module_name: str
    imported_names: List[str]
    is_relative: bool
    level: int = 0
    resolved_path: Optional[str] = None

@dataclass
class FunctionInfo:
    """Detailed information about function definitions."""
    name: str
    args: List[str]
    returns: Optional[str]
    is_async: bool
    decorators: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int
    complexity: int = 0
    has_test: bool = False
    test_functions: List[str] = field(default_factory=list)

@dataclass
class ClassInfo:
    """Detailed information about class definitions."""
    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    decorators: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int
    maturity_level: str = "Unknown"
    agent_type: Optional[str] = None
    complexity: int = 0
    has_test: bool = False
    test_classes: List[str] = field(default_factory=list)

@dataclass
class FileAnalysis:
    """Complete analysis of a source file."""
    path: str
    type: str  # service, test, utility, agent, interface, etc.
    imports: List[ImportInfo]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    dependencies: List[str]
    has_tests: bool
    last_modified: str
    lines: int
    docstring: Optional[str]
    test_files: List[str]
    complexity: int = 0
    is_test: bool = False
    implements: Optional[str] = None  # For test files, points to implementation
    implemented_by: List[str] = field(default_factory=list)  # For source files, points to tests

@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    path: str
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    is_circular: bool = False
    cycle_path: Optional[List[str]] = None

@dataclass
class ProjectMetrics:
    """Project-wide metrics and statistics."""
    total_files: int = 0
    total_lines: int = 0
    total_classes: int = 0
    total_functions: int = 0
    files_with_tests: int = 0
    test_coverage: float = 0.0
    avg_complexity: float = 0.0
    circular_dependencies: List[List[str]] = field(default_factory=list)
    high_complexity_files: List[str] = field(default_factory=list)
    missing_tests_files: List[str] = field(default_factory=list)
    agent_type_counts: Dict[str, int] = field(default_factory=dict)
    maturity_level_counts: Dict[str, int] = field(default_factory=dict)

@dataclass
class ScannerCache:
    """Cache for incremental scanning."""
    last_scan: datetime
    file_hashes: Dict[str, str]
    moved_files: Dict[str, str]  # old_path -> new_path
    analysis_cache: Dict[str, FileAnalysis]

@dataclass
class ProjectContext:
    """Complete project context for LLM interactions."""
    project_root: Path
    analysis: Dict[str, FileAnalysis]
    metrics: ProjectMetrics
    dependency_graph: Dict[str, DependencyNode]
    high_value_targets: List[str]  # Files that need attention
    agent_hierarchy: Dict[str, List[str]]  # Agent type -> implementing files 