import os
import logging
import json
from typing import Dict, List, Optional, Union
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from PyQt5.QtCore import QObject, pyqtSignal, QFileSystemWatcher

# Configure logging
logger = logging.getLogger(__name__)

# Define all template category subfolders
TEMPLATE_CATEGORIES = [
    'prompt_templates',
    'message_templates',
    'content',
    'engagement_templates',
    'discord_templates',
    'dreamscape_templates'
]

def get_base_template_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')

def discover_templates() -> List[str]:
    """
    Recursively discover all .j2 templates under known template categories.
    Returns:
        list: List of template paths relative to their category root.
    """
    base_dir = get_base_template_dir()
    discovered = []

    for category in TEMPLATE_CATEGORIES:
        category_path = os.path.join(base_dir, category)
        if not os.path.exists(category_path):
            continue
            
        for root, _, files in os.walk(category_path):
            for file in files:
                if file.endswith('.j2'):
                    rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                    discovered.append(rel_path.replace("\\", "/"))  # Normalize path

    logger.info(f"Discovered {len(discovered)} templates recursively across {len(TEMPLATE_CATEGORIES)} categories")
    return discovered

def load_template(template_rel_path: str):
    """
    Load a Jinja2 template using its relative path from /templates.
    Example: 'dreamscape_templates/dreamscape.j2' or 'prompt_templates/combat/special.j2'
    
    Args:
        template_rel_path: Path relative to templates directory
        
    Returns:
        jinja2.Template or None
    """
    if not template_rel_path.endswith('.j2'):
        logger.warning(f"Invalid template format: {template_rel_path}")
        return None

    base_dir = get_base_template_dir()
    full_path = os.path.join(base_dir, template_rel_path)
    
    if not os.path.isfile(full_path):
        logger.error(f"Template not found: {full_path}")
        return None
    
    try:
        loader_path = os.path.dirname(full_path)
        env = Environment(loader=FileSystemLoader(loader_path))
        template_name = os.path.basename(full_path)
        return env.get_template(template_name)
    except Exception as e:
        logger.error(f"Error loading template {template_rel_path}: {e}")
        return None

# Pre-load global template list
allowed_templates = discover_templates()

class TemplateManager(QObject):
    """
    Manages Jinja2 templates across multiple directories.
    Allows hot-reloading, rendering with context, and integration into GUI.
    """
    templates_updated = pyqtSignal(list)  # Emitted when templates change
    template_modified = pyqtSignal(str)   # Emitted when a template file changes
    render_preview = pyqtSignal(str)      # Emitted when preview should update

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        self.template_dir = template_dir or self.get_default_prompt_dir()
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.active_template = None
        self.allowed_templates = allowed_templates
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._on_template_modified)
        self.load_templates()

    def get_default_prompt_dir(self) -> str:
        """Return default path to /prompt_templates/."""
        return os.path.join(get_base_template_dir(), 'prompt_templates')

    def load_templates(self):
        """Recursively reload templates from the currently active directory."""
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        templates = []
        
        if os.path.exists(self.template_dir):
            for root, _, files in os.walk(self.template_dir):
                for file in files:
                    if file.endswith('.j2'):
                        rel_path = os.path.relpath(os.path.join(root, file), self.template_dir)
                        templates.append(rel_path.replace("\\", "/"))
                        # Add to file watcher
                        full_path = os.path.join(root, file)
                        if full_path not in self.watcher.files():
                            self.watcher.addPath(full_path)
                            
        self.templates_updated.emit(templates)
        logger.info(f"Loaded {len(templates)} templates from {self.template_dir}")

    def get_available_templates(self) -> List[str]:
        """
        Return list of all available template names under the current directory.
        Useful for populating dropdowns in the GUI.
        """
        if not os.path.exists(self.template_dir):
            return []
        
        available = []
        for root, _, files in os.walk(self.template_dir):
            for file in files:
                if file.endswith(".j2"):
                    rel_path = os.path.relpath(os.path.join(root, file), self.template_dir)
                    available.append(rel_path.replace("\\", "/"))
        return available

    def change_template_dir(self, new_dir: str) -> bool:
        """
        Switch to a different template directory.
        Returns:
            bool: True if directory is valid and templates were loaded.
        """
        if not os.path.exists(new_dir):
            logger.error(f"Template directory does not exist: {new_dir}")
            return False
            
        # Remove old watched paths
        for path in self.watcher.files():
            self.watcher.removePath(path)
            
        self.template_dir = new_dir
        self.load_templates()
        logger.info(f"Changed template directory to: {new_dir}")
        return True

    def set_active_template(self, template_name: str):
        """Set the currently selected template to render."""
        if not template_name.endswith('.j2'):
            logger.warning(f"Invalid template name: {template_name} (must end with .j2)")
            return
        self.active_template = template_name
        logger.info(f"Active template set to: {template_name}")

    def render_template(self, context: Optional[Dict] = None) -> Optional[str]:
        """
        Render the active template using the provided context.
        Returns:
            str: Rendered result or None if error.
        """
        if not self.active_template:
            logger.error("No active template selected.")
            return None

        try:
            template = self.env.get_template(self.active_template)
            rendered = template.render(context or {})
            self.render_preview.emit(rendered)  # Emit preview signal
            return rendered
        except TemplateNotFound:
            logger.error(f"Template not found: {self.active_template}")
            return None
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return None

    def save_rendered_output(self, rendered_text: str, output_path: str, format: str = 'txt') -> bool:
        """
        Save rendered template output to a file.
        
        Args:
            rendered_text: The rendered template text
            output_path: Path to save the file
            format: Output format ('txt' or 'md')
            
        Returns:
            bool: True if saved successfully
        """
        try:
            ext = '.md' if format == 'md' else '.txt'
            if not output_path.endswith(ext):
                output_path += ext
                
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_text)
            logger.info(f"Saved rendered output to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving rendered output: {e}")
            return False

    def validate_context(self, template_name: str, context: Dict) -> List[str]:
        """
        Check for missing or undefined variables in a template given a context.
        
        Args:
            template_name: Name of template to validate
            context: Context dictionary to validate against
            
        Returns:
            list: List of missing variable names
        """
        try:
            template = self.env.get_template(template_name)
            undefined = []
            
            # Parse template AST to find variables
            ast = template.environment.parse(template.source)
            
            def visit_node(node):
                if hasattr(node, 'name'):
                    if node.name not in context and node.name not in ['loop', 'self']:
                        undefined.append(node.name)
                for child in node.iter_child_nodes():
                    visit_node(child)
                    
            visit_node(ast)
            return list(set(undefined))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error validating template context: {e}")
            return []

    def _on_template_modified(self, path: str):
        """Handle template file modifications for hot-reloading."""
        logger.info(f"Template modified: {path}")
        self.template_modified.emit(path)
        
        # If this is the active template, re-render preview
        if self.active_template:
            rel_path = os.path.relpath(path, self.template_dir).replace("\\", "/")
            if rel_path == self.active_template:
                self.render_template()  # Re-render with current context
