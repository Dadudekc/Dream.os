"""
Test Mapping System for Dream.OS Intelligence Scanner.

Maps test files to their implementations and provides:
- Test coverage analysis
- Missing test detection
- Test-to-implementation tracing
- Test quality metrics
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ..models import FileAnalysis, ProjectMetrics

logger = logging.getLogger(__name__)

@dataclass
class TestMapping:
    """Mapping between test and implementation."""
    test_file: str
    impl_file: str
    test_functions: List[str]
    test_classes: List[str]
    coverage_score: float = 0.0

class TestMapper:
    """
    Maps relationships between test files and their implementations.
    Analyzes test coverage and suggests missing tests.
    """

    def __init__(self):
        self.test_map: Dict[str, TestMapping] = {}
        self.metrics = ProjectMetrics()
        self.test_patterns = [
            (r'^test_(.+)\.py$', r'\1.py'),  # test_foo.py -> foo.py
            (r'(.+)_test\.py$', r'\1.py'),   # foo_test.py -> foo.py
            (r'tests/(.+)/test_(.+)\.py$', r'\1/\2.py')  # tests/core/test_foo.py -> core/foo.py
        ]

    def map_tests(self, analysis_map: Dict[str, FileAnalysis]) -> Dict[str, TestMapping]:
        """
        Build complete test mapping for the project.
        
        Args:
            analysis_map: Dict mapping file paths to their analysis
        
        Returns:
            Dict mapping implementation files to their TestMapping
        """
        logger.info("Mapping test files to implementations...")
        
        # First pass: identify test files and their potential implementations
        test_files = {
            path: analysis for path, analysis in analysis_map.items()
            if analysis.type == 'test' or 'test' in path.lower()
        }
        
        # Second pass: map tests to implementations
        for test_path, test_analysis in test_files.items():
            impl_path = self._find_implementation(test_path, analysis_map)
            if impl_path and impl_path in analysis_map:
                # Create or update test mapping
                mapping = self._create_test_mapping(
                    test_path, impl_path,
                    test_analysis, analysis_map[impl_path]
                )
                self.test_map[impl_path] = mapping
                
                # Update file analysis objects
                analysis_map[impl_path].has_tests = True
                analysis_map[impl_path].test_files.append(test_path)
                test_analysis.is_test = True
                test_analysis.implements = impl_path
        
        # Update project metrics
        self._update_metrics(analysis_map)
        
        return self.test_map

    def _find_implementation(self, test_path: str, analysis_map: Dict[str, FileAnalysis]) -> Optional[str]:
        """Find the implementation file for a test file."""
        test_path = test_path.replace('\\', '/')  # Normalize path separators
        
        # Try each pattern
        for pattern, replacement in self.test_patterns:
            if match := re.match(pattern, test_path):
                impl_path = re.sub(pattern, replacement, test_path)
                if impl_path in analysis_map:
                    return impl_path
        
        # Try fuzzy matching if no exact match found
        test_name = Path(test_path).stem.replace('test_', '').replace('_test', '')
        for impl_path in analysis_map:
            if test_name in impl_path and 'test' not in impl_path.lower():
                return impl_path
        
        return None

    def _create_test_mapping(self, test_path: str, impl_path: str,
                           test_analysis: FileAnalysis, impl_analysis: FileAnalysis) -> TestMapping:
        """Create detailed test mapping for a pair of files."""
        # Extract test functions and classes
        test_functions = []
        test_classes = []
        
        for func in test_analysis.functions:
            if func.name.startswith('test_'):
                test_functions.append(func.name)
        
        for cls in test_analysis.classes:
            if cls.name.startswith('Test'):
                test_classes.append(cls.name)
                # Include test methods from test classes
                for method in cls.methods:
                    if method.name.startswith('test_'):
                        test_functions.append(f"{cls.name}.{method.name}")
        
        # Calculate rough coverage score based on test-to-impl ratio
        impl_elements = (
            len(impl_analysis.functions) +
            sum(len(cls.methods) for cls in impl_analysis.classes)
        )
        test_elements = len(test_functions)
        
        coverage_score = min(1.0, test_elements / max(1, impl_elements))
        
        return TestMapping(
            test_file=test_path,
            impl_file=impl_path,
            test_functions=test_functions,
            test_classes=test_classes,
            coverage_score=coverage_score
        )

    def _update_metrics(self, analysis_map: Dict[str, FileAnalysis]):
        """Update project-wide test metrics."""
        total_files = len([f for f in analysis_map.values() if f.type != 'test'])
        files_with_tests = len(self.test_map)
        
        self.metrics.total_files = total_files
        self.metrics.files_with_tests = files_with_tests
        self.metrics.test_coverage = files_with_tests / total_files if total_files > 0 else 0
        
        # Track files missing tests
        self.metrics.missing_tests_files = [
            path for path, analysis in analysis_map.items()
            if analysis.type != 'test' and not analysis.has_tests
        ]

    def get_test_metrics(self, impl_path: str) -> Dict:
        """Get detailed test metrics for a specific implementation file."""
        if impl_path not in self.test_map:
            return {
                "has_tests": False,
                "test_file": None,
                "test_count": 0,
                "coverage_score": 0.0
            }
        
        mapping = self.test_map[impl_path]
        return {
            "has_tests": True,
            "test_file": mapping.test_file,
            "test_functions": mapping.test_functions,
            "test_classes": mapping.test_classes,
            "test_count": len(mapping.test_functions),
            "coverage_score": mapping.coverage_score
        }

    def suggest_missing_tests(self) -> List[Dict]:
        """Generate suggestions for missing or inadequate tests."""
        suggestions = []
        
        for path in self.metrics.missing_tests_files:
            suggestions.append({
                "file": path,
                "type": "missing_tests",
                "priority": "high",
                "message": "No tests found for this file"
            })
        
        for impl_path, mapping in self.test_map.items():
            if mapping.coverage_score < 0.5:
                suggestions.append({
                    "file": impl_path,
                    "type": "low_coverage",
                    "priority": "medium",
                    "message": f"Low test coverage ({mapping.coverage_score:.0%})",
                    "test_file": mapping.test_file
                })
        
        return suggestions 