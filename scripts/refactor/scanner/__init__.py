"""
Dream.OS Intelligence Scanner Package.

A comprehensive code analysis and optimization tool for Dream.OS.
"""

from .core.scanner import IntelligenceScanner
from .core.deep_ast import DeepASTAnalyzer
from .core.test_mapper import TestMapper
from .core.agent_map import AgentMapper
from .core.dependency_map import DependencyMapper
from .models import (
    FileAnalysis,
    ProjectMetrics,
    ImportInfo,
    FunctionInfo,
    ClassInfo,
    TestMapping,
    AgentProfile
)

__version__ = "0.1.0"
__author__ = "Dream.OS Team"

__all__ = [
    # Core components
    "IntelligenceScanner",
    "DeepASTAnalyzer",
    "TestMapper",
    "AgentMapper",
    "DependencyMapper",
    
    # Models
    "FileAnalysis",
    "ProjectMetrics",
    "ImportInfo",
    "FunctionInfo",
    "ClassInfo",
    "TestMapping",
    "AgentProfile"
] 