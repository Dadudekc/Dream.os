#!/usr/bin/env python3
"""
Failure Validation Engine

Validates that failure scenarios are handled according to their templates.
Checks logs, file states, return values, and other validation conditions.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger('test_fortress.validator')

@dataclass
class ValidationResult:
    """Results of validating a failure scenario."""
    template_id: str
    success: bool
    checks_passed: Set[str]
    checks_failed: Set[str]
    error_details: Dict[str, str]
    validation_time: float
    
    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of passed checks."""
        total = len(self.checks_passed) + len(self.checks_failed)
        return (len(self.checks_passed) / total * 100) if total > 0 else 0.0

class FailureValidator:
    """
    Validates that failure scenarios are handled according to their templates.
    """
    
    def __init__(self, 
                 log_file: str = "test_fortress.log",
                 state_dir: str = "test_fortress/state",
                 backup_dir: str = "test_fortress/backups"):
        """
        Initialize the failure validator.
        
        Args:
            log_file: Path to the log file to check
            state_dir: Directory containing system state files
            backup_dir: Directory containing backup files
        """
        self.log_file = log_file
        self.state_dir = state_dir
        self.backup_dir = backup_dir
        
        # Ensure directories exist
        os.makedirs(state_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Cache log lines for performance
        self._log_lines: Optional[List[str]] = None
    
    def validate_scenario(self, template: Dict) -> ValidationResult:
        """
        Validate that a failure scenario was handled correctly.
        
        Args:
            template: The failure template to validate against
            
        Returns:
            ValidationResult containing pass/fail details
        """
        import time
        start_time = time.time()
        
        template_id = template.get('id', 'unknown')
        validation_rules = template.get('validation', {})
        
        checks_passed = set()
        checks_failed = set()
        error_details = {}
        
        # Validate each rule
        for rule, expected in validation_rules.items():
            try:
                if self._validate_rule(rule, expected, template):
                    checks_passed.add(rule)
                else:
                    checks_failed.add(rule)
                    error_details[rule] = f"Validation failed for {rule}"
            except Exception as e:
                checks_failed.add(rule)
                error_details[rule] = str(e)
        
        end_time = time.time()
        
        return ValidationResult(
            template_id=template_id,
            success=len(checks_failed) == 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            error_details=error_details,
            validation_time=end_time - start_time
        )
    
    def _validate_rule(self, rule: str, expected: any, template: Dict) -> bool:
        """
        Validate a specific rule against the system state.
        
        Args:
            rule: The validation rule to check
            expected: The expected value or condition
            template: The full template for context
            
        Returns:
            Whether the validation passed
        """
        # Log message validation
        if rule == 'verify_log_messages':
            return self._validate_log_messages(expected)
            
        # File state validation
        elif rule == 'verify_backup_created':
            return self._validate_backup_exists(template)
            
        # System state validation
        elif rule == 'verify_final_state':
            return self._validate_final_state(expected)
            
        # Memory state validation
        elif rule == 'verify_memory_state':
            return self._validate_memory_state(expected)
            
        # Lock validation
        elif rule == 'verify_lock_usage':
            return self._validate_lock_usage(template)
            
        # Generic state checks
        elif rule.startswith('verify_'):
            return self._validate_generic_state(rule, expected)
            
        else:
            raise ValueError(f"Unknown validation rule: {rule}")
    
    def _validate_log_messages(self, expected_messages: List[str]) -> bool:
        """Validate that expected log messages are present."""
        if self._log_lines is None:
            with open(self.log_file, 'r') as f:
                self._log_lines = f.readlines()
        
        # Check each expected message
        for message in expected_messages:
            if not any(message in line for line in self._log_lines):
                logger.error(f"Missing expected log message: {message}")
                return False
        
        return True
    
    def _validate_backup_exists(self, template: Dict) -> bool:
        """Validate that backup files were created."""
        target_file = template.get('corruption_scenario', {}).get('target_file')
        if not target_file:
            return False
            
        backup_path = os.path.join(self.backup_dir, 
                                  os.path.basename(target_file) + '.backup')
        return os.path.exists(backup_path)
    
    def _validate_final_state(self, expected_state: Dict) -> bool:
        """Validate the final state matches expectations."""
        try:
            with open(os.path.join(self.state_dir, 'final_state.json'), 'r') as f:
                actual_state = json.load(f)
                
            # Check each expected state field
            for key, value in expected_state.items():
                if actual_state.get(key) != value:
                    logger.error(f"State mismatch for {key}: "
                               f"expected {value}, got {actual_state.get(key)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating final state: {str(e)}")
            return False
    
    def _validate_memory_state(self, expected_state: Dict) -> bool:
        """Validate memory store state."""
        try:
            with open(os.path.join(self.state_dir, 'memory_state.json'), 'r') as f:
                memory_state = json.load(f)
                
            # Validate memory integrity
            if expected_state.get('has_valid_memory'):
                if not self._is_valid_memory(memory_state):
                    return False
            
            # Check if memory is empty when expected
            if expected_state.get('memory_is_empty'):
                if memory_state and len(memory_state) > 0:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating memory state: {str(e)}")
            return False
    
    def _validate_lock_usage(self, template: Dict) -> bool:
        """Validate proper lock usage in concurrent scenarios."""
        try:
            with open(os.path.join(self.state_dir, 'lock_trace.json'), 'r') as f:
                lock_trace = json.load(f)
            
            # Check lock acquisition order
            resources = set()
            current_locks = set()
            
            for event in lock_trace:
                if event['type'] == 'acquire':
                    resource = event['resource']
                    if resource in current_locks:
                        logger.error(f"Double lock on resource: {resource}")
                        return False
                    current_locks.add(resource)
                    resources.add(resource)
                elif event['type'] == 'release':
                    resource = event['resource']
                    if resource not in current_locks:
                        logger.error(f"Release of unacquired lock: {resource}")
                        return False
                    current_locks.remove(resource)
            
            # Ensure all locks were released
            if current_locks:
                logger.error(f"Unreleased locks: {current_locks}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating lock usage: {str(e)}")
            return False
    
    def _validate_generic_state(self, rule: str, expected: any) -> bool:
        """Validate generic state conditions."""
        try:
            # Extract the state key from the rule name
            state_key = rule.replace('verify_', '')
            
            with open(os.path.join(self.state_dir, 'generic_state.json'), 'r') as f:
                state = json.load(f)
            
            actual = state.get(state_key)
            if actual != expected:
                logger.error(f"State mismatch for {state_key}: "
                           f"expected {expected}, got {actual}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in generic state validation: {str(e)}")
            return False
    
    def _is_valid_memory(self, memory_state: Dict) -> bool:
        """Check if memory state is valid."""
        try:
            required_fields = {'task_history', 'execution_results', 'metadata'}
            return all(field in memory_state for field in required_fields)
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the cached log lines."""
        self._log_lines = None 