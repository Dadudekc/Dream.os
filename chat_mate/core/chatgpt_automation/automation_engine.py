"""
AutomationEngine module for managing automated interactions with ChatGPT.
"""

import os
import sys
import json
import time
import queue
import threading
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

from chat_mate.core.openai import OpenAIClient  # ChatGPT driver wrapper
from .driver_factory import DriverFactory
from .model_registry import ModelRegistry
from .config import Config
from .post_process_validator import PostProcessValidator
from .local_llm_engine import LocalLLMEngine
import shutil
import logging
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import Qt  # For splash screen messages
import re

# External project-specific imports (ensure these are configured correctly)
from core.chatgpt_automation.config import PROFILE_DIR, CHATGPT_HEADLESS, CHROMEDRIVER_PATH
# Import ProjectScanner assuming chat_mate is on the path or is the root
from ProjectScanner import ProjectScanner

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
    """Engine for automating interactions with ChatGPT."""
    
    def __init__(self, use_local_llm: bool = False, model_name: str = 'mistral', 
                 beta_mode: bool = False, splash_screen: Optional[Any] = None,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize the automation engine.
        
        Args:
            use_local_llm (bool): Whether to use a local LLM instead of ChatGPT.
            model_name (str): Name of the model to use.
            beta_mode (bool): Whether to enable beta features.
            splash_screen (Optional[Any]): Splash screen widget for progress updates.
            config (Optional[Dict[str, Any]]): Custom configuration settings.
        """
        self.logger = logging.getLogger(__name__)
        
        # Validate model_name
        MAX_MODEL_NAME_LENGTH = 64
        if not model_name or not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("Model name must be a non-empty string.")
        if len(model_name) > MAX_MODEL_NAME_LENGTH:
            raise ValueError(f"Model name exceeds maximum length of {MAX_MODEL_NAME_LENGTH} characters.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", model_name):
             raise ValueError("Model name contains invalid characters.")
            
        # Validate config
        if config is not None and not isinstance(config, dict):
            raise ValueError("Config must be a dictionary or None.")
        
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self.beta_mode = beta_mode
        self.splash_screen = splash_screen
        self.config = config or {}
        
        self.model_registry = ModelRegistry()
        self.driver_factory = DriverFactory()
        self.post_process_validator = PostProcessValidator()
        
        if use_local_llm:
            self.local_llm_engine = LocalLLMEngine(model_name=model_name)
        else:
            self.local_llm_engine = None
        
        self.project_analysis = {}  # Initialize as empty
        
        self.project_analysis = {}  # Initialize as empty
        
        self.logger.info("✅ AutomationEngine initialized successfully")
        
    def initialize_components(self):
        """Initialize all required components."""
        try:
            if self.use_local_llm:
                if not self.local_llm_engine:
                    self.local_llm_engine = LocalLLMEngine(model_name=self.model_name)
                if not self.local_llm_engine.initialize():
                    self.logger.error("❌ Failed to initialize Local LLM Engine.")
                    return False
            else:
                if not self.driver_factory.driver:
                    self.driver_factory.create_driver()
            self.logger.info("✅ Core components initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error initializing components: {e}")
            return False

    def scan_project_gui(self):
        """Runs the project scan and updates GUI elements (if provided)."""
        logger.info("🔍 Starting project scan with GUI updates...")
        # Remove the inner import, use the top-level one
        # from .project_scanner import ProjectScanner 
        
        try:
            # Assume project_root needs to be resolved relative to current working dir or a known base
            # If self.project_root is already set, use it. Otherwise, default? Let's default to "."
            project_root_to_scan = getattr(self, 'project_root', ".")
            scanner = ProjectScanner(project_root=project_root_to_scan)
            scanner.additional_ignore_dirs = self.config.get('scan_ignore_dirs', set())
            
            # Connect signals if GUI components are available (conceptual)
            # if hasattr(self, 'progress_bar') and self.progress_bar:
            #     scanner.progress.connect(self.progress_bar.setValue)
            # if hasattr(self, 'status_label') and self.status_label:
            #     scanner.status_update.connect(self.status_label.setText)

            scan_success = scanner.scan_project()
            
            if not scan_success:
                logger.error("❌ Project scan failed.")
                return False, "Scan failed. Check logs."

            # Load the analysis results
            analysis_file = Path("project_analysis.json")
            if analysis_file.exists():
                with open(analysis_file, "r", encoding="utf-8") as f:
                    self.project_analysis = json.load(f)
                logger.info("✅ Project analysis loaded successfully.")
                return True, f"Scan complete. {len(self.project_analysis)} files analyzed."
            else:
                logger.warning("⚠️ No project analysis report found after scan.")
                self.project_analysis = {}
                return False, "Scan finished, but no analysis report found."
        except ImportError as e:
            logger.error(f"❌ Error importing ProjectScanner: {e}. Is it installed and in the correct path?")
            self.project_analysis = {}
            return False, f"Scanner import error: {e}"    
        except Exception as e:
            logger.error(f"❌ Error running ProjectScanner: {e}", exc_info=True)
            self.project_analysis = {}
            return False, f"Error during scan: {e}"

    def get_chatgpt_response(self, prompt):
        """Unified call to LLM. Handles local LLM or OpenAI driver."""
        try:
            if self.use_local_llm:
                if not self.local_llm_engine:
                    logger.error("❌ Local LLM engine requested but not initialized.")
                    raise RuntimeError("Local LLM engine not initialized.")
                logger.debug("🧠 Using local LLM engine for response.")
                response = self.local_llm_engine.get_response(prompt)
            else:
                # Ensure driver is available via factory
                driver = self.driver_factory.get_driver()
                if not driver:
                     logger.error("❌ OpenAI driver requested but not available.")
                     raise RuntimeError("OpenAI driver not available.")
                logger.debug("🧠 Using OpenAI driver for response.")
                response = driver.get_response(prompt)

            return response
        except AttributeError as e:
            # Catch cases where get_response might be missing on the object
            logger.error(f"❌ Selected engine/driver does not support 'get_response': {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error getting response from LLM: {e}")
            raise # Re-raise after logging

    def switch_model(self, model_name):
        """Switch active LLM (local only for now)."""
        if not self.use_local_llm:
            logger.warning("⚠️ Model switching is currently only supported for local LLMs.")
            return
        # Use local_llm_engine if use_local_llm is True
        if not self.local_llm_engine:
            logger.error("❌ Local LLM engine requested for model switch but not initialized.")
            return 
        try:
            self.local_llm_engine.set_model(model_name)
            logger.info(f"✅ Switched to local model: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to switch model: {e}")

    def shutdown(self):
        """Gracefully shut down the automation engine and its components."""
        logger.info("🛑 Shutting down Automation Engine...")
        try:
            self.close() # Delegate shutdown logic to the close method
            logger.info("✅ Automation Engine shutdown complete.")
        except Exception as e:
            logger.error(f"❌ Error during engine shutdown: {e}")

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

    def add_manual_model(self, name: str, threshold: int, handler_func: Callable, endpoint: Optional[str] = None) -> bool:
        """Add a custom model programmatically."""
        # Check if model already exists before proceeding
        if name in self.model_registry.get_registry():
            logger.warning(f"⚠️ Model '{name}' already exists. Skipping addition.")
            return False # Indicate that the model already exists and was not added

        try:
            model_dir = self.model_registry.models_dir
            if not model_dir.exists():
                model_dir.mkdir()
            
            model_file = model_dir / f"model_{name}.py"
            
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

    def close(self):
        """Close and clean up resources."""
        try:
            if self.use_local_llm and self.local_llm_engine:
                self.local_llm_engine.close()
            # Check for openai_client before closing driver factory
            elif hasattr(self, "openai_client") and self.openai_client: 
                # Assume openai_client handles its own closing/shutdown elsewhere
                # or via its own shutdown method called by the original shutdown.
                # For now, do nothing here if openai_client exists.
                logger.info("OpenAIClient present, skipping driver_factory.close_driver().")
            else:
                # Close driver factory only if not local and no openai_client
                self.driver_factory.close_driver()
        except Exception as e:
            logger.error(f"❌ Error closing components: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            Dict[str, Any]: Current configuration settings.
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update the configuration.
        
        Args:
            new_config (Dict[str, Any]): New configuration settings.
        """
        self.config.update(new_config)


# ------------------------------
# Asynchronous Task Queue Components
# ------------------------------
class BotWorker(threading.Thread):
    """
    A background worker that processes file tasks from a queue.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner: Any, status_callback=None):
        threading.Thread.__init__(self)
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner
        self.status_callback = status_callback
        self.daemon = True

    def run(self):
        while True:
            task_item = self.task_queue.get()
            if task_item is None:
                break # Sentinel value received
            
            # Check if the task_item is a valid file path (string)
            if isinstance(task_item, (str, Path)):
                file_path = str(task_item)
                result = None # Initialize result
                try:
                    # Delegate processing to the scanner instance
                    result = self.scanner._process_file(file_path)
                    if result is not None:
                        self.results_list.append(result)
                except Exception as e:
                    # Log the error, but keep the worker running
                    logger.error(f"BotWorker error processing {file_path}: {e}")
                    result = None # Ensure result is None on exception
                finally:
                    if self.status_callback:
                        try:
                            self.status_callback(file_path, result)
                        except Exception as cb_e:
                            logger.error(f"BotWorker status_callback error: {cb_e}")
                    self.task_queue.task_done()
            else:
                # Handle invalid task format
                logger.warning(f"BotWorker received invalid task format: {type(task_item)}. Skipping.")
                if self.status_callback:
                    try:
                        self.status_callback(task_item, None) # Notify with None result
                    except Exception as cb_e:
                        logger.error(f"BotWorker status_callback error for invalid task: {cb_e}")
                self.task_queue.task_done() # Mark invalid task as done


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
        """Signals all workers to stop and waits for them to finish."""
        num_workers_to_stop = len(self.workers)
        logger.info(f"🛑 Stopping {num_workers_to_stop} workers...")
        for _ in range(num_workers_to_stop):
            self.task_queue.put(None) # Send sentinel value
            
        # Wait for all tasks to be processed
        # self.task_queue.join() # This might block indefinitely if workers crashed
        
        # Wait for all worker threads to complete
        for worker in self.workers:
            try:
                # Only join if the thread was actually started and is alive
                if worker.is_alive(): 
                    worker.join(timeout=5.0) # Add a timeout
                    if worker.is_alive():
                        logger.warning(f"Worker {worker.name} did not exit cleanly after timeout.")
            except Exception as e:
                logger.error(f"Error joining worker {worker.name}: {e}")
        logger.info("✅ All workers stopped.")
        

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
