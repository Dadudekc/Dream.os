import os
import importlib
import logging
from typing import Any, Dict, Optional
from social.strategies.base_platform_strategy import BasePlatformStrategy

class StrategyLoader:
    """
    Dynamically loads platform-specific strategy classes.
    Handles strategy initialization and validation.
    """
    
    def __init__(self):
        """Initialize the strategy loader."""
        self.logger = logging.getLogger(__name__)
        self.strategy_cache: Dict[str, Any] = {}
        self.strategy_module_map = {
            "TwitterStrategy": "social.strategies.twitter_strategy",
            "FacebookStrategy": "social.strategies.facebook_strategy",
            "RedditStrategy": "social.strategies.reddit_strategy",
            "InstagramStrategy": "social.strategies.instagram_strategy",
            "LinkedinStrategy": "social.strategies.linkedin_strategy",
            "StocktwitsStrategy": "social.strategies.stocktwits_strategy",
            "TikTokStrategy": "social.strategies.tiktok_strategy",
            "YouTubeStrategy": "social.strategies.youtube_strategy"
        }
    
    def load_strategy(self, strategy_name: str, driver=None) -> Optional[BasePlatformStrategy]:
        """
        Load a platform strategy by name.
        
        Args:
            strategy_name (str): Name of the strategy class to load
            driver: Optional WebDriver instance to use
            
        Returns:
            BasePlatformStrategy or None: Loaded strategy instance
        """
        try:
            # Check cache first
            if strategy_name in self.strategy_cache:
                self.logger.debug(f"Using cached strategy for {strategy_name}")
                return self.strategy_cache[strategy_name](driver=driver)
            
            # Get module path
            module_path = self.strategy_module_map.get(strategy_name)
            if not module_path:
                self.logger.error(f"No module mapping found for strategy: {strategy_name}")
                return None
            
            # Import module and get strategy class
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, strategy_name)
            
            # Validate strategy class
            if not self._validate_strategy(strategy_class):
                self.logger.error(f"Invalid strategy class: {strategy_name}")
                return None
            
            # Cache strategy class
            self.strategy_cache[strategy_name] = strategy_class
            
            # Create and return instance
            strategy = strategy_class(driver=driver)
            self.logger.info(f"Successfully loaded strategy: {strategy_name}")
            return strategy
        except ImportError as e:
            self.logger.error(f"Error importing strategy module {strategy_name}: {e}")
        except AttributeError as e:
            self.logger.error(f"Strategy class {strategy_name} not found in module: {e}")
        except Exception as e:
            self.logger.error(f"Error loading strategy {strategy_name}: {e}")
        
        return None
    
    def _validate_strategy(self, strategy_class: Any) -> bool:
        """
        Validate that a strategy class implements required interface.
        
        Args:
            strategy_class: Class to validate
            
        Returns:
            bool: True if valid
        """
        required_methods = [
            "initialize",
            "cleanup",
            "get_community_metrics",
            "get_top_members",
            "track_member_interaction"
        ]
        
        try:
            # Check inheritance
            if not issubclass(strategy_class, BasePlatformStrategy):
                self.logger.error(f"Strategy class must inherit from BasePlatformStrategy")
                return False
            
            # Check required methods
            for method in required_methods:
                if not hasattr(strategy_class, method):
                    self.logger.error(f"Strategy missing required method: {method}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating strategy class: {e}")
            return False
    
    def get_available_strategies(self) -> Dict[str, str]:
        """
        Get mapping of available strategy names to their module paths.
        
        Returns:
            Dict[str, str]: Strategy name to module path mapping
        """
        return self.strategy_module_map.copy()
    
    def reload_strategy(self, strategy_name: str) -> bool:
        """
        Force reload a strategy module.
        
        Args:
            strategy_name (str): Name of strategy to reload
            
        Returns:
            bool: True if successfully reloaded
        """
        try:
            # Remove from cache
            if strategy_name in self.strategy_cache:
                del self.strategy_cache[strategy_name]
            
            # Get module path
            module_path = self.strategy_module_map.get(strategy_name)
            if not module_path:
                self.logger.error(f"No module mapping found for strategy: {strategy_name}")
                return False
            
            # Force reload module
            module = importlib.import_module(module_path)
            importlib.reload(module)
            
            self.logger.info(f"Successfully reloaded strategy: {strategy_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error reloading strategy {strategy_name}: {e}")
            return False
    
    def register_strategy(self, strategy_name: str, module_path: str) -> bool:
        """
        Register a new strategy module.
        
        Args:
            strategy_name (str): Name of strategy class
            module_path (str): Import path to module
            
        Returns:
            bool: True if successfully registered
        """
        try:
            # Validate module exists
            module = importlib.import_module(module_path)
            if not hasattr(module, strategy_name):
                self.logger.error(f"Module {module_path} does not contain strategy {strategy_name}")
                return False
            
            # Add to module map
            self.strategy_module_map[strategy_name] = module_path
            
            # Clear from cache if present
            if strategy_name in self.strategy_cache:
                del self.strategy_cache[strategy_name]
            
            self.logger.info(f"Registered new strategy: {strategy_name} -> {module_path}")
            return True
        except ImportError as e:
            self.logger.error(f"Error importing module {module_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error registering strategy {strategy_name}: {e}")
        
        return False 
