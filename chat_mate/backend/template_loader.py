import os
import logging
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from PyQt5.QtCore import QObject, pyqtSignal

# Configure logging
logger = logging.getLogger(__name__)

# List of allowed templates (populated by discover_templates)
allowed_templates = []

def discover_templates():
    """Discover all available templates by scanning template directories."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dirs = [
        os.path.join(base_dir, 'templates', 'prompt_templates'),
        os.path.join(base_dir, 'templates', 'message_templates'),
        os.path.join(base_dir, 'templates', 'content'),
        os.path.join(base_dir, 'templates', 'engagement_templates'),
        os.path.join(base_dir, 'templates', 'discord_templates')
    ]
    
    discovered_templates = []
    for dir_path in template_dirs:
        if os.path.exists(dir_path):
            discovered_templates.extend([
                t for t in os.listdir(dir_path) if t.endswith('.j2')
            ])
            
    logger.info(f" Discovered {len(discovered_templates)} templates across {len(template_dirs)} directories")
    return discovered_templates

# Populate allowed_templates at module initialization
allowed_templates = discover_templates()

class TemplateManager(QObject):
    """
    Manager for Jinja2 templates with dynamic template loading and hot-reload capabilities.
    Handles loading, rendering, and managing templates from multiple directories.
    """
    templates_updated = pyqtSignal(list)  # Signal to update GUI

    def __init__(self, template_dir=None):
        super().__init__()
        self.template_dir = template_dir or self.get_template_dir()
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.active_template = None
        self.allowed_templates = allowed_templates
        self.load_templates()

    def get_template_dir(self):
        """Return the absolute path to the default template directory."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'templates', 'prompt_templates')
        
    def _discover_templates(self):
        """Discover all available templates by scanning template directories."""
        return allowed_templates

    def load_templates(self):
        """Load available templates from the current template directory."""
        self.env = Environment(loader=FileSystemLoader(self.template_dir))  # Reset Jinja2 env
        
        available_templates = []
        if os.path.exists(self.template_dir):
            available_templates = [t for t in os.listdir(self.template_dir) if t.endswith('.j2')]
            
        logger.info(f" Loaded {len(available_templates)} templates from {self.template_dir}")
        self.templates_updated.emit(available_templates)  # Signal GUI update

    def set_active_template(self, template_name):
        """Set the active template."""
        if template_name.endswith('.j2'):
            self.active_template = template_name
            logger.info(f" Active template set: {template_name}")
        else:
            logger.warning(f" Invalid template format: {template_name} - Must be a .j2 file")

    def render_template(self, context=None):
        """
        Render the active template with the provided context.
        
        Args:
            context (dict): Context variables for the template
            
        Returns:
            str: Rendered template or None if error occurs
        """
        if not self.active_template:
            logger.error(" No active template selected.")
            return None

        try:
            template = self.env.get_template(self.active_template)
            return template.render(context or {})
        except TemplateNotFound:
            logger.error(f" Template not found: {self.active_template}")
            return None
        except Exception as e:
            logger.error(f" Error rendering {self.active_template}: {e}")
            return None
            
    def change_template_dir(self, new_dir):
        """
        Change the template directory.
        
        Args:
            new_dir (str): Path to the new template directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(new_dir):
            logger.error(f" Template directory does not exist: {new_dir}")
            return False
            
        self.template_dir = new_dir
        self.load_templates()
        logger.info(f" Changed template directory to: {new_dir}")
        return True

def load_template(template_name):
    """
    Load a template by name.
    
    Args:
        template_name (str): Name of the template to load
        
    Returns:
        jinja2.Template: The template object if found, None otherwise
    """
    if not template_name.endswith('.j2'):
        logger.warning(f" Invalid template format: {template_name} - Must be a .j2 file")
        return None
        
    # Find the template in available directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dirs = [
        os.path.join(base_dir, 'templates', 'prompt_templates'),
        os.path.join(base_dir, 'templates', 'message_templates'),
        os.path.join(base_dir, 'templates', 'content'),
        os.path.join(base_dir, 'templates', 'engagement_templates'),
        os.path.join(base_dir, 'templates', 'discord_templates')
    ]
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir) and template_name in os.listdir(template_dir):
            try:
                env = Environment(loader=FileSystemLoader(template_dir))
                template = env.get_template(template_name)
                logger.info(f" Successfully loaded template: {template_name} from {template_dir}")
                return template
            except TemplateNotFound:
                continue
            except Exception as e:
                logger.error(f" Error loading {template_name}: {e}")
                continue
    
    logger.error(f" Template not found in any directory: {template_name}")
    return None
