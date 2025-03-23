import os
import json
import logging
import time
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from chat_mate_config import Config

logger = logging.getLogger("DiscordTemplateManager")
logging.basicConfig(level=logging.INFO)


class DiscordTemplateManager:
    """
    Manages Discord templates using Jinja2.
    
    Template directory resolution order:
    1. Environment variable DISCORD_TEMPLATE_DIR
    2. JSON config file path
    3. Centralized fallback (chat_mate_config.py)
    """

    def __init__(self, config_file: str = None, template_extension: str = ".j2"):
        self.template_extension = template_extension
        self.config_file = os.path.abspath(config_file) if config_file else Config.DEFAULT_CONFIG_FILE
        self.template_dir = self._resolve_template_dir(self.config_file)

        if not os.path.isdir(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            logger.info(f" Created template directory at: {self.template_dir}")

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        logger.info(f" DiscordTemplateManager initialized. Template directory: {self.template_dir}")

    def _resolve_template_dir(self, config_file: str) -> str:
        """
        Resolves the template directory from env, config, or fallback.
        """
        # 1. Environment variable override
        env_path = os.getenv("DISCORD_TEMPLATE_DIR")
        if env_path and os.path.isdir(env_path):
            logger.info(f" Loaded template dir from environment: {env_path}")
            return env_path

        # 2. JSON config lookup
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)

                json_path = cfg_data.get("discord_templates_dir")
                if json_path and os.path.isdir(json_path):
                    logger.info(f"️ Loaded template dir from config: {json_path}")
                    return json_path
                else:
                    logger.warning(f"️ 'discord_templates_dir' not found or invalid in {config_file}.")
            except Exception as e:
                logger.error(f" Failed to parse {config_file}: {e}")

        # 3. Fallback to centralized config
        fallback_dir = Config.DISCORD_TEMPLATE_DIR
        logger.warning(f"️ Falling back to centralized template dir: {fallback_dir}")
        return fallback_dir

    def render_message(self, template_name: str, context: dict) -> str:
        """
        Renders a message from the specified template with the provided context.
        Measures render time and logs performance.
        """
        template_file = f"{template_name}{self.template_extension}"
        start_time = time.time()

        try:
            template = self.env.get_template(template_file)
            message = template.render(context)
            render_time = round((time.time() - start_time), 3)

            logger.info(f" Rendered template '{template_file}' in {render_time}s.")

            if render_time > 1.0:
                logger.warning(f"️ Rendering '{template_file}' took {render_time}s. Consider optimizing the template.")

            return message

        except TemplateNotFound:
            logger.error(f" Template '{template_file}' not found in {self.template_dir}.")
            return f"⚠️ Template '{template_name}' not found."

        except Exception as e:
            logger.error(f" Error rendering '{template_file}': {e}")
            return f"⚠️ Error rendering template '{template_name}': {e}"

    def list_templates(self) -> list:
        """
        Lists available templates in the template directory.
        """
        try:
            templates = [
                f for f in os.listdir(self.template_dir)
                if f.endswith(self.template_extension)
            ]
            logger.info(f" Available templates: {templates}")
            return templates

        except Exception as e:
            logger.error(f" Error listing templates: {e}")
            return []
