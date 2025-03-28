import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from core.PathManager import PathManager
from core.TemplateManager import TemplateManager


class DreamscapeGenerationService:
    """
    Backend-only service for generating Dreamscape episodes.
    Supports rendering from templates or raw memory injection.
    """

    def __init__(
        self,
        path_manager: Optional[PathManager] = None,
        template_manager: Optional[TemplateManager] = None,
        logger: Optional[logging.Logger] = None,
        memory_data: Optional[Dict[str, Any]] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.path_manager = path_manager or PathManager()
        self.template_manager = template_manager or TemplateManager()
        self.memory_data = memory_data or {}

        self.output_dir = self.path_manager.get_path("dreamscape")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"[DreamscapeService] Output directory set to: {self.output_dir}")

    def load_context_from_file(self, json_path: str) -> Dict[str, Any]:
        """Load rendering context from JSON file."""
        try:
            path = Path(json_path)
            if not path.exists():
                raise FileNotFoundError(f"Context file not found: {json_path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.logger.info(f"[Context Loaded] {json_path}")
            return data
        except Exception as e:
            self.logger.error(f"[Error] Failed to load context: {e}")
            return {}

    def generate_context_from_memory(self) -> Dict[str, Any]:
        """Constructs a context dict from the injected memory structure."""
        return {
            "themes": self.memory_data.get("themes", []),
            "characters": self.memory_data.get("characters", []),
            "realms": self.memory_data.get("realms", []),
            "artifacts": self.memory_data.get("artifacts", []),
            "skill_levels": self.memory_data.get("skill_levels", {}),
            "architect_tier": self.memory_data.get("architect_tier", {}),
            "quests": self.memory_data.get("quests", {}),
            "protocols": self.memory_data.get("protocols", []),
            "stabilized_domains": self.memory_data.get("stabilized_domains", []),
        }

    def render_episode(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Dreamscape episode from a template and context."""
        try:
            output = self.template_manager.render_general_template(template_name, context)
            self.logger.info(f"[Rendered] Template: {template_name}")
            return output
        except Exception as e:
            self.logger.error(f"[Error] Rendering failed: {e}")
            return f"# Error rendering template\n\n{e}"

    def save_episode(self, name: str, content: str, format: str = "md") -> Path:
        """Save the rendered episode to disk."""
        try:
            path = self.output_dir / f"{name}.{format}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"[Saved] Episode → {path}")
            return path
        except Exception as e:
            self.logger.error(f"[Error] Saving episode failed: {e}")
            return Path()

    def generate_episode_from_template(self, template_name: str, context_path: str, output_name: str) -> Optional[Path]:
        """Load context from JSON, render it with template, and save output."""
        context = self.load_context_from_file(context_path)
        if not context:
            return None
        rendered = self.render_episode(template_name, context)
        return self.save_episode(output_name, rendered)

    def generate_episode_from_memory(self, template_name: str, output_name: Optional[str] = None) -> Optional[Path]:
        """Render and save an episode using memory-driven context."""
        context = self.generate_context_from_memory()
        rendered = self.render_episode(template_name, context)

        if not output_name:
            output_name = f"episode_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return self.save_episode(output_name, rendered)
