#!/usr/bin/env python3
"""
Test Runner for PromptCycleOrchestrator

Executes failure injection tests using the OrchestratorAdapter and failure templates.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..adapters.orchestrator_adapter import OrchestratorAdapter
from ..interfaces.testable import SubsystemRegistry, TestState

logger = logging.getLogger('test_fortress.orchestrator_runner')

class OrchestratorTestRunner:
    """Test runner for PromptCycleOrchestrator failure scenarios."""
    
    def __init__(self, orchestrator, template_path: str = None):
        """
        Initialize the test runner.
        
        Args:
            orchestrator: PromptCycleOrchestrator instance to test
            template_path: Path to failure templates JSON file
        """
        self.adapter = OrchestratorAdapter(orchestrator)
        self.template_path = template_path or 'test_fortress/templates/orchestrator_failures.json'
        self.templates = self._load_templates()
        self.results: List[Dict] = []
        
    def _load_templates(self) -> Dict:
        """Load failure templates from JSON file."""
        try:
            with open(self.template_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            return {'templates': []}
    
    def run_all_tests(self) -> Dict:
        """Run all failure templates and return results."""
        start_time = time.time()
        total_tests = len(self.templates.get('templates', []))
        passed = 0
        failed = 0
        
        logger.info(f"Starting orchestrator failure tests ({total_tests} templates)")
        
        for template in self.templates.get('templates', []):
            result = self.run_test(template)
            self.results.append(result)
            
            if result['success']:
                passed += 1
            else:
                failed += 1
                
            logger.info(f"Test '{template['name']}': {'PASS' if result['success'] else 'FAIL'}")
        
        duration = time.time() - start_time
        
        summary = {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'duration': duration,
            'results': self.results
        }
        
        self._save_results(summary)
        self._log_summary(summary)
        
        return summary
    
    def run_test(self, template: Dict) -> Dict:
        """Run a single failure test using the provided template."""
        try:
            logger.info(f"Running test: {template['name']}")
            
            # Capture initial state
            initial_state = self.adapter.capture_state()
            
            # Inject failure
            inject_success = self.adapter.inject_failure(template)
            if not inject_success:
                return {
                    'name': template['name'],
                    'success': False,
                    'error': 'Failed to inject failure'
                }
            
            # Allow time for recovery
            recovery_timeout = self.templates.get('metadata', {}).get(
                'validation_rules', {}).get('state_recovery_timeout', 60)
            time.sleep(recovery_timeout)
            
            # Validate recovery
            validation_result = self.adapter.validate_recovery(template)
            
            # Restore initial state
            self.adapter.restore_state(initial_state)
            
            result = {
                'name': template['name'],
                'success': validation_result['success'],
                'validation': validation_result.get('checks', {}),
                'error': validation_result.get('error')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error running test {template['name']}: {str(e)}")
            return {
                'name': template['name'],
                'success': False,
                'error': str(e)
            }
    
    def _save_results(self, summary: Dict):
        """Save test results to file."""
        try:
            results_dir = Path('test_fortress/results')
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            results_file = results_dir / f'orchestrator_test_results_{timestamp}.json'
            
            with open(results_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
            logger.info(f"Results saved to {results_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
    
    def _log_summary(self, summary: Dict):
        """Log test summary."""
        logger.info("\n=== Test Summary ===")
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Duration: {summary['duration']:.2f}s")
        
        if summary['failed'] > 0:
            logger.info("\nFailed Tests:")
            for result in summary['results']:
                if not result['success']:
                    logger.info(f"- {result['name']}: {result.get('error', 'Unknown error')}")

def run_orchestrator_tests(orchestrator, template_path: str = None) -> Dict:
    """
    Convenience function to run all orchestrator tests.
    
    Args:
        orchestrator: PromptCycleOrchestrator instance
        template_path: Optional path to failure templates
        
    Returns:
        Dict containing test results summary
    """
    runner = OrchestratorTestRunner(orchestrator, template_path)
    return runner.run_all_tests() 