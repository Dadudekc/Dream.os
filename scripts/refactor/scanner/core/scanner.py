"""
Dream.OS Intelligence Scanner Core.

Orchestrates the analysis of the Dream.OS codebase using specialized mappers:
- Deep AST analysis for code structure and metrics
- Test coverage and quality analysis
- Agent identification and profiling
- Dependency tracking and optimization
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import asdict

from ..models import FileAnalysis, ProjectMetrics
from .deep_ast import DeepASTAnalyzer
from .test_mapper import TestMapper
from .agent_map import AgentMapper
from .dependency_map import DependencyMapper

logger = logging.getLogger(__name__)

class IntelligenceScanner:
    """
    Core scanner that orchestrates the analysis of the Dream.OS codebase.
    Coordinates specialized mappers and aggregates their insights.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.analysis_map: Dict[str, FileAnalysis] = {}
        self.metrics = ProjectMetrics()
        
        # Initialize specialized analyzers
        self.ast_analyzer = DeepASTAnalyzer()
        self.test_mapper = TestMapper()
        self.agent_mapper = AgentMapper()
        self.dependency_mapper = DependencyMapper()
        
        # Cache for incremental scanning
        self.scan_cache = {}

    def scan_project(self, incremental: bool = True) -> Dict:
        """
        Perform complete project analysis.
        
        Args:
            incremental: Whether to use cached results for unchanged files
            
        Returns:
            Dict containing complete analysis results and insights
        """
        logger.info(f"Starting Dream.OS Intelligence Scan of {self.project_root}")
        
        # Phase 1: Deep AST Analysis
        self._perform_ast_analysis(incremental)
        
        # Phase 2: Test Analysis
        test_map = self.test_mapper.map_tests(self.analysis_map)
        
        # Phase 3: Agent Analysis
        agent_map = self.agent_mapper.map_agents(self.analysis_map)
        
        # Phase 4: Dependency Analysis
        dependency_graph = self.dependency_mapper.build_graph(self.analysis_map)
        
        # Phase 5: Generate Insights
        insights = self._generate_insights(
            test_map, agent_map, dependency_graph
        )
        
        # Prepare final report
        return self._prepare_report(insights)

    def _perform_ast_analysis(self, incremental: bool):
        """Perform deep AST analysis of all Python files."""
        python_files = list(self.project_root.rglob("*.py"))
        total_files = len(python_files)
        
        logger.info(f"Found {total_files} Python files to analyze")
        
        for i, file_path in enumerate(python_files, 1):
            rel_path = file_path.relative_to(self.project_root).as_posix()
            
            # Skip if unchanged and in cache
            if incremental and self._is_cached(file_path):
                self.analysis_map[rel_path] = self.scan_cache[rel_path]
                continue
                
            logger.debug(f"Analyzing [{i}/{total_files}] {rel_path}")
            
            try:
                analysis = self.ast_analyzer.enrich_analysis(
                    file_path=file_path,
                    existing_analysis=self.analysis_map.get(rel_path)
                )
                self.analysis_map[rel_path] = analysis
                
                if incremental:
                    self.scan_cache[rel_path] = analysis
                    
            except Exception as e:
                logger.error(f"Error analyzing {rel_path}: {str(e)}")

    def _is_cached(self, file_path: Path) -> bool:
        """Check if file analysis is cached and up to date."""
        if not file_path.exists():
            return False
            
        rel_path = file_path.relative_to(self.project_root).as_posix()
        if rel_path not in self.scan_cache:
            return False
            
        cached_mtime = self.scan_cache[rel_path].last_modified
        current_mtime = file_path.stat().st_mtime
        
        return cached_mtime == current_mtime

    def _generate_insights(self, test_map: Dict, agent_map: Dict,
                         dependency_graph: Dict) -> Dict:
        """Generate high-level insights from analysis results."""
        insights = {
            "test_insights": {
                "coverage_summary": self.test_mapper.get_test_metrics(""),
                "missing_tests": self.test_mapper.suggest_missing_tests()
            },
            "agent_insights": {
                "metrics": self.agent_mapper.get_agent_metrics(),
                "suggestions": self.agent_mapper.suggest_improvements()
            },
            "dependency_insights": {
                "high_risk_imports": self.dependency_mapper.get_high_risk_imports(),
                "refactor_suggestions": self.dependency_mapper.suggest_refactors()
            },
            "code_quality": self._analyze_code_quality(),
            "optimization_opportunities": self._identify_optimizations()
        }
        
        return insights

    def _analyze_code_quality(self) -> Dict:
        """Analyze overall code quality metrics."""
        total_complexity = 0
        total_documentation = 0
        files_analyzed = 0
        
        quality_issues = []
        
        for file_analysis in self.analysis_map.values():
            if not file_analysis.is_test:
                files_analyzed += 1
                total_complexity += file_analysis.complexity_score
                total_documentation += file_analysis.documentation_score
                
                # Track quality issues
                if file_analysis.complexity_score > 0.8:
                    quality_issues.append({
                        "file": file_analysis.path,
                        "type": "high_complexity",
                        "message": "File has high complexity score"
                    })
                    
                if file_analysis.documentation_score < 0.3:
                    quality_issues.append({
                        "file": file_analysis.path,
                        "type": "low_documentation",
                        "message": "File lacks adequate documentation"
                    })
        
        return {
            "average_complexity": total_complexity / max(1, files_analyzed),
            "average_documentation": total_documentation / max(1, files_analyzed),
            "quality_issues": quality_issues
        }

    def _identify_optimizations(self) -> List[Dict]:
        """Identify potential optimization opportunities."""
        opportunities = []
        
        # Look for duplicate code patterns
        duplicate_patterns = self._find_duplicate_patterns()
        if duplicate_patterns:
            opportunities.append({
                "type": "duplicate_code",
                "files": duplicate_patterns,
                "message": "Consider extracting common code into shared utilities"
            })
        
        # Identify complex inheritance chains
        complex_inheritance = self._find_complex_inheritance()
        if complex_inheritance:
            opportunities.append({
                "type": "complex_inheritance",
                "classes": complex_inheritance,
                "message": "Consider simplifying inheritance hierarchy"
            })
        
        # Find underutilized utilities
        underutilized = self._find_underutilized_code()
        if underutilized:
            opportunities.append({
                "type": "underutilized",
                "components": underutilized,
                "message": "Consider removing or consolidating rarely used utilities"
            })
        
        return opportunities

    def _find_duplicate_patterns(self) -> List[Dict]:
        """Find potential duplicate code patterns."""
        duplicates = []
        method_signatures = {}
        
        for file_analysis in self.analysis_map.values():
            for class_info in file_analysis.classes:
                for method in class_info.methods:
                    # Create signature from method name and args
                    signature = f"{method.name}({','.join(method.args.keys())})"
                    
                    if signature in method_signatures:
                        duplicates.append({
                            "pattern": signature,
                            "locations": [
                                method_signatures[signature],
                                f"{file_analysis.path}:{class_info.name}"
                            ]
                        })
                    else:
                        method_signatures[signature] = f"{file_analysis.path}:{class_info.name}"
        
        return duplicates

    def _find_complex_inheritance(self) -> List[Dict]:
        """Identify complex class inheritance hierarchies."""
        complex_hierarchies = []
        
        for file_analysis in self.analysis_map.values():
            for class_info in file_analysis.classes:
                if len(class_info.bases) > 2:  # Multiple inheritance
                    complex_hierarchies.append({
                        "class": class_info.name,
                        "file": file_analysis.path,
                        "bases": class_info.bases
                    })
        
        return complex_hierarchies

    def _find_underutilized_code(self) -> List[Dict]:
        """Find potentially underutilized code components."""
        # Track usage of each component
        usage_count = {}
        
        # First pass: register all components
        for file_analysis in self.analysis_map.values():
            for class_info in file_analysis.classes:
                usage_count[f"{file_analysis.path}:{class_info.name}"] = 0
                
            for func in file_analysis.functions:
                usage_count[f"{file_analysis.path}:{func.name}"] = 0
        
        # Second pass: count usages
        for file_analysis in self.analysis_map.values():
            for import_info in file_analysis.imports:
                if import_info.imported_names:
                    for name in import_info.imported_names:
                        key = f"{import_info.resolved_path}:{name}"
                        if key in usage_count:
                            usage_count[key] += 1
        
        # Find components with low usage
        underutilized = []
        for component, count in usage_count.items():
            if count <= 1:  # Only used in its own file or not at all
                file_path, name = component.split(":")
                underutilized.append({
                    "component": name,
                    "file": file_path,
                    "usage_count": count
                })
        
        return underutilized

    def _prepare_report(self, insights: Dict) -> Dict:
        """Prepare final analysis report."""
        return {
            "project_info": {
                "root": str(self.project_root),
                "files_analyzed": len(self.analysis_map),
                "last_scan_time": self.metrics.last_scan_time
            },
            "analysis_results": {
                "file_analysis": {
                    path: asdict(analysis)
                    for path, analysis in self.analysis_map.items()
                },
                "insights": insights
            },
            "metrics": asdict(self.metrics),
            "suggestions": self._compile_suggestions(insights)
        }

    def _compile_suggestions(self, insights: Dict) -> List[Dict]:
        """Compile and prioritize all improvement suggestions."""
        all_suggestions = []
        
        # Add test-related suggestions
        all_suggestions.extend(insights["test_insights"]["missing_tests"])
        
        # Add agent-related suggestions
        all_suggestions.extend(insights["agent_insights"]["suggestions"])
        
        # Add dependency-related suggestions
        all_suggestions.extend(insights["dependency_insights"]["refactor_suggestions"])
        
        # Add code quality suggestions
        for issue in insights["code_quality"]["quality_issues"]:
            all_suggestions.append({
                "type": "code_quality",
                "priority": "medium",
                **issue
            })
        
        # Add optimization suggestions
        for opt in insights["optimization_opportunities"]:
            all_suggestions.append({
                "type": "optimization",
                "priority": "low",
                **opt
            })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return all_suggestions

    def save_report(self, output_path: Path):
        """Save analysis report to file."""
        report = self.scan_project()
        
        with output_path.open('w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Analysis report saved to {output_path}")

    def get_file_analysis(self, file_path: str) -> Optional[FileAnalysis]:
        """Get analysis results for a specific file."""
        return self.analysis_map.get(file_path)

    def get_summary_stats(self) -> Dict:
        """Get summary statistics of the analysis."""
        return {
            "total_files": len(self.analysis_map),
            "total_classes": sum(
                len(analysis.classes)
                for analysis in self.analysis_map.values()
            ),
            "total_functions": sum(
                len(analysis.functions)
                for analysis in self.analysis_map.values()
            ),
            "test_coverage": self.metrics.test_coverage,
            "average_complexity": sum(
                analysis.complexity_score
                for analysis in self.analysis_map.values()
            ) / max(1, len(self.analysis_map))
        } 