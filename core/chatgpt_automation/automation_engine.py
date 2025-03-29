import os
import shutil
import logging
import json
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import Qt  # For splash screen messages
from typing import Optional
import threading
import queue
import time

# External project-specific imports (ensure these are configured correctly)
from core.chatgpt_automation.config import PROFILE_DIR, CHATGPT_HEADLESS, CHROMEDRIVER_PATH
from core.chatgpt_automation.ModelRegistry import ModelRegistry  # Central model registry
from ProjectScanner import ProjectScanner
from core.chatgpt_automation.OpenAIClient import OpenAIClient   # ChatGPT driver wrapper
from core.chatgpt_automation.local_llm_engine import LocalLLMEngine
from core.chatgpt_automation.driver_factory import DriverFactory

# ------------------------------
# Logger Setup (UTF-8 logging)
# ------------------------------
log_file = "automation_engine.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------
# Constants: Directory Paths
# ------------------------------
DEPLOY_FOLDER = Path("deployed")
BACKUP_FOLDER = Path("backups")
DEPLOY_FOLDER.mkdir(exist_ok=True)
BACKUP_FOLDER.mkdir(exist_ok=True)

# ------------------------------
# Automation Engine Class
# ------------------------------
class AutomationEngine:
    def __init__(self, use_local_llm=True, model_name='mistral', splash_screen=None, beta_mode=False):
        """Initialize the automation engine with optional local LLM support."""
        self.logger = logging.getLogger(__name__)
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self.splash_screen = splash_screen
        self.beta_mode = beta_mode
        self.project_analysis = {}  # Initialize as empty
        
        # Initialize driver
        self.driver = None
        self.driver_factory = DriverFactory(use_local_llm=self.use_local_llm, model_name=self.model_name)
        
        # Initialize model registry
        self.model_registry = ModelRegistry()
        
        # Initialize components
        self.initialize_components()
        
        # Initialize project analysis as empty
        self.project_analysis = {}
        
        self.logger.info("✅ AutomationEngine initialized successfully")
        
    def initialize_components(self):
        """Initialize core components of the automation engine."""
        try:
            # Initialize driver if needed
            if not self.driver:
                self.driver = self.driver_factory.create_driver()
            
            # Configure model registry with specific model configurations
            # NOTE: The registry auto-loads models from the models_dir, but we can supplement
            # with manual configurations for local models if needed
            if self.use_local_llm:
                # The driver factory has already set up a local LLM driver
                # We can add a manual entry for the currently active local model
                logger.info(f"🔧 Setting up local model: {self.model_name}")
                
                # Create a model module file in the registry's models directory if needed
                local_model_file = self.model_registry.models_dir / f"model_{self.model_name}.py"
                if not local_model_file.exists():
                    with open(local_model_file, "w", encoding="utf-8") as f:
                        f.write(f'''
def register():
    """Register the {self.model_name} model."""
    return {{
        'name': '{self.model_name}',
        'threshold': 100,  # Suitable for files with >=100 lines
        'handler': lambda driver, content, endpoint: driver.get_response(content),
        'endpoint': 'local'
    }}
''')
                    logger.info(f"✅ Created local model file: {local_model_file}")
                
                # Reload models to ensure our new model is registered
                self.model_registry.reload_models()
            
            # Log available models
            logger.info(f"🧠 Available models: {list(self.model_registry.get_registry().keys())}")
            
            self.logger.info("✅ Core components initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing components: {e}")
            raise

    def scan_project_gui(self):
        """Triggers the ProjectScanner to scan the project and load analysis into the engine."""
        from ProjectScanner import ProjectScanner  # Import here to avoid circular imports
        try:
            scanner = ProjectScanner(project_root=".")
            scanner.scan_project()
            analysis_path = Path("project_analysis.json")
            if analysis_path.exists():
                with open(analysis_path, "r", encoding="utf-8") as f:
                    self.project_analysis = json.load(f)
                self.logger.info("✅ Project analysis loaded successfully.")
                return True, f"Scan complete. {len(self.project_analysis)} files analyzed."
            else:
                self.logger.warning("⚠️ No project analysis report found.")
                self.project_analysis = {}
                return False, "No analysis report found."
        except Exception as e:
            self.logger.error(f"❌ Error running ProjectScanner: {e}")
            self.project_analysis = {}
            return False, f"Error during scan: {e}"

    def get_chatgpt_response(self, prompt):
        """Unified call to LLM. Abstracts away driver differences."""
        try:
            # Instead of calling self.driver.get_response directly,
            # call a unified method (or use a wrapper) that handles both local and OpenAI responses.
            response = self.driver.get_response(prompt)
            return response
        except AttributeError as e:
            logger.error(f"❌ Driver does not support 'get_response': {e}")
            raise

    def switch_model(self, model_name):
        """Switch active LLM (local only for now)."""
        if not self.use_local_llm:
            logger.warning("⚠️ Model switching is currently only supported for local LLMs.")
            return
        try:
            self.driver.set_model(model_name)
            logger.info(f"✅ Switched to local model: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to switch model: {e}")

    def shutdown(self):
        """Gracefully shut down the active driver."""
        logger.info("🛑 Shutting down Automation Engine...")
        try:
            if not self.use_local_llm and hasattr(self, "openai_client"):
                self.openai_client.shutdown()
                logger.info("✅ OpenAIClient driver shut down successfully.")
            else:
                logger.info("✅ Local LLM engine does not require shutdown.")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

    def process_file(self, file_path, manual_model=None):
        """Process a single file from analysis to deployment."""
        logger.info(f"📂 Processing file: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"❌ Failed to read file {file_path}: {e}")
            return None

        # Select the model based on file content (or manual override)
        model_registry = self.model_registry.get_registry()
        if not model_registry:
            logger.error("❌ No models available in registry. Cannot process file.")
            return None
            
        model_choice = manual_model or self.select_model(file_content)
        model_meta = model_registry.get(model_choice)
        
        # Fallback to default model if specified model not found
        if not model_meta:
            logger.warning(f"⚠️ Model '{model_choice}' not found in registry. Trying fallback.")
            # Try local model if we're using local LLM
            if self.use_local_llm and self.model_name in model_registry:
                model_choice = self.model_name
                model_meta = model_registry.get(model_choice)
                logger.info(f"✅ Falling back to local model: {model_choice}")
            # Otherwise use the first available model
            else:
                model_choice = next(iter(model_registry))
                model_meta = model_registry.get(model_choice)
                logger.info(f"✅ Falling back to first available model: {model_choice}")
                
        if not model_meta:
            logger.error("❌ No usable model found in registry.")
            return None

        endpoint = model_meta.get('endpoint')
        handler = model_meta.get('handler')
        logger.info(f"🧠 Selected model: {model_choice} | Endpoint: {endpoint}")

        try:
            # Log start of processing
            start_time = time.time()
            logger.info(f"⏱️ Processing started with model {model_choice}")
            
            response = handler(self.driver, file_content, endpoint)
            
            # Log completion and time taken
            elapsed_time = time.time() - start_time
            logger.info(f"⏱️ Processing completed in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Error from model handler '{model_choice}': {e}")
            return None

        if not response:
            logger.warning(f"⚠️ No response received for {file_path}")
            return None

        # Save the refactored file
        output_file = file_path.replace(".py", "_refactored.py")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response)
            logger.info(f"✅ Refactored file saved: {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to write refactored file {output_file}: {e}")
            return None

        # Test and deploy if tests pass
        if self.run_tests(output_file):
            self.deploy_file(output_file)
        else:
            logger.warning(f"⚠️ Tests failed for {output_file}. Skipping deployment.")
        return output_file

    def self_heal_file(self, file_path, write_back=True, deploy_if_passes=True):
        """
        Perform self-healing on the specified file.

        Args:
            file_path (str): Path to the file to heal.
            write_back (bool): If True, overwrite the original file with the healed version.
            deploy_if_passes (bool): If True, run tests and deploy if they pass.
            
        Returns:
            str or None: Path to healed file if successful, else None.
        """
        abs_path = str(Path(file_path).resolve())
        logger.info(f"🩺 Starting self-heal for: {abs_path}")

        if not os.path.exists(abs_path):
            logger.error(f"❌ File not found: {abs_path}")
            return None

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"❌ Failed to read file {abs_path}: {e}")
            return None

        # Prompt Template (Pluggable for future modes)
        prompt_text = (
            "You are an autonomous code repair system. "
            "Your task is to fix any bugs, syntax errors, or poor formatting in this Python file. "
            "Return only the complete, corrected source code."
        )
        combined_prompt = f"{prompt_text}\n\n---\n\n{file_content}"

        logger.info("🧠 Dispatching self-heal prompt to model...")
        response = self.get_chatgpt_response(combined_prompt)

        if not response:
            logger.error("❌ Self-heal failed; no response from model.")
            return None

        healed_path = abs_path if write_back else abs_path.replace(".py", "_healed.py")

        try:
            with open(healed_path, "w", encoding="utf-8") as f:
                f.write(response)
            logger.info(f"✅ Healed file written to: {healed_path}")
        except Exception as e:
            logger.error(f"❌ Failed to write healed file: {e}")
            return None

        if deploy_if_passes:
            logger.info("🧪 Running tests on healed file...")
            if self.run_tests(healed_path):
                logger.info("📦 Test passed. Deploying healed file...")
                self.deploy_file(healed_path)
            else:
                logger.warning("⚠️ Healed file failed tests. Skipping deployment.")

        return healed_path


    def select_model(self, file_content):
        """
        Dynamically select a model based on file complexity.
        Uses both line count and an estimation of code complexity.
        """
        lines = len(file_content.strip().splitlines())
        logger.info(f"📏 File has {lines} lines.")
        
        # Simple complexity heuristic - count imports, classes, and functions
        imports_count = len([line for line in file_content.splitlines() if line.strip().startswith(('import ', 'from '))])
        class_count = len([line for line in file_content.splitlines() if line.strip().startswith('class ')])
        function_count = len([line for line in file_content.splitlines() if line.strip().startswith(('def ', 'async def '))])
        
        # Compute weighted complexity score
        complexity_score = lines + (imports_count * 2) + (class_count * 5) + (function_count * 3)
        logger.info(f"🧮 Complexity analysis: {imports_count} imports, {class_count} classes, {function_count} functions")
        logger.info(f"🔢 Complexity score: {complexity_score}")
        
        # Get model registry and catch empty registry
        model_registry = self.model_registry.get_registry()
        if not model_registry:
            logger.warning("⚠️ Empty model registry. Defaulting to local model if available.")
            return self.model_name if self.use_local_llm else None
        
        # Sort models by threshold - highest threshold first
        sorted_models = sorted(model_registry.items(), key=lambda x: -x[1]['threshold'])
        
        # Try to find a model with a suitable threshold
        for model_name, meta in sorted_models:
            if complexity_score >= meta["threshold"]:
                logger.info(f"🎯 Selected model '{model_name}' based on complexity threshold {meta['threshold']}")
                return model_name
        
        # If no matching model found, use the one with the lowest threshold
        fallback_model = sorted_models[-1][0]
        logger.warning(f"⚠️ No perfect match found. Defaulting to model with lowest threshold: {fallback_model}")
        return fallback_model

    def run_tests(self, file_path):
        """Placeholder: Run tests for the given file. Replace with actual test logic."""
        logger.info(f"🧪 Running tests for: {file_path}")
        try:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                logger.info("✅ Test passed.")
                return True
        except Exception as e:
            logger.error(f"❌ Test error for {file_path}: {e}")
        return False

    def deploy_file(self, file_path):
        """Deploy and backup the file."""
        backup_path = BACKUP_FOLDER / (Path(file_path).stem + "_backup.py")
        deploy_path = DEPLOY_FOLDER / Path(file_path).name
        logger.info(f"📦 Deploying file: {file_path}")
        try:
            shutil.copy2(file_path, backup_path)
            shutil.move(file_path, deploy_path)
            logger.info(f"✅ Deployed to: {deploy_path}")
            logger.info(f"🗄️ Backup saved at: {backup_path}")
        except Exception as e:
            logger.error(f"❌ Deployment error for {file_path}: {e}")

    def prioritize_files(self):
        """
        Prioritize files based on their complexity score from project analysis.
        Returns a list of absolute file paths sorted by descending complexity.
        """
        prioritized = []
        for file_path, data in self.project_analysis.items():
            complexity = data.get("complexity", 0)
            prioritized.append((file_path, complexity))
        prioritized.sort(key=lambda x: x[1], reverse=True)
        logger.info("✅ Files prioritized by complexity.")
        return [str((Path(file) if Path(file).is_absolute() else Path(self.project_root) / file).resolve())
                for file, _ in prioritized]

    def process_all_files(self):
        """Process all files in order of complexity."""
        files = self.prioritize_files()
        for file_path in files:
            self.process_file(file_path)

    # ------------------------------
    # New Method: Export Project Context for AI
    # ------------------------------
    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None):
        """
        Exports the project analysis into a structured format suitable for ChatGPT.
        
        Args:
            template_path: Optional Jinja template path for narrative output.
            output_path: Optional output file path. Defaults to JSON if no template, or .md if template provided.
            
        Usage:
            - JSON export: self.export_chatgpt_context()
            - Jinja export: self.export_chatgpt_context(template_path="prompts/chatgpt_template.md.jinja", output_path="chatgpt_context.md")
        """
        if not output_path:
            output_path = "chatgpt_project_context.md" if template_path else "chatgpt_project_context.json"
        if not template_path:
            payload = {
                "project_root": str(self.project_root),
                "num_files_analyzed": len(self.project_analysis),
                "analysis_details": self.project_analysis
            }
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=4)
                print(f"✅ Exported project context (JSON) to: {output_path}")
                self.logger.info(f"✅ Exported project context (JSON) to: {output_path}")
            except Exception as e:
                self.logger.error(f"❌ Error writing JSON context: {e}")
            return

        try:
            from jinja2 import Template
            with open(template_path, "r", encoding="utf-8") as tf:
                template_content = tf.read()
            t = Template(template_content)
            context_dict = {
                "project_root": str(self.project_root),
                "analysis": self.project_analysis,
                "num_files_analyzed": len(self.project_analysis),
            }
            rendered = t.render(context=context_dict)
            with open(output_path, "w", encoding="utf-8") as outf:
                outf.write(rendered)
            print(f"✅ Exported project context (Jinja) to: {output_path}")
            self.logger.info(f"✅ Exported project context (Jinja) to: {output_path}")
        except ImportError:
            print("⚠️ Jinja2 not installed. Run `pip install jinja2` and retry.")
            self.logger.warning("⚠️ Jinja2 not installed. Run `pip install jinja2` and retry.")
        except Exception as e:
            self.logger.error(f"❌ Error rendering Jinja template: {e}")

    def add_manual_model(self, name, threshold, handler_func, endpoint='local'):
        """
        Manually add a model to the registry without using file-based loading.
        This is useful for dynamically adding models at runtime or for testing.
        
        Args:
            name: Model name identifier
            threshold: Complexity threshold for model selection
            handler_func: Function that processes content and returns a response
            endpoint: Endpoint identifier (default: 'local')
            
        Returns:
            bool: True if the model was successfully added
        """
        logger.info(f"🧩 Manually adding model: {name}")
        
        try:
            # Create a model file dynamically
            model_file = self.model_registry.models_dir / f"model_{name}.py"
            
            with open(model_file, "w", encoding="utf-8") as f:
                f.write(f'''
def register():
    """Register the {name} model."""
    
    def handler_wrapper(driver, content, endpoint):
        """Wrapper for the custom handler function."""
        # This wrapper ensures compatibility with the expected signature
        return handler_func(driver, content, endpoint)
    
    return {{
        'name': '{name}',
        'threshold': {threshold},
        'handler': handler_wrapper,
        'endpoint': '{endpoint}'
    }}
''')
            
            # Reload models to ensure our new model is registered
            self.model_registry.reload_models()
            
            # Verify the model was added
            model_registry = self.model_registry.get_registry()
            if name in model_registry:
                logger.info(f"✅ Model '{name}' successfully added with threshold {threshold}")
                return True
            else:
                logger.error(f"❌ Failed to add model '{name}' - not found in registry after reload")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding model '{name}': {e}")
            return False


# ------------------------------
# Asynchronous Task Queue Components
# ------------------------------
class BotWorker(threading.Thread):
    """
    A background worker that processes file tasks from a queue.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner: ProjectScanner, status_callback=None):
        threading.Thread.__init__(self)
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            file_path = self.task_queue.get()
            if file_path is None:
                break
            result = self.scanner._process_file(file_path)
            if result is not None:
                self.results_list.append(result)
            if self.status_callback:
                self.status_callback(file_path, result)
            self.task_queue.task_done()


class MultibotManager:
    """
    Manages a pool of BotWorker threads.
    """
    def __init__(self, scanner: ProjectScanner, num_workers=4, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list = []
        self.scanner = scanner
        self.status_callback = status_callback
        self.workers = [
            BotWorker(self.task_queue, self.results_list, scanner, status_callback)
            for _ in range(num_workers)
        ]

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        self.task_queue.join()

    def stop_workers(self):
        for _ in range(len(self.workers)):
            self.task_queue.put(None)


# ------------------------------
# Entry Point
# ------------------------------
if __name__ == "__main__":
    project_root = input("Enter the project root directory to scan (default '.'): ").strip() or "."
    ignore_input = input("Enter additional directories to ignore (comma separated, or leave empty): ").strip()
    additional_ignore_dirs = {d.strip() for d in ignore_input.split(",") if d.strip()} if ignore_input else set()

    scanner = ProjectScanner(project_root=project_root)
    scanner.additional_ignore_dirs = additional_ignore_dirs
    scanner.scan_project()
    scanner.generate_init_files(overwrite=True)

    export_answer = input("Export ChatGPT context? (y/n) ").lower()
    if export_answer.startswith("y"):
        jinja_path = input("Jinja template path (leave blank for JSON export): ").strip()
        output_file = input("Output file path (leave blank for default): ").strip()
        scanner.export_chatgpt_context(
            template_path=jinja_path if jinja_path else None,
            output_path=output_file if output_file else None
        )
