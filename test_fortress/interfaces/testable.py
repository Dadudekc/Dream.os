#!/usr/bin/env python3
"""
TestableSubsystem Interface

Defines the contract for making Dream.OS subsystems testable with Test Fortress.
Includes base interface, adapter pattern, and registration system.
"""

import abc
import json
import logging
from typing import Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger('test_fortress.testable')

@dataclass
class TestState:
    """Represents the state of a subsystem during testing."""
    logs: List[str]
    state_files: Dict[str, Path]
    memory_snapshot: Dict
    active_resources: List[str]
    error_state: Optional[Dict] = None

class TestableSubsystem(abc.ABC):
    """
    Interface for making subsystems testable by Test Fortress.
    
    Any Dream.OS subsystem that wants to support failure injection
    must implement this interface or use an adapter.
    """
    
    @abc.abstractmethod
    def inject_failure(self, template: Dict) -> bool:
        """
        Apply a failure scenario to the subsystem.
        
        Args:
            template: Failure template configuration
            
        Returns:
            Whether the failure was successfully injected
        """
        pass
    
    @abc.abstractmethod
    def validate_recovery(self, template: Dict) -> Dict:
        """
        Validate that the subsystem recovered from a failure.
        
        Args:
            template: Failure template with validation rules
            
        Returns:
            Validation results including state checks
        """
        pass
    
    @abc.abstractmethod
    def capture_state(self) -> TestState:
        """
        Capture the current state of the subsystem for validation.
        
        Returns:
            TestState containing logs, files, and memory state
        """
        pass
    
    @abc.abstractmethod
    def restore_state(self, state: TestState) -> bool:
        """
        Restore the subsystem to a previous state.
        
        Args:
            state: TestState to restore to
            
        Returns:
            Whether the state was successfully restored
        """
        pass

class SubsystemAdapter:
    """
    Base adapter for making existing subsystems testable.
    
    Use this as a base class to create specific adapters for
    different types of subsystems (e.g., MemoryManagerAdapter).
    """
    
    def __init__(self, subsystem: any):
        """
        Initialize the adapter.
        
        Args:
            subsystem: The subsystem instance to adapt
        """
        self.subsystem = subsystem
        self.state_dir = Path("test_fortress/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Track active resources for cleanup
        self.active_resources: List[str] = []
    
    def _save_state_file(self, name: str, data: Dict) -> Path:
        """Save state data to a file."""
        path = self.state_dir / f"{name}.json"
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return path
    
    def _load_state_file(self, path: Path) -> Dict:
        """Load state data from a file."""
        with open(path, 'r') as f:
            return json.load(f)
    
    def _track_resource(self, resource: str):
        """Track an active resource for cleanup."""
        self.active_resources.append(resource)
    
    def _release_resource(self, resource: str):
        """Release a tracked resource."""
        if resource in self.active_resources:
            self.active_resources.remove(resource)

class MemoryManagerAdapter(SubsystemAdapter, TestableSubsystem):
    """Adapter for making MemoryManager testable."""
    
    def inject_failure(self, template: Dict) -> bool:
        try:
            if template['type'] == 'memory_corruption':
                return self._inject_memory_corruption(template)
            elif template['type'] == 'file_not_found':
                return self._inject_missing_file(template)
            else:
                logger.warning(f"Unsupported failure type: {template['type']}")
                return False
        except Exception as e:
            logger.error(f"Error injecting failure: {str(e)}")
            return False
    
    def validate_recovery(self, template: Dict) -> Dict:
        try:
            state = self.capture_state()
            
            # Validate based on template rules
            results = {
                'state_valid': self._validate_memory_state(state.memory_snapshot),
                'resources_cleaned': len(self.active_resources) == 0,
                'logs_valid': self._validate_logs(state.logs, template)
            }
            
            return {
                'success': all(results.values()),
                'checks': results
            }
            
        except Exception as e:
            logger.error(f"Error validating recovery: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def capture_state(self) -> TestState:
        """Capture MemoryManager state."""
        try:
            return TestState(
                logs=self._capture_logs(),
                state_files={
                    'memory': self._save_state_file('memory', 
                                                  self.subsystem.get_memory_state())
                },
                memory_snapshot=self.subsystem.get_memory_state(),
                active_resources=self.active_resources.copy()
            )
        except Exception as e:
            logger.error(f"Error capturing state: {str(e)}")
            return TestState([], {}, {}, [])
    
    def restore_state(self, state: TestState) -> bool:
        """Restore MemoryManager state."""
        try:
            # Release any active resources
            for resource in self.active_resources:
                self._release_resource(resource)
            
            # Restore memory state
            if 'memory' in state.state_files:
                memory_state = self._load_state_file(state.state_files['memory'])
                self.subsystem.restore_memory_state(memory_state)
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring state: {str(e)}")
            return False
    
    def _inject_memory_corruption(self, template: Dict) -> bool:
        """Inject memory corruption scenario."""
        try:
            corrupt_data = template.get('corruption_scenario', {}).get('corrupt_data', {})
            self._track_resource('memory')
            self.subsystem.override_memory_state(corrupt_data)
            return True
        except Exception:
            return False
    
    def _inject_missing_file(self, template: Dict) -> bool:
        """Inject missing file scenario."""
        try:
            file_path = template.get('file_path', '')
            if not file_path:
                return False
                
            # Backup and remove file
            if Path(file_path).exists():
                self._track_resource(file_path)
                Path(file_path).rename(str(Path(file_path)) + '.backup')
            
            return True
        except Exception:
            return False
    
    def _validate_memory_state(self, state: Dict) -> bool:
        """Validate memory state structure."""
        required_fields = {'task_history', 'execution_results', 'metadata'}
        return all(field in state for field in required_fields)
    
    def _validate_logs(self, logs: List[str], template: Dict) -> bool:
        """Validate log messages match template."""
        expected_messages = template.get('validation', {}).get('verify_log_messages', [])
        return all(any(msg in log for log in logs) for msg in expected_messages)
    
    def _capture_logs(self) -> List[str]:
        """Capture relevant log messages."""
        # This would integrate with your logging system
        return []  # Replace with actual log capture

T = TypeVar('T', bound=TestableSubsystem)

class SubsystemRegistry:
    """
    Registry for testable subsystems.
    
    Manages the registration and retrieval of subsystem adapters,
    ensuring proper test integration across Dream.OS.
    """
    
    _registry: Dict[str, Type[TestableSubsystem]] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: Type[T]):
        """Register a subsystem adapter."""
        cls._registry[name] = adapter_class
    
    @classmethod
    def get_adapter(cls, name: str) -> Optional[Type[TestableSubsystem]]:
        """Get a registered adapter class."""
        return cls._registry.get(name)
    
    @classmethod
    def create_adapter(cls, name: str, subsystem: any) -> Optional[TestableSubsystem]:
        """Create an adapter instance for a subsystem."""
        adapter_class = cls.get_adapter(name)
        if adapter_class:
            return adapter_class(subsystem)
        return None
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List all registered adapters."""
        return list(cls._registry.keys()) 