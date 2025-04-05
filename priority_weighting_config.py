#!/usr/bin/env python3
"""
Priority Weighting Configuration

This module provides configuration utilities for customizing how
the StatefulCursorManager prioritizes modules for improvement.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriorityWeightingConfig:
    """
    Manages configuration for module prioritization weights.
    
    This class allows customization of how modules are selected
    for improvement by adjusting weights for various metrics.
    """
    
    DEFAULT_WEIGHTS = {
        "complexity": 2.0,        # Higher complexity = higher priority
        "coverage_deficit": 1.5,  # Lower coverage = higher priority
        "maintainability_deficit": 1.0,  # Lower maintainability = higher priority
        "days_since_improvement": 0.5,  # More days = higher priority
        "days_max_value": 50.0,   # Maximum value for days factor
        "size_factor": 0.8,       # Larger files get higher priority
        "churn_factor": 1.2,      # Frequently changed files get higher priority
        "error_prone_factor": 2.5 # Files with many bug fixes get higher priority
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Optional path to the configuration file.
                         Defaults to 'memory/priority_weights.json'.
        """
        self.config_path = Path(config_path or "memory/priority_weights.json")
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.load_config()
        
    def load_config(self) -> Dict[str, float]:
        """
        Load configuration from the JSON file.
        
        Returns:
            Dict[str, float]: The loaded weights configuration
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_weights = json.load(f)
                    # Update only keys that exist in the default weights
                    for key in self.DEFAULT_WEIGHTS:
                        if key in loaded_weights:
                            self.weights[key] = float(loaded_weights[key])
                    logger.info(f"Loaded priority weights from {self.config_path}")
            else:
                logger.info("No custom priority weights found, using defaults")
                self.save_config()  # Save defaults
        except Exception as e:
            logger.error(f"Error loading weights: {e}")
            
        return self.weights
        
    def save_config(self) -> bool:
        """
        Save configuration to the JSON file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.weights, f, indent=2)
            
            logger.info(f"Saved priority weights to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving weights: {e}")
            return False
            
    def update_weight(self, key: str, value: float) -> bool:
        """
        Update a specific weight value.
        
        Args:
            key: The weight key to update
            value: The new weight value
            
        Returns:
            bool: True if successful, False otherwise
        """
        if key not in self.weights:
            logger.error(f"Unknown weight key: {key}")
            return False
            
        try:
            self.weights[key] = float(value)
            return self.save_config()
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid weight value: {e}")
            return False
            
    def update_weights(self, new_weights: Dict[str, float]) -> bool:
        """
        Update multiple weights at once.
        
        Args:
            new_weights: Dictionary of weight keys and values to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for key, value in new_weights.items():
                if key in self.weights:
                    self.weights[key] = float(value)
            
            return self.save_config()
        except Exception as e:
            logger.error(f"Error updating weights: {e}")
            return False
            
    def reset_to_defaults(self) -> bool:
        """
        Reset all weights to default values.
        
        Returns:
            bool: True if successful, False otherwise
        """
        self.weights = self.DEFAULT_WEIGHTS.copy()
        return self.save_config()
        
    def get_weight(self, key: str) -> float:
        """
        Get a specific weight value.
        
        Args:
            key: The weight key
            
        Returns:
            float: The weight value or 0.0 if not found
        """
        return self.weights.get(key, 0.0)
        
    def get_all_weights(self) -> Dict[str, float]:
        """
        Get all weight values.
        
        Returns:
            Dict[str, float]: All weight values
        """
        return self.weights.copy()
        
    def calculate_module_score(self, module_metrics: Dict[str, Any]) -> float:
        """
        Calculate a priority score for a module based on current weights.
        
        Args:
            module_metrics: Dictionary of module metrics
            
        Returns:
            float: The priority score (higher = higher priority)
        """
        score = 0.0
        
        # Extract metrics (with defaults for missing values)
        complexity = module_metrics.get("complexity", 0)
        coverage = module_metrics.get("coverage_percentage", 0)
        maintainability = module_metrics.get("maintainability_index", 0)
        days_since_improvement = module_metrics.get("days_since_improvement", 1000)
        lines_of_code = module_metrics.get("lines_of_code", 0)
        churn_rate = module_metrics.get("churn_rate", 0)
        error_fixes = module_metrics.get("error_fixes", 0)
        
        # Apply weights to metrics
        score += complexity * self.weights["complexity"]
        score += max(0, (100 - coverage)) * self.weights["coverage_deficit"]
        score += max(0, (100 - maintainability)) * self.weights["maintainability_deficit"]
        score += min(days_since_improvement * self.weights["days_since_improvement"], 
                    self.weights["days_max_value"])
        
        # Optional advanced metrics
        if lines_of_code > 0:
            score += (lines_of_code / 100) * self.weights["size_factor"]
        
        if churn_rate > 0:
            score += churn_rate * self.weights["churn_factor"]
            
        if error_fixes > 0:
            score += error_fixes * self.weights["error_prone_factor"]
            
        return score


def create_priority_config_cli():
    """Command-line interface for managing priority weights."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage module priority weights')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List weights command
    list_parser = subparsers.add_parser('list', help='List all weights')
    
    # Update weight command
    update_parser = subparsers.add_parser('update', help='Update a weight')
    update_parser.add_argument('key', help='Weight key to update')
    update_parser.add_argument('value', type=float, help='New weight value')
    
    # Reset weights command
    reset_parser = subparsers.add_parser('reset', help='Reset weights to defaults')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create config manager
    config = PriorityWeightingConfig()
    
    # Execute command
    if args.command == 'list':
        weights = config.get_all_weights()
        print("Current Priority Weights:")
        for key, value in weights.items():
            print(f"  {key}: {value}")
    
    elif args.command == 'update':
        success = config.update_weight(args.key, args.value)
        if success:
            print(f"Updated {args.key} to {args.value}")
        else:
            print(f"Failed to update {args.key}")
    
    elif args.command == 'reset':
        success = config.reset_to_defaults()
        if success:
            print("Reset all weights to defaults")
        else:
            print("Failed to reset weights")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    create_priority_config_cli() 