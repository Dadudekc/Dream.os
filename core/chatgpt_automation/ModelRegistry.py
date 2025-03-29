import os
import importlib.util
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ModelRegistry:
    def __init__(self, models_dir=None):
        """
        Initialize the ModelRegistry.
        """
        self.project_root = self.find_project_root()

        self.models_dir = Path(models_dir) if models_dir else self.project_root / 'models'
        self.registry = {}

        logger.info(f"📂 Looking for models in: {self.models_dir}")

        # Load models on startup
        self.load_models()

    def find_project_root(self):
        """
        Walk upward to find the project root.
        """
        path = Path(__file__).resolve().parent

        while path != path.parent:
            if path.name == 'chatgpt_automation':
                logger.info(f"🏠 Project root anchored at: {path}")
                return path

            if any((path / marker).exists() for marker in ['.git', 'setup.py', 'pyproject.toml']):
                logger.info(f"🏠 Marker-based project root found at: {path}")
                return path

            path = path.parent

        logger.warning(f"⚠️ Project root not found. Defaulting to: {path}")
        return path

    def load_models(self):
        """
        Loads all models from the models directory.
        """
        if not self.models_dir.exists():
            logger.warning(f"📁 Models directory not found. Creating: {self.models_dir}")
            self.models_dir.mkdir(parents=True, exist_ok=True)
            return

        logger.info(f"🚀 Loading models from {self.models_dir}...")

        self.registry.clear()

        for filename in os.listdir(self.models_dir):
            if filename.endswith('.py') and filename.startswith('model_'):
                self._load_single_model(filename)

        logger.info(f"✅ {len(self.registry)} models loaded successfully.")

    def _load_single_model(self, filename):
        """
        Load an individual model file.
        """
        module_path = self.models_dir / filename
        module_name = module_path.stem

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, 'register'):
                logger.error(f"❌ {module_name} missing register(). Skipping...")
                return

            metadata = module.register()

            # Required keys for new model registration
            required_keys = {'name', 'threshold', 'handler', 'endpoint'}
            if not required_keys.issubset(metadata.keys()):
                logger.error(f"❌ {module_name} returned incomplete data: {metadata}")
                return

            self.registry[metadata['name']] = {
                'threshold': metadata['threshold'],
                'handler': metadata['handler'],
                'endpoint': metadata['endpoint']
            }

            logger.info(
                f"✅ Model registered: {metadata['name']} | "
                f"Threshold: {metadata['threshold']} | "
                f"Endpoint: {metadata['endpoint']}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to load model '{module_name}': {e}")

    def reload_models(self):
        """
        Clears and reloads all models at runtime.
        """
        logger.info("🔄 Reloading models...")

        self.load_models()

        logger.info(f"✅ Reload complete. {len(self.registry)} models now registered.")

    def get_registry(self):
        """
        Return the current model registry.
        """
        return self.registry

    def __str__(self):
        """
        Debug summary of all loaded models.
        """
        if not self.registry:
            return "🚫 No models registered."

        summary_lines = ["🚀 Loaded Models Summary:"]
        for model_name, meta in self.registry.items():
            handler_name = meta['handler'].__name__ if callable(meta['handler']) else "Not Callable"
            summary_lines.append(
                f"- {model_name}:\n"
                f"    ↪ Threshold: {meta['threshold']}\n"
                f"    ↪ Endpoint : {meta['endpoint']}\n"
                f"    ↪ Handler  : {handler_name}"
            )
        return "\n".join(summary_lines)


# ---------------------------
# Direct Run / Debugging Mode
# ---------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        registry_loader = ModelRegistry()
        print(registry_loader)

        # 🔄 Try hot reload (manual test)
        input("\n⚡ Press Enter to reload models...\n")
        registry_loader.reload_models()
        print(registry_loader)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
