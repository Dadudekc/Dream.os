"""
Model registry for managing different language models.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .config import Config


class ModelRegistry:
    """Registry for managing different language models."""
    
    def __init__(self, models_dir: Optional[Path] = None):
        """Initialize the model registry.
        
        Args:
            models_dir (Optional[Path]): Directory containing model files.
        """
        self.models_dir = models_dir or Config.get_models_dir()
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.load_models()
    
    def load_models(self):
        """Load model configurations from the models directory."""
        if not self.models_dir.exists():
            os.makedirs(self.models_dir)
            return
        
        for file in self.models_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    model_config = json.load(f)
                model_name = file.stem
                self.registry[model_name] = model_config
            except Exception as e:
                print(f"Error loading model {file}: {e}")
    
    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get a model by name.
        
        Args:
            model_name (str): Name of the model to get.
            
        Returns:
            Optional[Dict[str, Any]]: Model configuration if found, None otherwise.
        """
        return self.registry.get(model_name)
    
    def add_model(self, model_name: str, config: Dict[str, Any]) -> bool:
        """Add a new model to the registry. If the model already exists,
        it returns False without modifying the existing entry.

        Args:
            model_name (str): Name of the model to add.
            config (Dict[str, Any]): Model configuration.

        Returns:
            bool: True if the model was newly added, False if it already exists or an error occurred.
        """
        if model_name in self.registry:
            print(f"Model '{model_name}' already exists. Not adding.")
            return False  # Indicate that the model already exists

        try:
            model_file = self.models_dir / f"{model_name}.json"
            with open(model_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.registry[model_name] = config
            return True
        except Exception as e:
            print(f"Error adding model {model_name}: {e}")
            return False
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the registry.
        
        Args:
            model_name (str): Name of the model to remove.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            model_file = self.models_dir / f"{model_name}.json"
            if model_file.exists():
                os.remove(model_file)
            self.registry.pop(model_name, None)
            return True
        except Exception as e:
            print(f"Error removing model {model_name}: {e}")
            return False
    
    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the entire model registry.
        
        Returns:
            Dict[str, Dict[str, Any]]: The model registry.
        """
        return self.registry.copy()
    
    def clear_registry(self):
        """Clear the entire model registry."""
        try:
            for file in self.models_dir.glob("*.json"):
                os.remove(file)
            self.registry.clear()
        except Exception as e:
            print(f"Error clearing registry: {e}")
    
    def update_model(self, model_name: str, config: Dict[str, Any]) -> bool:
        """Update an existing model's configuration.
        
        Args:
            model_name (str): Name of the model to update.
            config (Dict[str, Any]): New model configuration.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if model_name not in self.registry:
            return False
        return self.add_model(model_name, config)
    
    def get_model_file(self, model_name: str) -> Optional[Path]:
        """Get the path to a model's configuration file.
        
        Args:
            model_name (str): Name of the model.
            
        Returns:
            Optional[Path]: Path to the model file if it exists, None otherwise.
        """
        model_file = self.models_dir / f"{model_name}.json"
        return model_file if model_file.exists() else None 