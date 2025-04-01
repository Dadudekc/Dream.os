"""
Template Engine Module

This module provides template rendering capabilities using Jinja2.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class TemplateEngine:
    """Template rendering engine using Jinja2."""
    
    def __init__(self):
        """Initialize the template engine."""
        self._check_dependencies()
        self.template_dirs = [
            Path("templates"),
            Path("core/templates"),
            Path("core/rendering/templates")
        ]
        self._ensure_template_dirs()
        logger.info("Template engine initialized")
        
    def _check_dependencies(self) -> None:
        """Check for required dependencies and install if missing."""
        try:
            import jinja2
        except ImportError:
            logger.warning("Jinja2 not found. Installing...")
            self._install_dependencies()
            
    def _install_dependencies(self) -> None:
        """Install required packages."""
        try:
            import pip
            pip.main(['install', 'jinja2'])
            logger.info("Dependencies installed successfully")
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            
    def _ensure_template_dirs(self) -> None:
        """Ensure template directories exist."""
        for template_dir in self.template_dirs:
            if not template_dir.exists():
                try:
                    template_dir.mkdir(parents=True, exist_ok=True)
                    # Create default templates if this is the first run
                    if not any(template_dir.glob("*.jinja")):
                        self._create_default_templates(template_dir)
                except Exception as e:
                    logger.error(f"Failed to create template directory {template_dir}: {e}")
                    
    def _create_default_templates(self, template_dir: Path) -> None:
        """Create default templates if none exist."""
        default_templates = {
            "web_summary_prompt.jinja": """
You are an intelligent summarizer and knowledge extractor.
Here is the raw content from a webpage ({{ url }}):
---
{{ content }}
---
Summarize the key ideas, topics, and actionables.
Return the output in Markdown format with bullet points.
""".strip(),
            
            "chat_summary_prompt.jinja": """
You are analyzing a chat conversation.
Here is the chat history:
---
{{ chat_history }}
---
Extract the main topics, decisions, and action items.
Format the output in Markdown with sections for:
- Key Points
- Decisions Made
- Action Items
- Follow-up Questions
""".strip()
        }
        
        for name, content in default_templates.items():
            template_path = template_dir / name
            try:
                template_path.write_text(content)
                logger.info(f"Created default template: {name}")
            except Exception as e:
                logger.error(f"Failed to create template {name}: {e}")
                
    def render_from_template(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """Render content using a template.
        
        Args:
            template_name: Name of the template file (e.g. "web_summary_prompt.jinja")
            context: Dictionary of variables to pass to the template
            
        Returns:
            Rendered content or None if rendering fails
        """
        try:
            import jinja2
            
            # Find template in available directories
            template_path = None
            for template_dir in self.template_dirs:
                candidate = template_dir / template_name
                if candidate.exists():
                    template_path = candidate
                    break
                    
            if not template_path:
                logger.error(f"Template not found: {template_name}")
                return None
                
            # Create Jinja environment
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader([str(d) for d in self.template_dirs]),
                autoescape=True
            )
            
            # Load and render template
            template = env.get_template(template_name)
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return None
            
    def get_available_templates(self) -> list:
        """Get list of available template names."""
        templates = []
        for template_dir in self.template_dirs:
            if template_dir.exists():
                templates.extend(f.name for f in template_dir.glob("*.jinja"))
        return sorted(templates) 