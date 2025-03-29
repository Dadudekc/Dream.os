import os
import json
import logging
import time
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

# Use whichever approach you prefer (Option A: Singleton)
from config.config_singleton import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DiscordTemplateManager:
    """
    Manages Discord templates using Jinja2.

    Template directory resolution order:
    1. Environment variable DISCORD_TEMPLATE_DIR
    2. New config system key: discord.template_dir
    3. Hard-coded fallback: "templates/discord"
    """

    def __init__(self, template_extension: str = ".j2"):
        self.template_extension = template_extension

        # Resolve the directory
        self.template_dir = self._resolve_template_dir()

        # Ensure directory exists
        os.makedirs(self.template_dir, exist_ok=True)
        logger.info(f"DiscordTemplateManager: Using template directory: {self.template_dir}")

        # Initialize Jinja environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"])
        )

    def _resolve_template_dir(self) -> str:
        """
        Resolves the template directory from env, new config, or fallback.
        """
        # 1. Environment variable
        env_dir = os.getenv("DISCORD_TEMPLATE_DIR")
        if env_dir and os.path.isdir(env_dir):
            logger.info(f"DiscordTemplateManager: Loaded template dir from environment: {env_dir}")
            return env_dir

        # 2. Config system key: "discord.template_dir"
        cfg_dir = config.get("discord.template_dir", default="templates/discord")
        if os.path.isdir(cfg_dir):
            logger.info(f"DiscordTemplateManager: Loaded template dir from config: {cfg_dir}")
            return cfg_dir

        # 3. Hard-coded fallback
        fallback = "templates/discord"
        logger.warning(f"DiscordTemplateManager: Fallback to: {fallback}")
        return fallback

    def render_message(self, template_name: str, context: dict) -> str:
        """
        Render a message from the specified template with the provided context.
        Measures render time and logs performance.
        """
        template_file = f"{template_name}{self.template_extension}"
        start_time = time.time()

        try:
            template = self.env.get_template(template_file)
            message = template.render(context)
            render_time = round((time.time() - start_time), 3)

            logger.info(f"Rendered template '{template_file}' in {render_time}s.")
            if render_time > 1.0:
                logger.warning(f"Rendering '{template_file}' took {render_time}s. Consider optimizing.")

            return message

        except TemplateNotFound:
            logger.error(f"Template '{template_file}' not found in {self.template_dir}.")
            return f"⚠️ Template '{template_name}' not found."
        except Exception as e:
            logger.error(f"Error rendering '{template_file}': {e}")
            return f"⚠️ Error rendering template '{template_name}': {e}"

    def list_templates(self) -> list:
        """
        Lists available templates in the template directory.
        """
        try:
            return [
                f for f in os.listdir(self.template_dir)
                if f.endswith(self.template_extension)
            ]
        except Exception as e:
            logger.error(f"Error listing templates in {self.template_dir}: {e}")
            return []
