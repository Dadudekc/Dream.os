import logging
import json
import os
from pathlib import Path
from jinja2 import Template

# Import your CursorDispatcher (adjust the path as necessary)
from core.refactor.cursor_dispatcher import CursorDispatcher


class ElephantBuilderService:
    """
    ElephantBuilderService is responsible for automating the creation of new modules based
    on a specification and a Jinja template. It reads module definitions from a spec file
    and renders prompts to generate production-ready code via the CursorDispatcher.
    """

    def __init__(self, path_manager, template_manager, openai_client, spec_path: Path, template_base_path: Path):
        """
        Initialize the ElephantBuilderService.

        :param path_manager: Provides consistent path references (e.g., project_root, config, etc.).
        :param template_manager: An instance responsible for template operations (if needed).
        :param openai_client: An OpenAIClient instance used for dispatching prompts if required.
        :param spec_path: Path to the ElephantSpec.json file.
        :param template_base_path: Base directory for elephant-related templates.
        """
        self.path_manager = path_manager
        self.template_manager = template_manager
        self.openai_client = openai_client
        self.spec_path = spec_path
        self.template_base_path = template_base_path
        self.logger = logging.getLogger(self.__class__.__name__)
        # Initialize a CursorDispatcher instance for prompt execution.
        self.cursor_dispatcher = CursorDispatcher()

    def build_single_module(self, module_name: str, module_goal: str):
        """
        Build a single module using the 'build_module.jinja' template.
        
        :param module_name: The name of the module to generate.
        :param module_goal: A short description of the module's purpose.
        """
        try:
            template_path = self.template_base_path / "build_module.jinja"
            if not template_path.exists():
                self.logger.error(f"Template file not found at {template_path}")
                return

            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Render the template with the provided context.
            template = Template(template_content)
            target_dir = self.path_manager.get_path("project_root") / "projects" / "neural_sovereign" / module_name
            context = {
                "module_name": module_name,
                "module_goal": module_goal,
                "target_dir": str(target_dir)
            }
            prompt = template.render(**context)
            self.logger.info(f"Dispatching build prompt for module '{module_name}'.")

            # Execute the prompt using CursorDispatcher. Alternatively, openai_client can be used.
            result = self.cursor_dispatcher.execute_prompt(prompt)
            self.logger.info(f"Module '{module_name}' built successfully. Result: {result}")

        except Exception as e:
            self.logger.error(f"Error building module '{module_name}': {e}", exc_info=True)

    def build_from_spec(self):
        """
        Load the ElephantSpec.json file and build each module defined in it.
        
        The spec is expected to be a JSON object with keys:
          - project_name: Name of the overarching project.
          - vision: A high-level description of the project's purpose.
          - modules: A list of module definitions, each containing:
              - name: Module name.
              - goal: Module goal/description.
              - (Optional) type: Module type identifier.
        """
        try:
            if not self.spec_path.exists():
                self.logger.error(f"Spec file not found at {self.spec_path}")
                return

            with open(self.spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)

            modules = spec.get("modules", [])
            if not modules:
                self.logger.warning("No modules found in ElephantSpec.json")
                return

            self.logger.info(f"Found {len(modules)} modules in spec. Beginning module build process.")
            for module in modules:
                module_name = module.get("name")
                module_goal = module.get("goal")
                if module_name and module_goal:
                    self.logger.info(f"Building module '{module_name}' from spec.")
                    self.build_single_module(module_name, module_goal)
                else:
                    self.logger.warning(f"Invalid module definition in spec: {module}")

        except Exception as e:
            self.logger.error(f"Error building modules from spec: {e}", exc_info=True)
