import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.PathManager import PathManager
from core.TemplateManager import TemplateManager

class ProjectOptimizerAgent:
    def __init__(self, path_manager: PathManager, logger: Optional[Any] = None):
        """
        Initialize the ProjectOptimizerAgent.

        Args:
            path_manager (PathManager): Instance to resolve file paths.
            logger (Optional[Any]): Logger instance; defaults to print if not provided.
        """
        self.path_manager = path_manager
        self.logger = logger or print
        self.prompt_output_dir: Path = self.path_manager.get_temp_path("generated_prompts")
        self.prompt_output_dir.mkdir(parents=True, exist_ok=True)
        self.template_manager = TemplateManager()

    def load_optimization_plan(self, plan_path: str) -> List[Dict[str, Any]]:
        """
        Load the generated project optimization plan from a JSON file.

        Args:
            plan_path (str): Path to the optimization plan JSON.

        Returns:
            List[Dict[str, Any]]: The parsed optimization plan.
        
        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If JSON is invalid.
        """
        path = Path(plan_path)
        if not path.exists():
            raise FileNotFoundError(f"Optimization plan not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger(f"Error decoding JSON from {path}: {e}")
            raise

    def create_prompts_from_plan(self, plan: List[Dict[str, Any]]) -> List[Path]:
        """
        Create .prompt.md files for each task in the optimization plan.

        Args:
            plan (List[Dict[str, Any]]): The optimization plan.

        Returns:
            List[Path]: List of paths to the generated prompt files.
        """
        generated_prompts: List[Path] = []

        for entry in plan:
            file_path = entry.get("file")
            actions = entry.get("actions", [])
            if not file_path:
                self.logger("Warning: 'file' key missing in plan entry; skipping entry.")
                continue

            for i, action in enumerate(actions):
                prompt_file = self.prompt_output_dir / f"{Path(file_path).stem}_{i}.prompt.md"
                try:
                    content = self._render_action_prompt(file_path, action)
                except Exception as e:
                    self.logger(f"Error rendering prompt for {file_path}: {e}")
                    continue
                prompt_file.write_text(content, encoding="utf-8")
                generated_prompts.append(prompt_file)
                self.logger(f"[Generated] {prompt_file}")
        return generated_prompts

    def _render_action_prompt(self, target_file: str, action: Dict[str, Any]) -> str:
        """
        Render a prompt for a specific action using TemplateManager.

        Args:
            target_file (str): The file to optimize.
            action (Dict[str, Any]): A dictionary describing the action, including a "type" key
                                     and optionally an "output_path".

        Returns:
            str: The rendered prompt text.

        Raises:
            ValueError: If the action type is unsupported.
        """
        action_type = action.get("type")
        output_path = action.get("output_path", "")
        context = {
            "target_file": target_file,
            "output_path": output_path
        }
        # Map action types to template files (if available)
        template_mapping = {
            "generate_test": "full_sync/generate_test.prompt.j2",
            "refactor_suggestion": "full_sync/refactor_suggestion.prompt.j2"
        }
        template_file = template_mapping.get(action_type)
        if template_file:
            # Render using the TemplateManager for the general category
            rendered = self.template_manager.render_general_template(template_file, context)
            return rendered

        # Fallback default inline templates:
        if action_type == "generate_test":
            return (
                f"You are a test generation agent.\n\n"
                f"Generate tests for the file below.\n\n"
                f"Target File: {target_file}\n\n"
                f"Output Path: {output_path}\n\n"
                f"Return the full test code in Python."
            )
        elif action_type == "refactor_suggestion":
            return (
                f"You are a refactor expert.\n\n"
                f"Analyze this file for structural improvements and output a markdown report.\n\n"
                f"Target File: {target_file}\n\n"
                f"Output Path: {output_path}\n\n"
                f"Include suggestions, inline code blocks, and rationale."
            )
        else:
            raise ValueError(f"Unsupported action type: {action_type}")
