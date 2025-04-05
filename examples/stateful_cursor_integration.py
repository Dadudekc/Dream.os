#!/usr/bin/env python3
"""
Example showing how to integrate the StatefulCursorManager with the system loader.
This demonstrates how to configure and register the StatefulCursorManager as a service.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StatefulCursorIntegration")

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Import project modules
from core.StatefulCursorManager import StatefulCursorManager
from core.system_loader import initialize_system

def setup_stateful_cursor_manager(config_path="config/system_config.yml"):
    """Set up and register the StatefulCursorManager with the system loader."""
    logger.info("Setting up StatefulCursorManager...")
    
    # Initialize the system loader with config
    system = initialize_system(config_path)
    
    # Get project root
    project_root = Path(root_dir)
    
    # Create memory directory if it doesn't exist
    memory_dir = project_root / "memory"
    memory_dir.mkdir(exist_ok=True)
    
    # State file path
    state_file_path = memory_dir / "cursor_state.json"
    
    # Get config manager from the system
    config_manager = system.get_service("config_manager")
    
    # Initialize the StatefulCursorManager
    cursor_manager = StatefulCursorManager(
        config_manager=config_manager,
        state_file_path=str(state_file_path)
    )
    
    # Load any existing state
    cursor_manager.load_state()
    
    # Register the manager as a service
    system.register_service("stateful_cursor_manager", cursor_manager)
    
    logger.info(f"StatefulCursorManager registered with state file: {state_file_path}")
    
    # Optional: Set up a shutdown hook to ensure state is saved
    import atexit
    def save_state_on_exit():
        logger.info("Saving cursor state on exit...")
        cursor_manager.save_state()
    
    atexit.register(save_state_on_exit)
    
    return system, cursor_manager

def example_usage(cursor_manager):
    """Example usage of the StatefulCursorManager."""
    logger.info("Demonstrating StatefulCursorManager usage...")
    
    # Example module to work with
    module_path = "core/StatefulCursorManager.py"
    
    # Store some context about this module
    cursor_manager.update_context(module_path, "primary_purpose", "State management for cursor sessions")
    cursor_manager.update_context(module_path, "improvement_focus", "Thread safety and error handling")
    
    # Simulate adding an improvement record
    cursor_manager.add_improvement_record(
        module=module_path,
        changes={"summary": "Added thread safety with locks"},
        metrics_before={"complexity": 12, "maintainability_index": 68},
        metrics_after={"complexity": 12, "maintainability_index": 72}
    )
    
    # Update metrics history
    metrics = {
        module_path: {
            "complexity": 12,
            "maintainability_index": 72,
            "coverage_percentage": 85
        }
    }
    cursor_manager.update_metrics_history(metrics)
    
    # Demonstrate retrieving information
    context = cursor_manager.get_context(module_path, "primary_purpose")
    history = cursor_manager.get_module_history(module_path)
    latest_metrics = cursor_manager.get_latest_metrics(module_path)
    
    logger.info(f"Retrieved context: {context}")
    logger.info(f"Module has {len(history)} improvement records")
    logger.info(f"Latest metrics: Complexity {latest_metrics.get('complexity')}, " 
                f"MI {latest_metrics.get('maintainability_index')}, "
                f"Coverage {latest_metrics.get('coverage_percentage')}%")
    
    # Generate a context-aware prompt
    prompt_context = cursor_manager.get_latest_prompt_context(module_path)
    logger.info(f"Generated prompt context: {prompt_context[:100]}...")
    
    # Save state to persist changes
    cursor_manager.save_state()
    logger.info("State saved successfully")

def main():
    """Main entry point for the example."""
    logger.info("Starting StatefulCursorManager integration example...")
    
    try:
        # Set up the system with the StatefulCursorManager
        system, cursor_manager = setup_stateful_cursor_manager()
        
        # Run example usage
        example_usage(cursor_manager)
        
        logger.info("Example completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error in example: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 