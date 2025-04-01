"""
Code Quality Dashboard
A real-time code quality monitoring and trend tracking system powered by Dream.OS scanner
"""

from typing import Dict, List, Union, Optional, Protocol

class FileAnalysis(Protocol):
    """Protocol defining the interface we expect from FileAnalysis"""
    complexity: float
    has_docstrings: bool

class Scanner(Protocol):
    """Protocol defining the interface we expect from scanner"""
    def get_file_analysis(self, file_path: str) -> Optional[FileAnalysis]: ...

class Dashboard:
    """
    Core dashboard class that provides code quality metrics and trend analysis
    Integrates with Dream.OS scanner for deep code intelligence
    """
    def __init__(self, scanner: Optional[Scanner] = None):
        """Initialize an empty dashboard instance"""
        self.scanner = scanner
        self.metrics: Dict[str, float] = {}
        self.trends: Dict[str, List[float]] = {"complexity_trend": []}
        self.current_file: Optional[str] = None
        self._current_analysis: Optional[FileAnalysis] = None

    def is_ready(self) -> bool:
        """Check if dashboard has analyzed a file and is ready to provide metrics"""
        return self.current_file is not None and bool(self.metrics)

    def analyze_file(self, file_path: str) -> None:
        """
        Analyze a file to extract code quality metrics
        
        Args:
            file_path: Path to the file to analyze
            
        Raises:
            FileNotFoundError: If file cannot be found or analyzed
            RuntimeError: If no scanner is configured
        """
        if not self.scanner:
            raise RuntimeError("No scanner configured")
            
        self.current_file = file_path
        analysis = self.scanner.get_file_analysis(file_path)
        
        if not analysis:
            self.current_file = None
            raise FileNotFoundError(f"No analysis found for {file_path}")
            
        self._current_analysis = analysis
        self.metrics = {
            "complexity": self._calculate_complexity(analysis),
            "maintainability": self._calculate_maintainability(analysis)
        }

    def get_current_metrics(self) -> Dict[str, float]:
        """Get the current metrics for the analyzed file"""
        return self.metrics

    def record_snapshot(self) -> None:
        """Record current metrics in trends for historical tracking"""
        if "complexity" in self.metrics:
            self.trends["complexity_trend"].append(self.metrics["complexity"])

    def get_trends(self) -> Dict[str, List[float]]:
        """Get historical trends of metrics over time"""
        return self.trends

    def _calculate_complexity(self, analysis: FileAnalysis) -> float:
        """
        Calculate code complexity score
        Currently uses cyclomatic complexity as base metric
        """
        # Start with cyclomatic complexity
        base_score = analysis.complexity
        
        # Normalize to a 0-100 scale where lower is better
        normalized_score = min(100, max(0, base_score))
        
        return normalized_score

    def _calculate_maintainability(self, analysis: FileAnalysis) -> float:
        """
        Calculate maintainability index on 0-1 scale
        Uses complexity, code structure, and documentation metrics
        """
        if not analysis:
            return 0.0
            
        # Start with inverse of normalized complexity (0-1 scale)
        complexity_factor = max(0, 1 - (self._calculate_complexity(analysis) / 100))
        
        # Factor in documentation and code structure
        # These weights can be tuned based on real-world usage
        doc_weight = 0.3
        complexity_weight = 0.7
        
        # Simplified maintainability score
        score = (
            complexity_weight * complexity_factor +
            doc_weight * (1 if analysis.has_docstrings else 0)
        )
        
        return max(0, min(1, score))  # Ensure result is between 0 and 1 