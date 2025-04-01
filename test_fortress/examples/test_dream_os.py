#!/usr/bin/env python3
"""
Example: Testing Dream.OS with Test Fortress

This example demonstrates how to use Test Fortress to test Dream.OS subsystems,
focusing on the PromptCycleOrchestrator as an example.
"""

import json
import logging
import sys
from pathlib import Path

from dream_os.orchestrator import PromptCycleOrchestrator
from test_fortress.runners.orchestrator_test_runner import run_orchestrator_tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_fortress.example')

def create_example_template() -> str:
    """Create an example failure template file."""
    template = {
        "templates": [
            {
                "name": "task_timeout_example",
                "description": "Example test for task timeout handling",
                "type": "task_timeout",
                "task_id": "example_task",
                "timeout_duration": 10,
                "validation": {
                    "verify_retry_count": 2,
                    "tasks_recovered": True,
                    "state_consistent": True,
                    "logs_valid": True
                },
                "expected_logs": [
                    "Task example_task timed out",
                    "Initiating retry sequence",
                    "Task recovery completed"
                ]
            },
            {
                "name": "race_condition_example",
                "description": "Example test for race condition handling",
                "type": "race_condition",
                "concurrent_tasks": [
                    {
                        "id": "task1",
                        "priority": 1,
                        "dependencies": []
                    },
                    {
                        "id": "task2",
                        "priority": 2,
                        "dependencies": ["task1"]
                    }
                ],
                "validation": {
                    "verify_task_order": ["task1", "task2"],
                    "state_consistent": True,
                    "logs_valid": True
                }
            }
        ],
        "metadata": {
            "version": "1.0",
            "validation_rules": {
                "state_recovery_timeout": 5
            }
        }
    }
    
    # Save template to file
    template_file = Path('example_templates.json')
    with open(template_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    return str(template_file)

def run_example():
    """Run example Test Fortress test suite."""
    try:
        logger.info("Starting Test Fortress example")
        
        # Create example template
        template_path = create_example_template()
        logger.info(f"Created example template: {template_path}")
        
        # Create orchestrator instance
        logger.info("Initializing PromptCycleOrchestrator")
        orchestrator = PromptCycleOrchestrator()
        
        # Run tests
        logger.info("Running Test Fortress tests")
        summary = run_orchestrator_tests(orchestrator, template_path)
        
        # Display results
        print("\n=== Test Results ===")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Duration: {summary['duration']:.2f}s")
        
        if summary['failed'] > 0:
            print("\nFailed Tests:")
            for result in summary['results']:
                if not result['success']:
                    print(f"- {result['name']}: {result.get('error', 'Unknown error')}")
                    if 'validation' in result:
                        print("  Validation Results:")
                        for check, value in result['validation'].items():
                            print(f"    {check}: {'PASS' if value else 'FAIL'}")
        
        # Cleanup
        Path(template_path).unlink()
        logger.info("Example completed")
        
        return 0 if summary['failed'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Error running example: {str(e)}")
        return 1

def main():
    """Example entry point."""
    sys.exit(run_example())

if __name__ == '__main__':
    main()

"""
Example Usage:

1. Install Test Fortress:
   pip install -e .

2. Run the example:
   python examples/test_dream_os.py

3. Using the CLI:
   test-fortress --subsystem orchestrator --templates example_templates.json

4. With custom options:
   test-fortress --subsystem orchestrator \\
                --templates example_templates.json \\
                --output results \\
                --log-level DEBUG \\
                --report-format json \\
                --fail-fast

The example demonstrates:
- Creating failure templates
- Initializing the test runner
- Running failure injection tests
- Handling test results
- Using the Test Fortress CLI
""" 