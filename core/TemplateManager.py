from typing import Dict, Any, List, Optional, Union
import os
import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from PyQt5.QtCore import QObject, pyqtSignal, QFileSystemWatcher

# Optional imports from your project
try:
    from core.PathManager import PathManager
except ImportError:
    PathManager = None
try:
    from social.log_writer import write_json_log
except ImportError:
    def write_json_log(platform, result, tags, ai_output): 
        pass

class TemplateManager(QObject):
    """
    Centralized manager for Jinja2 templates across multiple categories.
    Provides hot-reloading, multi-environment support, context validation, and integration into a GUI.
    
    Features:
      - Auto-loads environments for each template category.
      - Supports dynamic directory switching and recursive template discovery.
      - Emits signals on template updates, modifications, and render previews.
      - Logs template activity for analytics.
    """
    # PyQt signals for integration and hot-reload feedback.
    templates_updated = pyqtSignal(list)  # Emitted when templates change
    template_modified = pyqtSignal(str)   # Emitted when a template file changes
    render_preview = pyqtSignal(str)      # Emitted when preview should update

    # Define default template categories
    TEMPLATE_CATEGORIES = {
        "discord": None,
        "messages": None,
        "general": None
    }

    def __init__(self, template_dir: Optional[str] = None, default_data: Optional[Dict] = None, logger: Optional[logging.Logger] = None, path_manager: Optional[PathManager] = None):
        """
        Initialize the TemplateManager.
        
        Args:
            template_dir (Optional[str]): Override for the 'general' templates directory.
            default_data (Optional[Dict]): Data to inject into all templates by default.
            logger (Optional[logging.Logger]): Logger instance.
            path_manager (Optional[PathManager]): Pre-initialized PathManager instance.
        """
        super().__init__()

        # Set logger
        self.logger = logger or logging.getLogger(__name__)

        # Set default data
        self.default_data = default_data or {}

        # Use provided PathManager or initialize one if PathManager class is available
        self.path_manager = path_manager
        if self.path_manager is None and PathManager:
            try:
                self.path_manager = PathManager()
            except Exception as e:
                 self.logger.warning(f"Could not initialize internal PathManager: {e}")
                 self.path_manager = None # Ensure it's None if init fails

        # Determine general template directory
        if template_dir:
            general_dir = str(Path(template_dir))
        elif self.path_manager:
            try:
                 general_dir = self.path_manager.get_path('templates')
            except KeyError:
                 self.logger.warning("'templates' key not found in PathManager, using fallback.")
                 general_dir = str(self.get_base_template_dir())
        else:
            general_dir = str(self.get_base_template_dir())

        # Setup directories for each category using the instance self.path_manager
        self.template_categories = {
            "discord": str(self.path_manager.get_path('discord_templates')) if self.path_manager else os.path.join(general_dir, "discord_templates"),
            "messages": str(self.path_manager.get_path('message_templates')) if self.path_manager else os.path.join(general_dir, "message_templates"),
            "dreamscape": str(self.path_manager.get_path('dreamscape_templates')) if self.path_manager else os.path.join(general_dir, "dreamscape_templates"),
            "general": general_dir
        }
        # Ensure all template directories exist
        for category, path in self.template_categories.items():
            os.makedirs(path, exist_ok=True)
            self.logger.info(f"Ensuring template directory exists for {category}: {path}")

        # Initialize Jinja2 environments for each category.
        self.environments: Dict[str, Environment] = {
            category: self._init_environment(path)
            for category, path in self.template_categories.items()
        }

        # Active template (for general category by default)
        self.active_template: Optional[str] = None

        # Initialize the templates dictionary BEFORE loading templates to avoid attribute errors.
        self.templates: Dict[str, str] = {}

        # Initialize a file system watcher for hot reloading.
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._on_template_modified)

        # Discover and load available templates from the general directory.
        self.load_templates()

    def get_base_template_dir(self) -> str:
        """
        Fallback method to determine base template directory.
        """
        return os.path.join(os.getcwd(), "templates")

    def _init_environment(self, path: str) -> Environment:
        """
        Creates a Jinja2 Environment for a given directory.
        Adds custom filters for JSON handling.
        """
        env = Environment(
            loader=FileSystemLoader(path),
            autoescape=select_autoescape()
        )

        # Add JSON filters
        def load_json_filter(path):
            """Load and parse a JSON file."""
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading JSON from {path}: {e}")
                return {}

        def tojson_filter(value):
            """Convert a value to a JSON string."""
            try:
                return json.dumps(value, indent=2)
            except Exception as e:
                self.logger.error(f"Error converting to JSON: {e}")
                return str(value)

        env.filters['load_json'] = load_json_filter
        env.filters['tojson'] = tojson_filter

        return env

    def discover_templates(self) -> List[str]:
        """
        Recursively discovers all templates under the 'general' template directory.
        
        Returns:
            List[str]: List of template paths relative to the base directory.
        """
        base_dir = self.template_categories.get("general", self.get_base_template_dir())
        discovered = []
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.j2') or file.endswith('.jinja'):
                    rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                    discovered.append(rel_path.replace("\\", "/"))
        self.logger.info(f"Discovered {len(discovered)} templates under 'general'")
        return discovered

    def load_templates(self, template_dir: Union[str, Path] = None):
        """
        Reloads templates from the provided directory (or the 'general' template directory if not specified),
        adds them to the file watcher, and emits the updated list.
        
        Args:
            template_dir (Union[str, Path]): Directory to load templates from. If None, uses the 'general' directory.
        """
        template_dir = Path(template_dir) if template_dir else Path(self.template_categories.get("general", self.get_base_template_dir()))
        self.logger.info(f"Loading templates from: {template_dir}")
        if not template_dir.exists():
            self.logger.warning(f"Template directory does not exist: {template_dir}")
            return

        # Find both .j2 and .jinja templates
        templates = []
        for ext in [".j2", ".jinja"]:
            templates.extend(list(template_dir.glob(f"*{ext}")))
            
        self.logger.info(f"Found {len(templates)} template(s): {[t.name for t in templates]}")
        for template_file in templates:
            with open(template_file, 'r', encoding='utf-8') as f:
                self.templates[template_file.name] = f.read()

        self.templates_updated.emit([str(t.relative_to(template_dir)) for t in templates])
        self.logger.info(f"Loaded {len(templates)} templates from {template_dir}")

    def get_available_templates(self, category: str = "general", model_key: Optional[str] = None) -> List[str]:
        """
        Returns a sorted list of available template filenames for a given category,
        optionally filtered by model key.
        
        Args:
            category (str): Template category to search in
            model_key (Optional[str]): If provided, only return templates compatible with this model
            
        Returns:
            List[str]: List of template filenames
        """
        path = self.template_categories.get(category)
        if not path or not os.path.isdir(str(path)):
            self.logger.warning(f"No valid directory found for template category: {category} at path: {path}")
            return []
            
        available = []
        for root, _, files in os.walk(str(path)):
            for file in files:
                if not (file.endswith(".j2") or file.endswith(".jinja")):
                    continue
                    
                # If model_key is provided, check if template is compatible
                if model_key:
                    # Check for model-specific template (e.g. template.gpt-4o.jinja)
                    if model_key in file:
                        rel_path = os.path.relpath(os.path.join(root, file), str(path))
                        available.append(rel_path.replace("\\", "/"))
                    # Also include default templates that don't specify a model
                    elif not any(model in file for model in [
                        "gpt-4o", "gpt-4o-mini", "gpt-4o-scheduled",
                        "gpt-4.5", "gpt-4", "o1", "o3-mini", "o3-mini-high"
                    ]):
                        rel_path = os.path.relpath(os.path.join(root, file), str(path))
                        available.append(rel_path.replace("\\", "/"))
                else:
                    rel_path = os.path.relpath(os.path.join(root, file), str(path))
                    available.append(rel_path.replace("\\", "/"))
                    
        return sorted(available)

    def change_template_dir(self, category: str, new_dir: str) -> bool:
        """
        Switches to a different directory for a specific template category.
        
        Args:
            category (str): The template category to change.
            new_dir (str): New directory path.
            
        Returns:
            bool: True if directory is valid and templates reloaded; False otherwise.
        """
        if not os.path.exists(new_dir):
            self.logger.error(f"Template directory does not exist: {new_dir}")
            return False
        # Remove watched files from old directory
        for path in self.watcher.files():
            self.watcher.removePath(path)
        self.template_categories[category] = new_dir
        self.environments[category] = self._init_environment(new_dir)
        self.load_templates()
        self.logger.info(f"Changed {category} template directory to: {new_dir}")
        return True

    def load_template(self, template_rel_path: str, category: str = "general"):
        """
        Loads a Jinja2 template from a relative path under a given category.
        
        Args:
            template_rel_path (str): Relative path (e.g., 'my_episode.j2' or 'my_episode.jinja').
            category (str): Template category.
            
        Returns:
            jinja2.Template or None if not found.
        """
        if not (template_rel_path.endswith('.j2') or template_rel_path.endswith('.jinja')):
            self.logger.warning(f"Invalid template format: {template_rel_path}")
            return None

        try:
            template = self.environments[category].get_template(template_rel_path)
            return template
        except TemplateNotFound:
            self.logger.error(f"Template not found: {template_rel_path} in category {category}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading template {template_rel_path}: {e}")
            return None

    def set_active_template(self, template_name: str, category: str = "general"):
        """
        Sets the currently active template for rendering.
        
        Args:
            template_name (str): Filename of the template (must end with .j2).
            category (str): Category to search in.
            
        Raises:
            TemplateNotFound: If the template is not available.
        """
        available = self.get_available_templates(category)
        if template_name in available:
            self.active_template = template_name
            self.logger.info(f"Active template set to: {template_name} (Category: {category})")
        else:
            error_msg = f"Template '{template_name}' not found in category '{category}'."
            self.logger.error(error_msg)
            raise TemplateNotFound(error_msg)

    def render(self, category: str, template_filename: str, data: Dict) -> str:
        """
        Generic renderer for a template in a given category.
        
        Args:
            category (str): Template category.
            template_filename (str): Template filename.
            data (Dict): Data to inject.
            
        Returns:
            str: Rendered template output, or error message on failure.
        """
        if category not in self.environments:
            error_msg = f"Unknown template category: {category}"
            self.logger.error(error_msg)
            return error_msg

        merged_data = {**self.default_data, **data}

        try:
            template = self.environments[category].get_template(template_filename)
            rendered = template.render(**merged_data)
            self._log_template_render(category, template_filename, merged_data)
            self.render_preview.emit(rendered)
            return rendered
        except TemplateNotFound:
            error_msg = f"Template '{template_filename}' not found in category '{category}'."
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error rendering template '{template_filename}': {e}"
            self.logger.error(error_msg)
            return error_msg

    def render_discord_template(self, template_filename: str, data: Dict) -> str:
        """Convenience method to render a Discord template."""
        return self.render("discord", template_filename, data)

    def render_message_template(self, template_filename: str, data: Dict) -> str:
        """Convenience method to render a message/engagement template."""
        return self.render("messages", template_filename, data)

    def render_general_template(self, template_name: str, data: Dict[str, Any], category: str = "general") -> str:
        """
        Renders a template from the specified category using the provided data.
        Merges default data with provided data.
        
        Args:
            template_name (str): Name of the template file (e.g., 'my_template.j2')
            data (Dict[str, Any]): Dictionary of data for template context.
            category (str): The category environment to use (default: "general").
            
        Returns:
            str: Rendered template output, or error message on failure.
        """
        
        # Select the correct environment based on category
        env = self.environments.get(category)
        if not env:
            self.logger.error(f"Template category '{category}' not found.")
            return f"Error: Template category '{category}' not found."
        
        # Merge default data with provided data
        context = {**self.default_data, **data}

        try:
            template = env.get_template(template_name)
            rendered = template.render(context)
            self.logger.info(f"Successfully rendered template '{template_name}' from category '{category}'.")
            return rendered
        except TemplateNotFound:
            self.logger.error(f"Template '{template_name}' not found in category '{category}'.")
            return f"Template '{template_name}' not found in category '{category}'."
        except Exception as e:
            self.logger.error(f"Error rendering template '{template_name}' from category '{category}': {e}")
            return f"Error rendering template '{template_name}': {e}"

    def render_template(self, context: Dict) -> str:
        """
        Renders the currently active general template using provided context.
        
        Args:
            context (Dict): Data for rendering.
            
        Returns:
            str: Rendered output or an error message.
        """
        if not self.active_template:
            error_msg = "No active template is set."
            self.logger.error(error_msg)
            return error_msg
        return self.render("general", self.active_template, context)

    def validate_context(self, template_name: str, context: Dict) -> List[str]:
        """
        Checks for missing variables in a template given a context.
        
        Args:
            template_name (str): Template filename.
            context (Dict): Context to validate.
            
        Returns:
            List[str]: List of missing variable names.
        """
        try:
            template = self.environments["general"].get_template(template_name)
            undefined = []
            ast = template.environment.parse(template.source)

            def visit_node(node):
                if hasattr(node, 'name'):
                    if node.name not in context and node.name not in ['loop', 'self']:
                        undefined.append(node.name)
                for child in node.iter_child_nodes():
                    visit_node(child)

            visit_node(ast)
            return list(set(undefined))
        except Exception as e:
            self.logger.error(f"Error validating template context: {e}")
            return []

    def save_rendered_output(self, rendered_text: str, output_path: str, format: str = 'txt') -> bool:
        """
        Saves rendered template output to a file.
        
        Args:
            rendered_text (str): Text to save.
            output_path (str): Output file path.
            format (str): File extension ('txt' or 'md').
            
        Returns:
            bool: True if saved successfully, else False.
        """
        try:
            ext = '.md' if format == 'md' else '.txt'
            if not output_path.endswith(ext):
                output_path += ext
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_text)
            self.logger.info(f"Saved rendered output to: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving rendered output: {e}")
            return False

    def _log_template_render(self, category: str, template_filename: str, data: Dict):
        """
        Logs successful template rendering activity.
        """
        log_data = {
            "category": category,
            "template": template_filename,
            "data": data
        }
        self.logger.info(f"Template rendered: {category}/{template_filename}")
        write_json_log(
            platform="TemplateManager",
            result="success",
            tags=["template_render", category],
            ai_output=log_data
        )

    def _on_template_modified(self, path: str):
        """
        Slot to handle a modified template file for hot-reloading.
        """
        self.logger.info(f"Template modified: {path}")
        self.template_modified.emit(path)
        # If the modified file is the active template, re-render preview.
        base_dir = self.template_categories.get("general", self.get_base_template_dir())
        rel_path = os.path.relpath(path, base_dir).replace("\\", "/")
        if self.active_template and rel_path == self.active_template:
            self.render_template({})

    def get_template_content(self, template_name: str, category: str = "general") -> Optional[str]:
        """Get the raw content of a template.
        
        Args:
            template_name: Name of the template file
            category: Template category to search in
            
        Returns:
            Raw template content as string, or None if not found
        """
        try:
            template_path = Path(self.template_categories[category]) / template_name
            if template_path.exists():
                return template_path.read_text(encoding='utf-8')
            self.logger.warning(f"Template not found: {template_name} in category {category}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading template {template_name}: {e}")
            return None
