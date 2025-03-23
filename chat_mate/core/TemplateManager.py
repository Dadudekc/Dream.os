import os
import json
import logging
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from core.PathManager import PathManager
from social.log_writer import write_json_log

logger = logging.getLogger("TemplateManager")
logging.basicConfig(level=logging.INFO)


class TemplateManager:
    """
    Centralized manager for rendering Jinja2 templates across Discord, Messages, Reports, and Engagement Agents.
    - Auto-loads environments for each template category.
    - Supports optional default data injection (e.g., global variables).
    - Logs template activity for analytics and reinforcement engines.
    """

    def __init__(self, default_data: Optional[Dict] = None):
        # Ensure directory structure exists via PathManager
        PathManager.ensure_directories()

        # Default data to inject into all templates (optional)
        self.default_data = default_data or {}

        # Template categories and their paths
        self.template_categories = {
            "discord": PathManager.get_path('discord_templates'),
            "messages": PathManager.get_path('message_templates'),
            "general": PathManager.get_path('templates')
        }

        # Initialize Jinja2 environments dynamically
        self.environments = {
            category: self._init_environment(path)
            for category, path in self.template_categories.items()
        }

        for category, path in self.template_categories.items():
            logger.info(f" Loaded {category} templates from: {path}")

    def _init_environment(self, path: str) -> Environment:
        """
        Creates a Jinja2 Environment for a given path.
        """
        return Environment(
            loader=FileSystemLoader(path),
            autoescape=True
        )

    def render(self, category: str, template_filename: str, data: Dict) -> str:
        """
        Generic template renderer.
        :param category: Template category ('discord', 'messages', 'general', etc.)
        :param template_filename: Name of the template file.
        :param data: Dict of data to inject into the template.
        """
        if category not in self.environments:
            logger.error(f" Template category '{category}' is not registered.")
            return f"❌ Unknown template category: {category}"

        # Merge default data + provided data (priority to provided data)
        merged_data = {**self.default_data, **data}

        try:
            template = self.environments[category].get_template(template_filename)
            rendered = template.render(**merged_data)

            # Optional: Log successful template render
            self._log_template_render(category, template_filename, merged_data)

            return rendered

        except TemplateNotFound:
            logger.error(f" Template not found: {template_filename} (Category: {category})")
            return f"❌ Template '{template_filename}' not found in category '{category}'."

        except Exception as e:
            logger.error(f" Error rendering template '{template_filename}' (Category: {category}): {e}")
            return f"❌ Error rendering template '{template_filename}': {e}"

    def render_discord_template(self, template_filename: str, data: Dict) -> str:
        """
        Renders a Discord-specific template.
        """
        return self.render("discord", template_filename, data)

    def render_message_template(self, template_filename: str, data: Dict) -> str:
        """
        Renders a direct message / engagement template.
        """
        return self.render("messages", template_filename, data)

    def render_general_template(self, template_filename: str, data: Dict) -> str:
        """
        Renders a general-purpose template.
        """
        return self.render("general", template_filename, data)

    def list_templates(self, category: str) -> list:
        """
        Returns a list of available templates in a category.
        """
        path = self.template_categories.get(category)
        if not path or not os.path.isdir(path):
            logger.warning(f"️ No valid directory found for template category: {category}")
            return []

        return [
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and f.endswith('.j2')
        ]

    def _log_template_render(self, category: str, template_filename: str, data: Dict):
        """
        Logs rendering activity for tracking, analytics, or reinforcement learning.
        """
        log_data = {
            "category": category,
            "template": template_filename,
            "data": data
        }

        logger.info(f" Template rendered: {category}/{template_filename}")
        write_json_log(
            platform="TemplateManager",
            status="successful",
            tags=["template_render", category],
            ai_output=log_data
        )
