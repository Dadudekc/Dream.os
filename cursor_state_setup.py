#!/usr/bin/env python3
"""
Cursor State Setup

This script configures and registers the StatefulCursorManager with the system loader,
creating necessary directories and setting up integration points. Run this script
before using the overnight improvements functionality.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/cursor_setup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CursorStateSetup")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from core.StatefulCursorManager import StatefulCursorManager
from core.system_loader import initialize_system

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Set up the StatefulCursorManager')
    parser.add_argument('--config', type=str, default='config/system_config.yml',
                      help='Path to config file')
    parser.add_argument('--reset', action='store_true',
                      help='Reset existing state if present')
    return parser.parse_args()

def setup_directories():
    """Create necessary directories for state persistence."""
    # Create memory directory
    memory_dir = Path("memory")
    memory_dir.mkdir(exist_ok=True)
    logger.info(f"Ensured memory directory exists: {memory_dir.absolute()}")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Ensured logs directory exists: {logs_dir.absolute()}")
    
    return memory_dir

def setup_cursor_manager(config_path, memory_dir, reset_state=False):
    """Set up and register the StatefulCursorManager."""
    # State file path
    state_file_path = memory_dir / "cursor_state.json"
    
    # Check if we need to reset existing state
    if reset_state and state_file_path.exists():
        logger.info(f"Resetting existing state file: {state_file_path}")
        # Create a backup first
        backup_path = state_file_path.with_suffix(".json.bak")
        state_file_path.rename(backup_path)
        logger.info(f"Created backup at: {backup_path}")
    
    try:
        # Initialize the system loader with config
        logger.info(f"Initializing system with config: {config_path}")
        system = initialize_system(config_path)
        
        # Get config manager from the system
        config_manager = system.get_service("config_manager")
        
        # Initialize the StatefulCursorManager
        logger.info(f"Creating StatefulCursorManager with state file: {state_file_path}")
        cursor_manager = StatefulCursorManager(
            config_manager=config_manager,
            state_file_path=str(state_file_path)
        )
        
        # Load any existing state
        cursor_manager.load_state()
        
        # Register the manager as a service
        logger.info("Registering StatefulCursorManager as a service")
        system.register_service("stateful_cursor_manager", cursor_manager)
        
        # Save initial state if we reset or if it's new
        if reset_state or not state_file_path.exists():
            cursor_manager.save_state()
            logger.info("Initialized and saved fresh state")
        
        return system, cursor_manager
    
    except Exception as e:
        logger.error(f"Error setting up StatefulCursorManager: {e}")
        raise

def create_test_data(cursor_manager):
    """Create some test data in the cursor manager."""
    # Only add test data if no history exists
    if not cursor_manager.state.get("improvement_history"):
        logger.info("Adding test data to demonstrate functionality")
        
        # Add test modules
        test_modules = [
            "core/CursorSessionManager.py",
            "core/StatefulCursorManager.py",
            "code_metrics.py"
        ]
        
        # Add some context for each module
        for module in test_modules:
            cursor_manager.update_context(module, "purpose", f"Manages {module.split('/')[-1].split('.')[0]} functionality")
            cursor_manager.update_context(module, "last_reviewed", "2023-04-04")
        
        # Add some test metrics
        metrics = {
            test_modules[0]: {"complexity": 8, "coverage_percentage": 70, "maintainability_index": 65},
            test_modules[1]: {"complexity": 12, "coverage_percentage": 85, "maintainability_index": 72},
            test_modules[2]: {"complexity": 6, "coverage_percentage": 90, "maintainability_index": 80}
        }
        cursor_manager.update_metrics_history(metrics)
        
        # Add some example improvements
        cursor_manager.add_improvement_record(
            module=test_modules[0],
            changes={"summary": "Improved error handling"},
            metrics_before={"complexity": 9, "coverage_percentage": 65},
            metrics_after={"complexity": 8, "coverage_percentage": 70}
        )
        
        # Save the test data
        cursor_manager.save_state()
        logger.info("Test data added and saved")

def main():
    """Main entry point for setup."""
    logger.info("Starting StatefulCursorManager setup...")
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Setup directories
        memory_dir = setup_directories()
        
        # Setup cursor manager
        system, cursor_manager = setup_cursor_manager(
            args.config, 
            memory_dir,
            args.reset
        )
        
        # Create test data if --reset was specified or it's a fresh start
        if args.reset or not Path(memory_dir / "cursor_state.json").exists():
            create_test_data(cursor_manager)
        
        logger.info("StatefulCursorManager setup completed successfully")
        
        # Print next steps
        print("\nSetup completed successfully!")
        print("Next steps:")
        print("1. Run the test script: python test_stateful_cursor.py")
        print("2. Run the example: python examples/stateful_cursor_integration.py")
        print("3. Run overnight improvements: python overnight_improvements.py")
        
        return 0
    
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 