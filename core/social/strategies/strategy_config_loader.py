# core/social/strategies/strategy_config_loader.py
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import warnings

# Define the default base path for configs relative to this file's grandparent directory
# Adjust this path if your project structure differs significantly
DEFAULT_CONFIG_BASE_DIR = Path(__file__).parent.parent.parent / "configs" / "strategies"

class StrategyConfigLoader:
    """
    Loads, validates, and provides access to platform-specific strategy
    configuration parameters stored in JSON files.
    """

    def __init__(self, platform: str, config_dir: Path = DEFAULT_CONFIG_BASE_DIR):
        """
        Initializes the loader for a specific platform.

        Args:
            platform: The name of the platform (e.g., 'twitter', 'instagram').
            config_dir: The directory containing the strategy config JSON files.
        """
        self.platform = platform.lower()
        self.config_dir = config_dir
        self.config_path = self.config_dir / f"{self.platform}_strategy_config.json"
        self._config: Optional[Dict[str, Any]] = None
        self._parameters: Dict[str, Any] = {} # Holds the nested 'parameters' dict

        self.load_config()

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Performs basic validation on the loaded config structure."""
        if config.get("platform") != self.platform:
            warnings.warn(
                f"Platform mismatch in config file {self.config_path}. "
                f"Expected '{self.platform}', found '{config.get("platform")}'.",
                UserWarning
            )
            # Continue loading but be aware of the mismatch

        if "parameters" not in config:
            warnings.warn(f"Config file {self.config_path} is missing the required 'parameters' key.", UserWarning)
            return False

        if not isinstance(config["parameters"], dict):
             warnings.warn(f"'parameters' key in {self.config_path} is not a dictionary.", UserWarning)
             return False

        # Add more specific parameter validation as needed
        # Example: Check if post_frequency_per_day is a positive number

        return True

    def load_config(self) -> bool:
        """Loads or reloads the configuration file for the specified platform."""
        if not self.config_path.is_file():
            warnings.warn(f"Config file not found for platform '{self.platform}' at {self.config_path}", UserWarning)
            self._config = None
            self._parameters = {}
            return False
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            if self._validate_config(config_data):
                self._config = config_data
                self._parameters = self._config.get("parameters", {}) # Extract parameters
                print(f"Successfully loaded and validated config for '{self.platform}' from {self.config_path}")
                return True
            else:
                warnings.warn(f"Config validation failed for '{self.platform}'. Using empty parameters.", UserWarning)
                self._config = config_data # Keep raw config even if validation fails partially
                self._parameters = {}
                return False

        except json.JSONDecodeError as e:
            warnings.warn(f"Error decoding JSON from {self.config_path}: {e}", UserWarning)
            self._config = None
            self._parameters = {}
            return False
        except Exception as e:
            warnings.warn(f"Error reading config file {self.config_path}: {e}", UserWarning)
            self._config = None
            self._parameters = {}
            return False

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a specific parameter from the loaded configuration.

        Args:
            key: The name of the parameter (e.g., 'post_frequency_per_day').
            default: The value to return if the key is not found.

        Returns:
            The parameter value or the default.
        """
        if not self._parameters:
             if default is not None:
                 return default
             else:
                 # Raise error or return None if no parameters loaded and no default?
                 # Returning None is safer for now.
                 warnings.warn(f"Attempted to get parameter '{key}' but no config parameters loaded for '{self.platform}'. Returning None.", RuntimeWarning)
                 return None

        return self._parameters.get(key, default)

    def get_all_parameters(self) -> Dict[str, Any]:
        """Returns a copy of the entire parameters dictionary."""
        return self._parameters.copy()

    def is_enabled(self) -> bool:
        """Checks if the strategy is marked as enabled in the config."""
        if not self._config:
            return False # Cannot be enabled if config didn't load
        return self._config.get("enabled", False)

    @property
    def last_updated(self) -> Optional[str]:
         """Returns the last updated timestamp from the config, if available."""
         if not self._config:
             return None
         return self._config.get("last_updated")

# Example Usage
if __name__ == "__main__":
    print("Testing StrategyConfigLoader...")

    # Test loading Twitter config (assuming it exists in ../../configs/strategies/)
    print("\n--- Loading Twitter Config ---")
    twitter_loader = StrategyConfigLoader("twitter")
    if twitter_loader._config:
        print(f"Twitter Enabled: {twitter_loader.is_enabled()}")
        print(f"Twitter Last Updated: {twitter_loader.last_updated}")
        freq = twitter_loader.get_parameter("post_frequency_per_day", default=1)
        print(f"Twitter Post Frequency: {freq}")
        keywords = twitter_loader.get_parameter("targeting_keywords", default=[])
        print(f"Twitter Keywords: {keywords}")
        non_existent = twitter_loader.get_parameter("some_missing_key")
        print(f"Missing Key (no default): {non_existent}")
        missing_with_default = twitter_loader.get_parameter("some_missing_key", default="fallback")
        print(f"Missing Key (with default): {missing_with_default}")
        all_params = twitter_loader.get_all_parameters()
        print(f"All Twitter Params Keys: {list(all_params.keys())}")
    else:
        print("Twitter config could not be loaded.")

    # Test loading Instagram config
    print("\n--- Loading Instagram Config ---")
    insta_loader = StrategyConfigLoader("instagram")
    if insta_loader._config:
        print(f"Instagram Enabled: {insta_loader.is_enabled()}")
        style = insta_loader.get_parameter("caption_style", "default_style")
        print(f"Instagram Caption Style: {style}")
    else:
        print("Instagram config could not be loaded.")

    # Test loading a non-existent config
    print("\n--- Loading Non-Existent Config ---")
    unknown_loader = StrategyConfigLoader("facebook") # Assuming no facebook config yet
    print(f"Facebook Enabled: {unknown_loader.is_enabled()}")
    val = unknown_loader.get_parameter("some_key", "default_val")
    print(f"Facebook Param (should be default): {val}")

    print("\nStrategyConfigLoader Test Complete.") 