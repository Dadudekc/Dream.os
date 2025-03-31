#!/usr/bin/env python3
"""
Lifecycle Hooks Loader
=====================

Provides dynamic loading of lifecycle hook modules that can be executed at 
various points in the task execution process. Hooks allow for customization
of the task lifecycle without modifying core code.

Features:
- Dynamic discovery and loading of hook modules from configured paths
- Support for task-specific hooks based on task type
- Validation of hook module structure and interface
- Versioned hooks with compatibility checking
"""

import os
import sys
import json
import importlib
import logging
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Define hook types and their execution points
class HookType:
    """Types of hooks that can be registered in the system"""
    PRE_TASK = "pre_task"          # Before task execution starts
    POST_TASK = "post_task"        # After task execution completes
    TASK_ERROR = "task_error"      # When task execution fails
    PRE_COMMIT = "pre_commit"      # Before committing changes to files
    POST_COMMIT = "post_commit"    # After committing changes to files
    MODEL_REQUEST = "model_request" # Before sending request to the model
    MODEL_RESPONSE = "model_response" # After receiving response from the model
    FILE_MODIFIED = "file_modified" # After a file is modified
    SYSTEM_STARTUP = "system_startup" # During system startup
    SYSTEM_SHUTDOWN = "system_shutdown" # During system shutdown
    CUSTOM = "custom"              # Custom hooks for specific applications

# Hook interface specification
class HookSpec:
    """Specification for a hook function"""
    def __init__(self, 
                 hook_type: str, 
                 expected_args: List[str], 
                 return_type: Optional[type] = None,
                 is_async: bool = False,
                 description: str = ""):
        self.hook_type = hook_type
        self.expected_args = expected_args
        self.return_type = return_type
        self.is_async = is_async
        self.description = description

# Define specifications for each hook type
HOOK_SPECS = {
    HookType.PRE_TASK: HookSpec(
        hook_type=HookType.PRE_TASK,
        expected_args=["task"],
        return_type=bool,
        is_async=False,
        description="Called before task execution. Return False to prevent execution."
    ),
    HookType.POST_TASK: HookSpec(
        hook_type=HookType.POST_TASK,
        expected_args=["task", "result"],
        return_type=None,
        is_async=False,
        description="Called after task execution with the task result."
    ),
    HookType.TASK_ERROR: HookSpec(
        hook_type=HookType.TASK_ERROR,
        expected_args=["task", "error"],
        return_type=None,
        is_async=False,
        description="Called when task execution fails with the error."
    ),
    HookType.PRE_COMMIT: HookSpec(
        hook_type=HookType.PRE_COMMIT,
        expected_args=["task", "changes"],
        return_type=Union[bool, Dict[str, Any]],
        is_async=False,
        description="Called before committing changes. Return False to prevent commit or modified changes."
    ),
    HookType.POST_COMMIT: HookSpec(
        hook_type=HookType.POST_COMMIT,
        expected_args=["task", "commit_info"],
        return_type=None,
        is_async=False,
        description="Called after committing changes with commit info."
    ),
    HookType.MODEL_REQUEST: HookSpec(
        hook_type=HookType.MODEL_REQUEST,
        expected_args=["task", "request"],
        return_type=Dict[str, Any],
        is_async=True,
        description="Called before sending request to the model. Return modified request."
    ),
    HookType.MODEL_RESPONSE: HookSpec(
        hook_type=HookType.MODEL_RESPONSE,
        expected_args=["task", "request", "response"],
        return_type=Dict[str, Any],
        is_async=True,
        description="Called after receiving response from the model. Return modified response."
    ),
    HookType.FILE_MODIFIED: HookSpec(
        hook_type=HookType.FILE_MODIFIED,
        expected_args=["task", "file_path", "action", "content"],
        return_type=None,
        is_async=False,
        description="Called after a file is modified."
    ),
    HookType.SYSTEM_STARTUP: HookSpec(
        hook_type=HookType.SYSTEM_STARTUP,
        expected_args=["config"],
        return_type=None,
        is_async=False,
        description="Called during system startup with configuration."
    ),
    HookType.SYSTEM_SHUTDOWN: HookSpec(
        hook_type=HookType.SYSTEM_SHUTDOWN,
        expected_args=[],
        return_type=None,
        is_async=False,
        description="Called during system shutdown."
    ),
    HookType.CUSTOM: HookSpec(
        hook_type=HookType.CUSTOM,
        expected_args=["name", "args"],
        return_type=Any,
        is_async=False,
        description="Custom hook with dynamic name and arguments."
    )
}

class HookValidationError(Exception):
    """Exception raised when a hook module fails validation"""
    pass

class HookModule:
    """Represents a loaded hook module with metadata"""
    def __init__(self, module, metadata):
        self.module = module
        self.metadata = metadata
        self.hooks = {}  # mapping of hook_type to hook function

    def get_hook(self, hook_type: str) -> Optional[Callable]:
        """Get the hook function for the specified hook type"""
        return self.hooks.get(hook_type)

class LifecycleHooksLoader:
    """
    Responsible for discovering, loading, and managing lifecycle hook modules.
    
    Attributes:
        hook_paths: List of paths to search for hook modules
        loaded_modules: Dictionary of loaded hook modules by name
        registered_hooks: Dictionary of registered hooks by type
    """
    
    def __init__(self, hook_paths: List[str] = None):
        """
        Initialize the hooks loader.
        
        Args:
            hook_paths: List of paths to search for hook modules
        """
        self.hook_paths = hook_paths or ["hooks", "custom_hooks"]
        self.loaded_modules: Dict[str, HookModule] = {}
        self.registered_hooks: Dict[str, List[Tuple[str, Callable]]] = {
            hook_type: [] for hook_type in HOOK_SPECS.keys()
        }
        self.custom_hook_types: Set[str] = set()
        
        logger.info(f"LifecycleHooksLoader initialized with paths: {self.hook_paths}")
    
    def discover_hooks(self) -> List[str]:
        """
        Discover hook modules in the configured paths.
        
        Returns:
            List of hook module names
        """
        hook_module_paths = []
        
        for hook_path in self.hook_paths:
            if not os.path.exists(hook_path):
                logger.warning(f"Hook path not found: {hook_path}")
                continue
            
            # Add hook path to Python path temporarily
            if hook_path not in sys.path:
                sys.path.insert(0, hook_path)
            
            # Find Python files in the hook path
            for root, _, files in os.walk(hook_path):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        module_path = os.path.join(root, file)
                        rel_path = os.path.relpath(module_path, hook_path)
                        # Convert path to module name (remove .py, replace / with .)
                        module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                        hook_module_paths.append(module_name)
        
        logger.info(f"Discovered {len(hook_module_paths)} hook modules")
        return hook_module_paths
    
    def load_hooks(self, module_names: List[str] = None) -> Dict[str, HookModule]:
        """
        Load hook modules by name.
        
        Args:
            module_names: List of module names to load (if None, discover and load all)
            
        Returns:
            Dictionary of loaded hook modules
        """
        if module_names is None:
            module_names = self.discover_hooks()
        
        for module_name in module_names:
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Check for required metadata
                if not hasattr(module, "HOOK_METADATA"):
                    logger.warning(f"Skipping module {module_name} - missing HOOK_METADATA")
                    continue
                
                metadata = module.HOOK_METADATA
                
                # Validate metadata
                if not self._validate_metadata(module_name, metadata):
                    continue
                
                # Create hook module object
                hook_module = HookModule(module, metadata)
                
                # Find and validate hook functions
                for hook_type, spec in HOOK_SPECS.items():
                    hook_func_name = f"on_{hook_type}"
                    if hasattr(module, hook_func_name):
                        hook_func = getattr(module, hook_func_name)
                        if callable(hook_func):
                            # Validate hook function signature
                            if self._validate_hook_function(hook_func, spec):
                                hook_module.hooks[hook_type] = hook_func
                                # Register the hook
                                self.registered_hooks[hook_type].append((module_name, hook_func))
                                logger.debug(f"Registered hook {hook_type} from {module_name}")
                
                # Look for custom hooks (functions starting with on_custom_)
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if name.startswith("on_custom_"):
                        custom_hook_type = name[3:]  # Remove "on_" prefix
                        hook_module.hooks[custom_hook_type] = func
                        self.custom_hook_types.add(custom_hook_type)
                        
                        # Create a registration for this custom hook type if needed
                        if custom_hook_type not in self.registered_hooks:
                            self.registered_hooks[custom_hook_type] = []
                        
                        # Register the custom hook
                        self.registered_hooks[custom_hook_type].append((module_name, func))
                        logger.debug(f"Registered custom hook {custom_hook_type} from {module_name}")
                
                # Store the loaded module
                self.loaded_modules[module_name] = hook_module
                logger.info(f"Loaded hook module: {module_name}")
                
            except Exception as e:
                logger.error(f"Failed to load hook module {module_name}: {str(e)}")
        
        logger.info(f"Loaded {len(self.loaded_modules)} hook modules with {sum(len(hooks) for hooks in self.registered_hooks.values())} hooks")
        return self.loaded_modules
    
    def execute_hook(self, 
                    hook_type: str, 
                    task_id: Optional[str] = None, 
                    **kwargs) -> List[Any]:
        """
        Execute all registered hooks of the specified type.
        
        Args:
            hook_type: Type of hook to execute
            task_id: ID of the task context (for filtering task-specific hooks)
            **kwargs: Arguments to pass to the hook functions
            
        Returns:
            List of results from the hook functions
        """
        results = []
        
        # Get hooks for this type
        hooks = self.registered_hooks.get(hook_type, [])
        if not hooks:
            logger.debug(f"No hooks registered for type: {hook_type}")
            return results
        
        for module_name, hook_func in hooks:
            try:
                # Check if this hook should be executed for this task
                module = self.loaded_modules.get(module_name)
                if module and task_id:
                    # Check if hook has task type filtering
                    task_types = module.metadata.get("task_types", [])
                    if task_types and "task" in kwargs:
                        task = kwargs.get("task", {})
                        if task.get("task_type") not in task_types:
                            logger.debug(f"Skipping hook {hook_type} from {module_name} - task type mismatch")
                            continue
                
                # Execute the hook
                if hook_type in HOOK_SPECS and HOOK_SPECS[hook_type].is_async:
                    # For async hooks, we need to run them with await
                    # This needs to be handled by the caller
                    results.append((module_name, hook_func, kwargs))
                else:
                    # For sync hooks, we can just call them
                    result = hook_func(**kwargs)
                    results.append(result)
                    logger.debug(f"Executed hook {hook_type} from {module_name}")
            except Exception as e:
                logger.error(f"Error executing hook {hook_type} from {module_name}: {str(e)}")
        
        return results
    
    def get_hooks_for_type(self, hook_type: str) -> List[Tuple[str, Callable]]:
        """
        Get all registered hooks of the specified type.
        
        Args:
            hook_type: Type of hook to get
            
        Returns:
            List of (module_name, hook_function) tuples
        """
        return self.registered_hooks.get(hook_type, [])
    
    def get_hook_types(self) -> List[str]:
        """
        Get all registered hook types, including custom hooks.
        
        Returns:
            List of hook types
        """
        return list(self.registered_hooks.keys())
    
    def _validate_metadata(self, module_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Validate hook module metadata.
        
        Args:
            module_name: Name of the module
            metadata: Metadata to validate
            
        Returns:
            True if metadata is valid, False otherwise
        """
        required_fields = ["name", "version", "description"]
        
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"Module {module_name} missing required metadata field: {field}")
                return False
        
        return True
    
    def _validate_hook_function(self, hook_func: Callable, spec: HookSpec) -> bool:
        """
        Validate a hook function against its specification.
        
        Args:
            hook_func: Hook function to validate
            spec: Hook specification
            
        Returns:
            True if function is valid, False otherwise
        """
        # Get function signature
        sig = inspect.signature(hook_func)
        
        # Check if all expected args are present
        for arg in spec.expected_args:
            if arg not in sig.parameters:
                logger.warning(f"Hook function {hook_func.__name__} missing required parameter: {arg}")
                return False
        
        # All validations passed
        return True
    
    def get_module_metadata(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a loaded hook module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Module metadata or None if not found
        """
        module = self.loaded_modules.get(module_name)
        if module:
            return module.metadata
        return None
    
    def get_hook_spec(self, hook_type: str) -> Optional[HookSpec]:
        """
        Get the specification for a hook type.
        
        Args:
            hook_type: Type of hook
            
        Returns:
            Hook specification or None if not found
        """
        if hook_type in HOOK_SPECS:
            return HOOK_SPECS[hook_type]
        return None
    
    def register_custom_hook_spec(self, 
                                 hook_type: str, 
                                 expected_args: List[str],
                                 return_type: Optional[type] = None,
                                 is_async: bool = False,
                                 description: str = "") -> None:
        """
        Register a specification for a custom hook type.
        
        Args:
            hook_type: Type of hook (must start with "custom_")
            expected_args: List of expected argument names
            return_type: Expected return type
            is_async: Whether the hook is asynchronous
            description: Description of the hook
        """
        if not hook_type.startswith("custom_"):
            hook_type = f"custom_{hook_type}"
        
        HOOK_SPECS[hook_type] = HookSpec(
            hook_type=hook_type,
            expected_args=expected_args,
            return_type=return_type,
            is_async=is_async,
            description=description
        )
        
        # Create a registration for this custom hook type if needed
        if hook_type not in self.registered_hooks:
            self.registered_hooks[hook_type] = []
        
        logger.info(f"Registered custom hook spec: {hook_type}")
    
    def save_hook_specs_to_json(self, file_path: str) -> None:
        """
        Save all hook specifications to a JSON file.
        
        Args:
            file_path: Path to save the specifications
        """
        specs_data = {}
        
        for hook_type, spec in HOOK_SPECS.items():
            specs_data[hook_type] = {
                "hook_type": spec.hook_type,
                "expected_args": spec.expected_args,
                "return_type": str(spec.return_type) if spec.return_type else None,
                "is_async": spec.is_async,
                "description": spec.description
            }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(specs_data, f, indent=2)
    
    def create_hook_module_template(self, 
                                   module_name: str, 
                                   hook_types: List[str],
                                   output_dir: str = None) -> str:
        """
        Create a template for a new hook module.
        
        Args:
            module_name: Name of the module
            hook_types: List of hook types to include
            output_dir: Directory to save the module (default: first hook path)
            
        Returns:
            Path to the created module file
        """
        if output_dir is None:
            output_dir = self.hook_paths[0]
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate module code
        code = [
            "#!/usr/bin/env python3",
            f'"""',
            f'Hook module: {module_name}',
            f'"""',
            "",
            "# Hook module metadata",
            "HOOK_METADATA = {",
            f'    "name": "{module_name}",',
            '    "version": "0.1.0",',
            f'    "description": "{module_name} hook module",',
            '    "author": "",',
            '    "task_types": []  # Empty means all task types',
            "}",
            ""
        ]
        
        # Add hook functions
        for hook_type in hook_types:
            if hook_type in HOOK_SPECS:
                spec = HOOK_SPECS[hook_type]
                
                # Generate function signature
                args_str = ", ".join(spec.expected_args)
                
                code.extend([
                    f"def on_{hook_type}({args_str}):",
                    f'    """',
                    f'    {spec.description}',
                    f'',
                    f'    Args:',
                ])
                
                # Add parameter descriptions
                for arg in spec.expected_args:
                    code.append(f'        {arg}: Description of {arg}')
                
                # Add return description if applicable
                if spec.return_type is not None:
                    code.extend([
                        f'',
                        f'    Returns:',
                        f'        Description of return value',
                    ])
                
                code.extend([
                    f'    """',
                    f'    # Implement hook logic here',
                ])
                
                # Add return statement if applicable
                if spec.return_type is bool:
                    code.append(f'    return True')
                elif spec.return_type is not None:
                    if spec.return_type == Dict[str, Any]:
                        code.append(f'    return {}')
                    else:
                        code.append(f'    return None')
                
                code.append("")
        
        # Write to file
        file_path = os.path.join(output_dir, f"{module_name}.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(code))
        
        return file_path 