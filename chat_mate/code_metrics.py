import ast
import os
import radon.complexity as cc
import radon.metrics as rm
from typing import Dict, Any, List
from pathlib import Path
import coverage
import subprocess

class CodeMetricsAnalyzer:
    """Advanced code metrics analyzer for Python modules."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.coverage = coverage.Coverage()
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file for various metrics."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic metrics
            metrics = {
                'path': file_path,
                'size_bytes': os.path.getsize(file_path),
                'lines': len(content.splitlines())
            }
            
            # Cyclomatic complexity
            try:
                complexity_metrics = self._calculate_complexity(content)
                metrics.update(complexity_metrics)
            except:
                metrics.update({
                    'avg_complexity': 0,
                    'max_complexity': 0,
                    'total_complexity': 0
                })
            
            # Halstead metrics
            try:
                halstead = self._calculate_halstead(content)
                metrics.update(halstead)
            except:
                metrics.update({
                    'halstead_difficulty': 0,
                    'halstead_effort': 0,
                    'halstead_bugs': 0
                })
            
            # Maintainability index
            try:
                mi_score = self._calculate_maintainability(content)
                metrics['maintainability_index'] = mi_score
            except:
                metrics['maintainability_index'] = 0
            
            # Test coverage (if available)
            coverage_data = self._get_test_coverage(file_path)
            metrics.update(coverage_data)
            
            return metrics
        except Exception as e:
            return {
                'path': file_path,
                'error': str(e),
                'size_bytes': 0,
                'lines': 0,
                'avg_complexity': 0,
                'max_complexity': 0,
                'total_complexity': 0,
                'maintainability_index': 0,
                'coverage_percentage': 0
            }
    
    def _calculate_complexity(self, content: str) -> Dict[str, float]:
        """Calculate cyclomatic complexity metrics."""
        blocks = cc.cc_visit(content)
        if not blocks:
            return {
                'avg_complexity': 0,
                'max_complexity': 0,
                'total_complexity': 0
            }
        
        complexities = [block.complexity for block in blocks]
        return {
            'avg_complexity': sum(complexities) / len(complexities),
            'max_complexity': max(complexities),
            'total_complexity': sum(complexities)
        }
    
    def _calculate_halstead(self, content: str) -> Dict[str, float]:
        """Calculate Halstead metrics."""
        h = rm.h_visit(content)
        return {
            'halstead_difficulty': h.difficulty,
            'halstead_effort': h.effort,
            'halstead_bugs': h.bugs
        }
    
    def _calculate_maintainability(self, content: str) -> float:
        """Calculate maintainability index."""
        return rm.mi_visit(content, True)
    
    def _get_test_coverage(self, file_path: str) -> Dict[str, float]:
        """Get test coverage data for the file."""
        try:
            # Run pytest with coverage
            relative_path = os.path.relpath(file_path, self.root_dir)
            test_file = f"tests/test_{os.path.basename(file_path)}"
            
            if os.path.exists(os.path.join(self.root_dir, test_file)):
                subprocess.run(
                    ['pytest', '--cov=' + relative_path, test_file],
                    cwd=str(self.root_dir),
                    capture_output=True
                )
                
                # Read coverage data
                self.coverage.load()
                file_coverage = self.coverage.get_data().get_file_report(file_path)
                
                return {
                    'coverage_percentage': file_coverage.total_coverage,
                    'covered_lines': len(file_coverage.covered_lines()),
                    'missing_lines': len(file_coverage.missing_lines())
                }
        except:
            pass
        
        return {
            'coverage_percentage': 0,
            'covered_lines': 0,
            'missing_lines': 0
        }
    
    def analyze_directory(self) -> Dict[str, Dict[str, Any]]:
        """Analyze all Python files in the directory."""
        results = {}
        
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    results[file_path] = self.analyze_file(file_path)
        
        return results

def get_code_metrics(root_dir: str) -> Dict[str, Dict[str, Any]]:
    """Get comprehensive code metrics for all Python files in the directory."""
    analyzer = CodeMetricsAnalyzer(root_dir)
    return analyzer.analyze_directory() 