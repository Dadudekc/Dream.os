"""
Cursor Prompt Task Generator for Dream.OS Intelligence Scanner.

Converts scanner insights into structured Cursor prompt tasks for:
- Test coverage improvements
- Dependency optimizations
- Agent refactoring
- Documentation enhancements
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CursorTask:
    """Structured task for Cursor prompt generation."""
    task_type: str
    file_path: str
    priority: str
    context: Dict
    recommendation: str

class PromptTaskGenerator:
    """
    Generates Cursor prompt tasks from scanner insights.
    Tasks are saved as JSON files in .cursor/queued_tasks/.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cursor_tasks_dir = project_root / ".cursor" / "queued_tasks"
        self.cursor_tasks_dir.mkdir(parents=True, exist_ok=True)

    def generate_tasks(self, scanner_report: Dict) -> List[CursorTask]:
        """
        Generate Cursor tasks from scanner insights.
        
        Args:
            scanner_report: Complete scanner analysis report
            
        Returns:
            List of generated CursorTask objects
        """
        tasks = []
        insights = scanner_report["analysis_results"]["insights"]
        
        # Generate test coverage tasks
        tasks.extend(self._generate_test_tasks(insights["test_insights"]))
        
        # Generate dependency optimization tasks
        tasks.extend(self._generate_dependency_tasks(insights["dependency_insights"]))
        
        # Generate agent improvement tasks
        tasks.extend(self._generate_agent_tasks(insights["agent_insights"]))
        
        # Generate code quality tasks
        tasks.extend(self._generate_quality_tasks(insights["code_quality"]))
        
        return tasks

    def _generate_test_tasks(self, test_insights: Dict) -> List[CursorTask]:
        """Generate tasks for improving test coverage."""
        tasks = []
        
        for item in test_insights.get("missing_tests", []):
            tasks.append(CursorTask(
                task_type="increase_test_coverage",
                file_path=item["file"],
                priority="high",
                context={
                    "test_coverage": 0.0,
                    "missing_functions": self._get_untested_functions(item["file"]),
                    "test_file": self._get_test_file_path(item["file"])
                },
                recommendation="Create missing test file with pytest fixtures and test cases."
            ))
            
        for item in test_insights.get("low_coverage", []):
            tasks.append(CursorTask(
                task_type="improve_test_coverage",
                file_path=item["file"],
                priority="medium",
                context={
                    "test_coverage": item["coverage"],
                    "missing_tests": item.get("missing_tests", []),
                    "test_file": item["test_file"]
                },
                recommendation=f"Add tests for uncovered functions: {', '.join(item.get('missing_tests', []))}"
            ))
            
        return tasks

    def _generate_dependency_tasks(self, dep_insights: Dict) -> List[CursorTask]:
        """Generate tasks for optimizing dependencies."""
        tasks = []
        
        for item in dep_insights.get("high_risk_imports", []):
            tasks.append(CursorTask(
                task_type="optimize_dependencies",
                file_path=item["file"],
                priority="high" if item.get("risk_type") == "circular_dependency" else "medium",
                context={
                    "risk_type": item["risk_type"],
                    "details": item["details"],
                    "affected_files": item.get("cycle_path", [])
                },
                recommendation=self._get_dependency_recommendation(item)
            ))
            
        return tasks

    def _generate_agent_tasks(self, agent_insights: Dict) -> List[CursorTask]:
        """Generate tasks for improving agents."""
        tasks = []
        
        for item in agent_insights.get("suggestions", []):
            tasks.append(CursorTask(
                task_type="improve_agent",
                file_path=item["agent"],
                priority=item.get("priority", "medium"),
                context={
                    "agent_type": item.get("type"),
                    "maturity": item.get("maturity"),
                    "current_score": item.get("current_score", 0.0)
                },
                recommendation=item["message"]
            ))
            
        return tasks

    def _generate_quality_tasks(self, quality_insights: Dict) -> List[CursorTask]:
        """Generate tasks for improving code quality."""
        tasks = []
        
        for item in quality_insights.get("quality_issues", []):
            tasks.append(CursorTask(
                task_type="improve_code_quality",
                file_path=item["file"],
                priority=item.get("priority", "medium"),
                context={
                    "issue_type": item["type"],
                    "current_score": item.get("current_score", 0.0)
                },
                recommendation=item["message"]
            ))
            
        return tasks

    def save_tasks(self, tasks: List[CursorTask]):
        """Save generated tasks as JSON files."""
        for i, task in enumerate(tasks):
            file_id = f"{task.task_type}_{i:03d}"
            task_path = self.cursor_tasks_dir / f"{file_id}.json"
            
            with task_path.open('w') as f:
                json.dump(asdict(task), f, indent=2)
            
            logger.info(f"Saved Cursor task: {task_path}")

    def _get_untested_functions(self, file_path: str) -> List[str]:
        """Extract list of untested functions from file."""
        # This would use the scanner's analysis map to get function info
        return []  # Placeholder

    def _get_test_file_path(self, source_file: str) -> str:
        """Generate appropriate test file path."""
        path = Path(source_file)
        return str(path.parent / f"test_{path.name}")

    def _get_dependency_recommendation(self, dep_item: Dict) -> str:
        """Generate specific recommendation for dependency issue."""
        if dep_item.get("risk_type") == "circular_dependency":
            return "Break circular dependency using dependency injection or interface extraction."
        elif dep_item.get("risk_type") == "high_coupling":
            return "Reduce coupling by extracting shared functionality into a separate module."
        else:
            return "Review and optimize import structure." 