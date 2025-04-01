#!/usr/bin/env python3
"""
PromptCycleOrchestrator Test Adapter

Adapts the PromptCycleOrchestrator for Test Fortress integration.
Handles failure injection and validation for orchestration cycles.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..interfaces.testable import TestableSubsystem, SubsystemAdapter, TestState, SubsystemRegistry

logger = logging.getLogger('test_fortress.orchestrator')

class OrchestratorAdapter(SubsystemAdapter, TestableSubsystem):
    """Adapter for testing PromptCycleOrchestrator."""
    
    def __init__(self, orchestrator):
        """
        Initialize the orchestrator adapter.
        
        Args:
            orchestrator: PromptCycleOrchestrator instance
        """
        super().__init__(orchestrator)
        
        # Track active tasks and their states
        self.active_tasks: Dict[str, Dict] = {}
        self.task_history: List[Dict] = []
        
        # Register failure handlers
        self.failure_handlers = {
            'task_timeout': self._inject_task_timeout,
            'execution_error': self._inject_execution_error,
            'invalid_state': self._inject_invalid_state,
            'race_condition': self._inject_race_condition
        }
    
    def inject_failure(self, template: Dict) -> bool:
        """Inject a failure into the orchestrator."""
        try:
            failure_type = template.get('type')
            if failure_type not in self.failure_handlers:
                logger.warning(f"Unsupported failure type: {failure_type}")
                return False
            
            # Capture pre-failure state
            pre_state = self.capture_state()
            
            # Inject the failure
            success = self.failure_handlers[failure_type](template)
            
            if not success:
                # Restore state if injection failed
                self.restore_state(pre_state)
                
            return success
            
        except Exception as e:
            logger.error(f"Error injecting failure: {str(e)}")
            return False
    
    def validate_recovery(self, template: Dict) -> Dict:
        """Validate orchestrator recovery from failure."""
        try:
            state = self.capture_state()
            
            # Validate based on template rules
            results = {
                'tasks_recovered': self._validate_task_recovery(state),
                'state_consistent': self._validate_state_consistency(state),
                'logs_valid': self._validate_logs(state.logs, template),
                'resources_cleaned': len(self.active_resources) == 0
            }
            
            # Check specific validation rules from template
            validation_rules = template.get('validation', {})
            for rule, expected in validation_rules.items():
                if rule not in results:
                    results[rule] = self._validate_custom_rule(rule, expected, state)
            
            return {
                'success': all(results.values()),
                'checks': results
            }
            
        except Exception as e:
            logger.error(f"Error validating recovery: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def capture_state(self) -> TestState:
        """Capture orchestrator state."""
        try:
            # Get active tasks and history
            tasks_state = {
                'active_tasks': self.active_tasks.copy(),
                'task_history': self.task_history.copy()
            }
            
            # Save state to file
            state_file = self._save_state_file('orchestrator', tasks_state)
            
            return TestState(
                logs=self._capture_logs(),
                state_files={'orchestrator': state_file},
                memory_snapshot=tasks_state,
                active_resources=self.active_resources.copy()
            )
            
        except Exception as e:
            logger.error(f"Error capturing state: {str(e)}")
            return TestState([], {}, {}, [])
    
    def restore_state(self, state: TestState) -> bool:
        """Restore orchestrator state."""
        try:
            # Release active resources
            for resource in self.active_resources:
                self._release_resource(resource)
            
            # Restore state from file
            if 'orchestrator' in state.state_files:
                saved_state = self._load_state_file(state.state_files['orchestrator'])
                self.active_tasks = saved_state.get('active_tasks', {})
                self.task_history = saved_state.get('task_history', [])
                
                # Restore orchestrator internal state
                self.subsystem.restore_state(saved_state)
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring state: {str(e)}")
            return False
    
    def _inject_task_timeout(self, template: Dict) -> bool:
        """Inject a task timeout scenario."""
        try:
            task_id = template.get('task_id')
            if not task_id or task_id not in self.active_tasks:
                return False
            
            # Track the resource
            self._track_resource(f"task_{task_id}")
            
            # Simulate timeout
            self.subsystem.force_task_timeout(task_id)
            
            return True
        except Exception:
            return False
    
    def _inject_execution_error(self, template: Dict) -> bool:
        """Inject an execution error."""
        try:
            error_type = template.get('error_type', 'generic')
            task_id = template.get('task_id')
            
            if not task_id:
                return False
            
            # Track the resource
            self._track_resource(f"task_{task_id}")
            
            # Inject error
            self.subsystem.force_execution_error(task_id, error_type)
            
            return True
        except Exception:
            return False
    
    def _inject_invalid_state(self, template: Dict) -> bool:
        """Inject an invalid state scenario."""
        try:
            invalid_state = template.get('invalid_state', {})
            
            # Track state modification
            self._track_resource('orchestrator_state')
            
            # Force invalid state
            self.subsystem.override_state(invalid_state)
            
            return True
        except Exception:
            return False
    
    def _inject_race_condition(self, template: Dict) -> bool:
        """Inject a race condition scenario."""
        try:
            concurrent_tasks = template.get('concurrent_tasks', [])
            if not concurrent_tasks:
                return False
            
            # Track resources
            for task in concurrent_tasks:
                self._track_resource(f"task_{task['id']}")
            
            # Force concurrent execution
            self.subsystem.force_concurrent_execution(concurrent_tasks)
            
            return True
        except Exception:
            return False
    
    def _validate_task_recovery(self, state: TestState) -> bool:
        """Validate task recovery after failure."""
        try:
            tasks_state = state.memory_snapshot
            
            # Check if failed tasks were properly handled
            for task in tasks_state['task_history']:
                if task.get('status') == 'failed':
                    # Verify retry or cleanup happened
                    if not task.get('retry_count') and not task.get('cleaned_up'):
                        return False
            
            return True
        except Exception:
            return False
    
    def _validate_state_consistency(self, state: TestState) -> bool:
        """Validate orchestrator state consistency."""
        try:
            tasks_state = state.memory_snapshot
            
            # Check active tasks consistency
            for task_id, task in tasks_state['active_tasks'].items():
                # Verify task exists in history
                if not any(t['id'] == task_id for t in tasks_state['task_history']):
                    return False
                
                # Verify task status is valid
                if task['status'] not in {'queued', 'running', 'failed', 'completed'}:
                    return False
            
            return True
        except Exception:
            return False
    
    def _validate_custom_rule(self, rule: str, expected: any, state: TestState) -> bool:
        """Validate a custom rule from the template."""
        try:
            if rule == 'verify_retry_count':
                return self._validate_retry_count(expected, state)
            elif rule == 'verify_task_order':
                return self._validate_task_order(expected, state)
            else:
                return self._validate_generic_state(rule, expected)
        except Exception:
            return False
    
    def _validate_retry_count(self, expected: int, state: TestState) -> bool:
        """Validate task retry count."""
        try:
            tasks_state = state.memory_snapshot
            for task in tasks_state['task_history']:
                if task.get('retry_count', 0) > expected:
                    return False
            return True
        except Exception:
            return False
    
    def _validate_task_order(self, expected_order: List[str], state: TestState) -> bool:
        """Validate task execution order."""
        try:
            tasks_state = state.memory_snapshot
            actual_order = [task['id'] for task in tasks_state['task_history']]
            return actual_order == expected_order
        except Exception:
            return False

# Register the adapter
SubsystemRegistry.register('PromptCycleOrchestrator', OrchestratorAdapter) 