"""
Test Coverage Analyzer module for analyzing test coverage.
"""
from typing import Optional, Any, Dict, List
import logging
from pathlib import Path
import coverage

class TestCoverageAnalyzer:
    """Analyzer for test coverage using coverage.py data."""
    
    def __init__(
        self,
        config: Any,
        coverage_data_file: str = ".coverage",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the test coverage analyzer.
        
        Args:
            config: The configuration manager
            coverage_data_file: Path to the .coverage data file.
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.coverage_data_file = coverage_data_file
        self.coverage_data = {}
        
    def analyze_file(self, file_path: str) -> Optional[Dict]:
        """
        Analyze test coverage for a specific file using coverage.py data.
        
        Args:
            file_path: Absolute or relative path to the source file.
            
        Returns:
            Coverage data dictionary or None if analysis fails.
        """
        try:
            cov = coverage.Coverage(data_file=self.coverage_data_file)
            cov.load()

            # Get analysis results for the specific file
            # analysis2 returns: filename, statements, excluded, missing, missing_formatted
            # Note: file_path needs to match how it's stored in the .coverage file (often relative to project root)
            try:
                # Try finding the file exactly as provided first
                analysis_result = cov.analysis2(file_path)
            except coverage.misc.NoSource:
                 # If not found, try resolving relative to project root (common case)
                 # This requires PathManager to be available or configured differently
                 self.logger.warning(f"Could not find source for '{file_path}' directly. Attempting relative path.")
                 # Assuming project root might be derivable from coverage data file path or config
                 # This part might need refinement depending on how paths are stored/accessed
                 try:
                     base_dir = Path(self.coverage_data_file).parent
                     relative_file_path = str(Path(file_path).relative_to(base_dir)) # Example heuristic
                     analysis_result = cov.analysis2(relative_file_path)
                 except (coverage.misc.NoSource, ValueError, Exception) as inner_e:
                     self.logger.error(f"Could not find source for '{file_path}' even with relative path attempt: {inner_e}")
                     return None

            if not analysis_result:
                 self.logger.warning(f"No coverage data found for file: {file_path}")
                 return None
                 
            _fname, statements, _excluded, missing, missing_formatted = analysis_result
            
            lines_total = len(statements)
            lines_missed = len(missing)
            lines_covered = lines_total - lines_missed
            coverage_percent = (lines_covered / lines_total * 100) if lines_total > 0 else 0.0

            # TODO: Implement actual coverage analysis - Replaced
            coverage_dict = {
                "file": file_path, # Store the originally requested path
                "lines_total": lines_total,
                "lines_covered": lines_covered,
                "lines_missed": lines_missed,
                "coverage_percent": round(coverage_percent, 2),
                "uncovered_lines": sorted(missing), # Store line numbers
                "uncovered_formatted": missing_formatted # Store formatted ranges (e.g., '10-15')
            }
            # self.coverage_data[file_path] = coverage # Store analysis result
            # self.logger.info(f"Analyzed coverage for: {file_path}")
            # return coverage

            self.coverage_data[file_path] = coverage_dict # Store analysis result
            self.logger.info(f"Coverage analysis successful for: {file_path} ({coverage_dict['coverage_percent']} %)")
            return coverage_dict
            
        except coverage.misc.CoverageException as e:
             self.logger.error(f"Coverage.py error analyzing {file_path}: {e}")
             return None
        except FileNotFoundError:
             self.logger.error(f"Coverage data file not found at: {self.coverage_data_file}")
             return None
        except Exception as e:
            self.logger.error(f"Unexpected error analyzing coverage for {file_path}: {e}", exc_info=True)
            return None
            
    def get_file_coverage(self, file_path: str) -> Optional[Dict]:
        """
        Get coverage data for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Coverage data or None
        """
        return self.coverage_data.get(file_path)
        
    def get_total_coverage(self) -> Dict:
        """
        Get total coverage statistics.
        
        Returns:
            Total coverage data
        """
        total_lines = 0
        covered_lines = 0
        
        for coverage in self.coverage_data.values():
            total_lines += coverage["lines_total"]
            covered_lines += coverage["lines_covered"]
            
        return {
            "files_analyzed": len(self.coverage_data),
            "total_lines": total_lines,
            "covered_lines": covered_lines,
            "coverage_percent": (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
        } 