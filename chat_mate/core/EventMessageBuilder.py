import os
import json
import logging
import threading
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError, select_autoescape
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging for the module
logger = logging.getLogger("EventMessageBuilder")
logging.basicConfig(level=logging.INFO)


class TemplateChangeHandler(FileSystemEventHandler):
    """
    Watches the template directory for changes. When a template file is modified,
    created, or deleted, it will trigger a cache clear in the EventMessageBuilder.
    """
    def __init__(self, event_builder):
        self.event_builder = event_builder

    def on_modified(self, event):
        if event.src_path.endswith(self.event_builder.template_extension):
            logger.info(f" Template modified: {event.src_path}")
            self.event_builder.clear_cache()

    def on_created(self, event):
        if event.src_path.endswith(self.event_builder.template_extension):
            logger.info(f" New template created: {event.src_path}")
            self.event_builder.clear_cache()

    def on_deleted(self, event):
        if event.src_path.endswith(self.event_builder.template_extension):
            logger.info(f" Template deleted: {event.src_path}")
            self.event_builder.clear_cache()


class EventMessageBuilder:
    """
    Builds Discord messages using Jinja2 templates for various event types.
    Place your templates (e.g., quest_complete.j2, protocol_unlock.j2, tier_up.j2)
    in your designated template directory.
    
    If no template directory is provided, the default location is:
      ../templates/message_templates relative to this file.
      
    This builder will automatically watch for changes in the template directory
    and clear its cache accordingly.
    """
    def __init__(self, template_dir: str = None, template_extension: str = ".j2"):
        # Determine default template directory relative to this file if not provided.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_template_dir = os.path.join(base_dir, "..", "templates", "message_templates")
        self.template_dir = os.path.abspath(template_dir) if template_dir else os.path.abspath(default_template_dir)
        self.template_extension = template_extension
        self.template_cache = {}

        if not os.path.isdir(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            logger.info(f" Created template directory at '{self.template_dir}'")

        # Initialize the Jinja2 environment with autoescaping for html and xml.
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        logger.info(f" EventMessageBuilder initialized. Template directory: {repr(self.template_dir)}")

        # Start the template directory watcher.
        self._start_template_watcher()

    def _start_template_watcher(self):
        """Start a watchdog observer to monitor the template directory for changes."""
        event_handler = TemplateChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path=self.template_dir, recursive=False)
        observer_thread = threading.Thread(target=observer.start, daemon=True)
        observer_thread.start()
        logger.info(f" Watching template directory for changes: {self.template_dir}")

    def build_message(self, event_type: str, data: dict) -> str:
        """
        Build a message for the given event type by rendering the corresponding template.
        
        :param event_type: The type of event (e.g., "quest_complete").
        :param data: A dictionary with data to pass to the template.
        :return: The rendered message as a string.
        """
        if not isinstance(data, dict) or not data:
            logger.warning(f"️ Event data for '{event_type}' is empty or invalid. Using empty dict.")
            data = {}

        template_name = f"{event_type}{self.template_extension}"
        try:
            # Attempt to use cached template first.
            if template_name in self.template_cache:
                template = self.template_cache[template_name]
                logger.debug(f" Loaded template for '{event_type}' from cache")
            else:
                template = self.env.get_template(template_name)
                self.template_cache[template_name] = template
                logger.info(f" Loaded and cached template: '{template_name}'")
            message = template.render(data)
            logger.info(f" Successfully built message for event '{event_type}'")
            return message
        except TemplateNotFound:
            logger.error(f" Template '{template_name}' not found in '{self.template_dir}'")
        except TemplateError as e:
            logger.error(f" Template error in '{template_name}': {e}")
        except Exception as e:
            logger.error(f" Unexpected error rendering '{template_name}': {e}")

        # Fallback message if template rendering fails.
        fallback_msg = (
            f"📢 **{event_type.replace('_', ' ').title()}**\n"
            f"```json\n{json.dumps(data, indent=2)}```"
        )
        logger.warning(f"️ Using fallback message for event '{event_type}'")
        return fallback_msg

    def list_available_templates(self) -> list:
        """
        List all available templates in the template directory.
        
        :return: A list of template file names.
        """
        try:
            files = os.listdir(self.template_dir)
            templates = [f for f in files if f.endswith(self.template_extension)]
            logger.info(f" Found {len(templates)} available templates.")
            return templates
        except Exception as e:
            logger.error(f" Failed to list templates: {e}")
            return []

    def clear_cache(self) -> None:
        """
        Clear the cached templates. This is typically called when a template file is modified,
        created, or deleted.
        """
        self.template_cache.clear()
        logger.info("️ Cleared template cache due to template change.")


# Example Usage:
if __name__ == "__main__":
    builder = EventMessageBuilder()

    event_data = {
        "user": "Victor",
        "quest_name": "The Dawn Protocol",
        "reward": "Unlocks Tier 2 Execution Velocity"
    }

    # Build and print a message for the 'quest_complete' event.
    message = builder.build_message("quest_complete", event_data)
    print(message)

    # List and print available templates.
    templates = builder.list_available_templates()
    print(f"Available templates: {templates}")
