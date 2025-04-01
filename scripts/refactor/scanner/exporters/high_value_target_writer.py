"""
High Value Target Writer for Dream.OS Intelligence Scanner.

Identifies and prioritizes files that need attention based on:
- Test coverage gaps
- Code complexity
- Agent maturity levels
- Dependency issues
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class HighValueTarget:
    """A file that needs attention with reasons and suggestions."""
    file_path: str
    reasons: List[str]
    suggestions: List[str]
    score: float  # 0-1 priority score

class HighValueTargetWriter:
    """
    Analyzes scanner results to identify high-value targets for improvement.
    Outputs prioritized list of files that need attention.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.output_file = project_root / "high_value_targets.json"
        self.min_test_coverage = 0.7
        self.max_complexity = 0.8
        self.min_documentation = 0.4

    def process_report(self, scanner_report: Dict) -> Dict[str, Dict]:
        """
        Process scanner report to identify high-value targets.
        
        Args:
            scanner_report: Complete scanner analysis report
            
        Returns:
            Dict mapping file paths to their improvement details
        """
        insights = scanner_report["analysis_results"]["insights"]
        targets: Dict[str, HighValueTarget] = {}
        
        # Process test coverage issues
        self._process_test_insights(insights["test_insights"], targets)
        
        # Process dependency issues
        self._process_dependency_insights(insights["dependency_insights"], targets)
        
        # Process agent issues
        self._process_agent_insights(insights["agent_insights"], targets)
        
        # Process code quality issues
        self._process_quality_insights(insights["code_quality"], targets)
        
        # Convert to output format
        return {
            path: asdict(target)
            for path, target in sorted(
                targets.items(),
                key=lambda x: x[1].score,
                reverse=True
            )
        }

    def _process_test_insights(self, test_insights: Dict, targets: Dict[str, HighValueTarget]):
        """Process test coverage insights."""
        # Handle missing tests
        for item in test_insights.get("missing_tests", []):
            self._add_or_update_target(
                targets,
                item["file"],
                reason="missing_tests",
                suggestion="Create test file with comprehensive test cases",
                score_weight=1.0
            )
        
        # Handle low coverage
        for item in test_insights.get("low_coverage", []):
            if item.get("coverage", 0) < self.min_test_coverage:
                self._add_or_update_target(
                    targets,
                    item["file"],
                    reason="low_test_coverage",
                    suggestion=f"Increase test coverage (currently {item['coverage']:.0%})",
                    score_weight=0.8
                )

    def _process_dependency_insights(self, dep_insights: Dict, targets: Dict[str, HighValueTarget]):
        """Process dependency insights."""
        for item in dep_insights.get("high_risk_imports", []):
            if item.get("risk_type") == "circular_dependency":
                for file in item.get("cycle_path", []):
                    self._add_or_update_target(
                        targets,
                        file,
                        reason="circular_dependency",
                        suggestion="Break circular dependency using dependency injection",
                        score_weight=0.9
                    )
            elif item.get("risk_type") == "high_coupling":
                self._add_or_update_target(
                    targets,
                    item["file"],
                    reason="high_coupling",
                    suggestion="Reduce coupling by extracting shared functionality",
                    score_weight=0.7
                )

    def _process_agent_insights(self, agent_insights: Dict, targets: Dict[str, HighValueTarget]):
        """Process agent-related insights."""
        for item in agent_insights.get("suggestions", []):
            if item.get("maturity") in ["prototype", "beta"]:
                self._add_or_update_target(
                    targets,
                    item["agent"],
                    reason=f"low_agent_maturity_{item['maturity']}",
                    suggestion=f"Improve agent maturity: {item['message']}",
                    score_weight=0.8 if item['maturity'] == "prototype" else 0.6
                )

    def _process_quality_insights(self, quality_insights: Dict, targets: Dict[str, HighValueTarget]):
        """Process code quality insights."""
        for item in quality_insights.get("quality_issues", []):
            if item["type"] == "high_complexity":
                self._add_or_update_target(
                    targets,
                    item["file"],
                    reason="high_complexity",
                    suggestion="Reduce code complexity through refactoring",
                    score_weight=0.7
                )
            elif item["type"] == "low_documentation":
                self._add_or_update_target(
                    targets,
                    item["file"],
                    reason="low_documentation",
                    suggestion="Improve code documentation",
                    score_weight=0.5
                )

    def _add_or_update_target(self, targets: Dict[str, HighValueTarget],
                             file_path: str, reason: str, suggestion: str,
                             score_weight: float):
        """Add or update a target with new reason and suggestion."""
        if file_path not in targets:
            targets[file_path] = HighValueTarget(
                file_path=file_path,
                reasons=[reason],
                suggestions=[suggestion],
                score=score_weight
            )
        else:
            target = targets[file_path]
            if reason not in target.reasons:
                target.reasons.append(reason)
            if suggestion not in target.suggestions:
                target.suggestions.append(suggestion)
            # Update score to be the highest of all issues
            target.score = max(target.score, score_weight)

    def save_targets(self, targets: Dict[str, Dict]):
        """Save high-value targets to JSON file."""
        with self.output_file.open('w') as f:
            json.dump(targets, f, indent=2)
        
        logger.info(f"Saved {len(targets)} high-value targets to {self.output_file}")

    def get_top_targets(self, targets: Dict[str, Dict], limit: int = 5) -> List[Dict]:
        """Get the top N highest-priority targets."""
        return sorted(
            targets.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:limit] 