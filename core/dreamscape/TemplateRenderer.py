import os
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

class TemplateRenderer:
    """
    Handles all template rendering operations for Dreamscape episodes.
    Uses Jinja2 to load and render templates with context data.
    """
    
    def __init__(self, template_dir: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the template renderer with a directory containing templates.
        
        Args:
            template_dir: Directory containing Jinja2 templates
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.template_dir = template_dir
        self._setup_jinja_env()
        
    def _setup_jinja_env(self):
        """Set up the Jinja2 environment with the template directory."""
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.logger.info(f"✅ Jinja2 environment initialized with template dir: {self.template_dir}")
        except Exception as e:
            self.logger.error(f"❌ Error setting up Jinja2 environment: {str(e)}")
            raise
            
    def load_template(self, template_name: str) -> Optional[Template]:
        """
        Load a template by name from the template directory.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            The loaded Jinja2 template or None if not found
        """
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            self.logger.error(f"❌ Error loading template '{template_name}': {str(e)}")
            return None
            
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Render a template with the provided context data.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of data to inject into the template
            
        Returns:
            The rendered template string or None if rendering failed
        """
        template = self.load_template(template_name)
        if not template:
            return None
            
        try:
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"❌ Error rendering template '{template_name}': {str(e)}")
            return None
            
    def render_string_template(self, template_string: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Render a template from a string with the provided context data.
        
        Args:
            template_string: The template as a string
            context: Dictionary of data to inject into the template
            
        Returns:
            The rendered template string or None if rendering failed
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"❌ Error rendering string template: {str(e)}")
            return None
            
    def validate_template_context(self, template_name: str, context: Dict[str, Any]) -> list:
        """
        Validate that all required variables for a template are present in the context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of context data to validate
            
        Returns:
            List of missing variable names
        """
        template = self.load_template(template_name)
        if not template:
            return []
            
        try:
            # Get all variables used in the template
            ast = self.env.parse(template.source)
            variables = {node.name for node in ast.find_all(self.env.name_type)}
            
            # Check which variables are missing from context
            missing = [var for var in variables if var not in context]
            return missing
        except Exception as e:
            self.logger.error(f"❌ Error validating template context: {str(e)}")
            return [] 