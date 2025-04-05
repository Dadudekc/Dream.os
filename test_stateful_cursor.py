#!/usr/bin/env python3
"""
Test script for StatefulCursorManager functionality.
This script tests basic state persistence and retrieval operations.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StatefulCursorTest")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from core.StatefulCursorManager import StatefulCursorManager

def test_state_persistence():
    """Test basic state persistence functionality."""
    logger.info("Testing state persistence...")
    
    # Set up test file path
    test_state_path = "memory/test_cursor_state.json"
    
    # Create a temporary config manager mock
    class MockConfigManager:
        def get_config(self, key, default=None):
            return default
    
    # Initialize the manager with the test state file
    cursor_manager = StatefulCursorManager(
        config_manager=MockConfigManager(),
        state_file_path=test_state_path
    )
    
    # Test context operations
    test_module = "test_module.py"
    
    # Update context
    cursor_manager.update_context(test_module, "last_improvement", "2023-10-25")
    cursor_manager.update_context(test_module, "complexity_goal", 10)
    
    # Save state
    cursor_manager.save_state()
    logger.info(f"State saved to {test_state_path}")
    
    # Create a new manager instance to verify loading works
    new_manager = StatefulCursorManager(
        config_manager=MockConfigManager(),
        state_file_path=test_state_path
    )
    new_manager.load_state()
    
    # Verify context was loaded correctly
    last_improvement = new_manager.get_context(test_module, "last_improvement")
    complexity_goal = new_manager.get_context(test_module, "complexity_goal")
    
    logger.info(f"Retrieved context - last_improvement: {last_improvement}, complexity_goal: {complexity_goal}")
    
    assert last_improvement == "2023-10-25", f"Expected '2023-10-25', got '{last_improvement}'"
    assert complexity_goal == 10, f"Expected 10, got {complexity_goal}"
    
    # Test improvement records
    new_manager.add_improvement_record(
        module=test_module,
        changes={"summary": "Reduced cyclomatic complexity"},
        metrics_before={"complexity": 15, "coverage": 70},
        metrics_after={"complexity": 10, "coverage": 75}
    )
    
    # Save and reload again
    new_manager.save_state()
    
    third_manager = StatefulCursorManager(
        config_manager=MockConfigManager(),
        state_file_path=test_state_path
    )
    third_manager.load_state()
    
    # Verify improvement history
    module_history = third_manager.get_module_history(test_module)
    
    assert len(module_history) > 0, "No improvement history found"
    assert module_history[0]["metrics_delta"]["complexity"] == -5, "Expected complexity delta of -5"
    assert module_history[0]["metrics_delta"]["coverage"] == 5, "Expected coverage delta of 5"
    
    logger.info("Improvement record verified successfully")
    
    # Test metrics history
    metrics = {
        test_module: {"complexity": 10, "coverage": 75, "maintainability_index": 65}
    }
    third_manager.update_metrics_history(metrics)
    third_manager.save_state()
    
    # Load again and verify metrics
    fourth_manager = StatefulCursorManager(
        config_manager=MockConfigManager(),
        state_file_path=test_state_path
    )
    fourth_manager.load_state()
    latest_metrics = fourth_manager.get_latest_metrics(test_module)
    
    assert latest_metrics["complexity"] == 10, f"Expected complexity 10, got {latest_metrics.get('complexity')}"
    assert latest_metrics["maintainability_index"] == 65, f"Expected MI 65, got {latest_metrics.get('maintainability_index')}"
    
    logger.info("Metrics history verified successfully")
    
    # Cleanup
    if os.path.exists(test_state_path):
        os.remove(test_state_path)
        logger.info(f"Cleanup: Removed {test_state_path}")
    
    logger.info("All state persistence tests passed!")
    return True

def main():
    """Run all tests."""
    logger.info("Starting StatefulCursorManager tests...")
    
    try:
        test_state_persistence()
        logger.info("All tests passed!")
        return 0
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 