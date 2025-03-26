import os
import json
import logging
from pathlib import Path
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

    def __init__(self, template_dir: Optional[str] = None, default_data: Optional[Dict] = None):
        """
        Initialize the TemplateManager.
        
        Args:
            template_dir (Optional[str]): Optional override for the general templates directory.
                If provided, this will be used for the 'general' category; otherwise, PathManager's path is used.
            default_data (Optional[Dict]): Default data to inject into all templates.
        """
        # Ensure directory structure exists via PathManager
        PathManager.ensure_directories()

        self.default_data = default_data or {}

        # Template categories and their paths
        self.template_categories = {
            "discord": PathManager.get_path('discord_templates'),
            "messages": PathManager.get_path('message_templates'),
            "general": template_dir if template_dir else PathManager.get_path('templates')
        }

        # Initialize Jinja2 environments for each category
        self.environments = {
            category: self._init_environment(path)
            for category, path in self.template_categories.items()
        }

        # Active template (default is None until set)
        self.active_template = None

        for category, path in self.template_categories.items():
            logger.info(f"Loaded {category} templates from: {path}")

    def _init_environment(self, path: str) -> Environment:
        """
        Creates a Jinja2 Environment for a given path.
        """
        return Environment(
            loader=FileSystemLoader(path),
            autoescape=True
        )

    def set_active_template(self, template_name: str, category: str = "general"):
        """
        Sets the active template for rendering.
        
        Args:
            template_name (str): The filename of the template to set active.
            category (str): Template category to look in (default: 'general').
        
        Raises:
            TemplateNotFound: If the template is not found in the specified category.
        """
        available_templates = self.get_available_templates(category)
        if template_name in available_templates:
            self.active_template = template_name
            logger.info(f"Active template set to: {template_name} (Category: {category})")
        else:
            error_msg = f"Template '{template_name}' not found in category '{category}'."
            logger.error(error_msg)
            raise TemplateNotFound(error_msg)

    def render(self, category: str, template_filename: str, data: Dict) -> str:
        """
        Generic template renderer.
        
        Args:
            category (str): Template category ('discord', 'messages', 'general', etc.)
            template_filename (str): Name of the template file.
            data (Dict): Dict of data to inject into the template.
            
        Returns:
            str: The rendered template or an error message if rendering fails.
        """
        if category not in self.environments:
            error_msg = f"❌ Unknown template category: {category}"
            logger.error(error_msg)
            return error_msg

        # Merge default data + provided data (priority to provided data)
        merged_data = {**self.default_data, **data}

        try:
            template = self.environments[category].get_template(template_filename)
            rendered = template.render(**merged_data)

            # Log successful template render
            self._log_template_render(category, template_filename, merged_data)

            return rendered

        except TemplateNotFound:
            error_msg = f"❌ Template '{template_filename}' not found in category '{category}'."
            logger.error(error_msg)
            return error_msg

        except Exception as e:
            error_msg = f"❌ Error rendering template '{template_filename}': {e}"
            logger.error(error_msg)
            return error_msg

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
            logger.warning(f"⚠️ No valid directory found for template category: {category}")
            return []

        return [
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and f.endswith('.j2')
        ]

    def get_available_templates(self, category: str = "general") -> list:
        """
        Returns a sorted list of available templates for a given category.
        
        Args:
            category (str): Template category. Defaults to 'general'.
        
        Returns:
            list: Sorted list of template filenames.
        """
        templates = self.list_templates(category)
        return sorted(templates)

    def _log_template_render(self, category: str, template_filename: str, data: Dict):
        """
        Logs rendering activity for tracking, analytics, or reinforcement learning.
        """
        log_data = {
            "category": category,
            "template": template_filename,
            "data": data
        }

        logger.info(f"✅ Template rendered: {category}/{template_filename}")
        write_json_log(
            platform="TemplateManager",
            result="success",
            tags=["template_render", category],
            ai_output=log_data
        )

    def render_template(self, context: Dict) -> str:
        """
        Renders the currently active general template using the provided context.
        
        Args:
            context (Dict): Data to inject into the active template.
        
        Returns:
            str: Rendered template output.
        """
        if not self.active_template:
            error_msg = "❌ No active template is set."
            logger.error(error_msg)
            return error_msg

        return self.render("general", self.active_template, context)
