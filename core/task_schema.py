#!/usr/bin/env python3
"""
TaskSchema - Schema definitions for task validation
==================================================

Defines the schema for task objects and provides utilities for validating
task inputs against the schema. This ensures that all tasks have the required
fields and that field values conform to expected types and formats.

The module includes:
1. Field definitions with types, validation rules, and documentation
2. Schema definition for task objects
3. Validation utilities for tasks and related objects
4. Default/example task templates
"""

import re
import uuid
import json
import jsonschema
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Set

# Type definitions
TaskId = str  # UUID string
T = TypeVar('T')  # Generic type for validation functions

class Priority(str, Enum):
    """Priority levels for tasks"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, Enum):
    """Status values for tasks"""
    PENDING = "pending"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    """Types of tasks that can be processed"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    REFACTORING = "refactoring"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    CUSTOM = "custom"

# Schema definition
TASK_SCHEMA = {
    "type": "object",
    "required": ["task_id", "task_type", "description", "priority", "status"],
    "properties": {
        "task_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            "description": "Unique identifier for the task (UUID)"
        },
        "task_type": {
            "type": "string",
            "enum": [t.value for t in TaskType],
            "description": "Type of task to be performed"
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1000,
            "description": "Human-readable description of the task"
        },
        "priority": {
            "type": "string",
            "enum": [p.value for p in Priority],
            "description": "Priority level of the task"
        },
        "status": {
            "type": "string",
            "enum": [s.value for s in TaskStatus],
            "description": "Current status of the task"
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO timestamp when the task was created"
        },
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO timestamp when the task was last updated"
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            },
            "description": "List of task IDs that must be completed before this task"
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "description": "List of tags for categorizing the task"
        },
        "assignee": {
            "type": ["string", "null"],
            "description": "Name of the entity assigned to complete the task"
        },
        "metadata": {
            "type": "object",
            "description": "Additional task-specific metadata"
        },
        "progress": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Percentage of task completion (0-100)"
        },
        "estimated_duration_seconds": {
            "type": "number",
            "minimum": 0,
            "description": "Estimated time to complete the task in seconds"
        },
        "actual_duration_seconds": {
            "type": ["number", "null"],
            "minimum": 0,
            "description": "Actual time taken to complete the task in seconds"
        },
        "input_files": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of file paths that serve as inputs to the task"
        },
        "output_files": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of file paths that were modified or created by the task"
        },
        "parent_task_id": {
            "type": ["string", "null"],
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|^$",
            "description": "ID of the parent task if this is a subtask"
        },
        "retry_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of times the task has been retried"
        },
        "max_retries": {
            "type": "integer",
            "minimum": 0,
            "description": "Maximum number of retries allowed for this task"
        },
        "error": {
            "type": ["object", "null"],
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Error message if the task failed"
                },
                "type": {
                    "type": "string",
                    "description": "Type or category of error"
                },
                "traceback": {
                    "type": "string",
                    "description": "Stack trace for the error"
                }
            },
            "description": "Error details if the task failed"
        },
        "result": {
            "type": ["object", "null"],
            "description": "Result data from completed task"
        }
    },
    "additionalProperties": False
}

# Schema for task type-specific metadata
TYPE_SPECIFIC_SCHEMAS = {
    TaskType.CODE_GENERATION.value: {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "Programming language for the code generation"
            },
            "target_file": {
                "type": "string",
                "description": "Target file for the generated code"
            },
            "requirements": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of requirements for the code generation"
            },
            "context_files": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of files to provide context for generation"
            }
        }
    },
    TaskType.TEST_GENERATION.value: {
        "type": "object",
        "properties": {
            "source_file": {
                "type": "string",
                "description": "Source file to generate tests for"
            },
            "test_framework": {
                "type": "string",
                "description": "Testing framework to use (e.g., pytest, jest)"
            },
            "coverage_target": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Target coverage percentage"
            }
        }
    },
    TaskType.REFACTORING.value: {
        "type": "object",
        "properties": {
            "target_files": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Files to refactor"
            },
            "refactoring_type": {
                "type": "string",
                "description": "Type of refactoring to perform"
            },
            "preserve_behavior": {
                "type": "boolean",
                "description": "Whether to ensure behavior is preserved"
            }
        }
    }
}

class ValidationError(Exception):
    """Exception raised for task validation errors"""
    def __init__(self, message: str, validation_errors: List[str] = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.message)
    
    def __str__(self):
        if self.validation_errors:
            return f"{self.message}: {', '.join(self.validation_errors)}"
        return self.message

def validate_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a task against the task schema.
    
    Args:
        task_data: Dictionary containing task data
        
    Returns:
        The validated task data
        
    Raises:
        ValidationError: If the task data is invalid
    """
    try:
        jsonschema.validate(instance=task_data, schema=TASK_SCHEMA)
        
        # If task has task_type specific metadata, validate it against the appropriate schema
        task_type = task_data.get("task_type")
        metadata = task_data.get("metadata", {})
        
        if task_type in TYPE_SPECIFIC_SCHEMAS and metadata:
            try:
                jsonschema.validate(instance=metadata, schema=TYPE_SPECIFIC_SCHEMAS[task_type])
            except jsonschema.exceptions.ValidationError as e:
                raise ValidationError(f"Invalid metadata for task type {task_type}", [e.message])
        
        return task_data
    except jsonschema.exceptions.ValidationError as e:
        raise ValidationError("Task validation failed", [e.message])

def create_task_id() -> TaskId:
    """Generate a new task ID (UUID4)"""
    return str(uuid.uuid4())

def create_task(
    task_type: Union[TaskType, str],
    description: str,
    priority: Union[Priority, str] = Priority.MEDIUM,
    dependencies: List[TaskId] = None,
    tags: List[str] = None,
    assignee: Optional[str] = None,
    metadata: Dict[str, Any] = None,
    parent_task_id: Optional[TaskId] = None,
    max_retries: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new task with the specified parameters.
    
    Args:
        task_type: Type of task
        description: Description of the task
        priority: Priority level (default: medium)
        dependencies: List of task IDs that must be completed first
        tags: List of tags for categorizing the task
        assignee: Name of the entity assigned to complete the task
        metadata: Additional task-specific metadata
        parent_task_id: ID of the parent task if this is a subtask
        max_retries: Maximum number of retries allowed
        **kwargs: Additional task fields
        
    Returns:
        A validated task dictionary
    """
    # Convert enum values to strings if needed
    if isinstance(task_type, TaskType):
        task_type = task_type.value
    if isinstance(priority, Priority):
        priority = priority.value
    
    # Create task with required fields
    from datetime import datetime
    now = datetime.now().isoformat()
    
    task = {
        "task_id": create_task_id(),
        "task_type": task_type,
        "description": description,
        "priority": priority,
        "status": TaskStatus.PENDING.value,
        "created_at": now,
        "updated_at": now,
        "dependencies": dependencies or [],
        "tags": tags or [],
        "assignee": assignee,
        "metadata": metadata or {},
        "progress": 0,
        "retry_count": 0,
        "max_retries": max_retries,
        "parent_task_id": parent_task_id
    }
    
    # Add any additional fields
    task.update(kwargs)
    
    # Validate and return
    return validate_task(task)

def create_code_generation_task(
    description: str,
    language: str,
    target_file: str,
    requirements: List[str] = None,
    context_files: List[str] = None,
    priority: Union[Priority, str] = Priority.MEDIUM,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a code generation task.
    
    Args:
        description: Description of the task
        language: Programming language
        target_file: Target file for the generated code
        requirements: List of requirements
        context_files: List of files to provide context
        priority: Priority level
        **kwargs: Additional task fields
        
    Returns:
        A validated code generation task
    """
    metadata = {
        "language": language,
        "target_file": target_file,
        "requirements": requirements or [],
        "context_files": context_files or []
    }
    
    return create_task(
        task_type=TaskType.CODE_GENERATION,
        description=description,
        priority=priority,
        metadata=metadata,
        **kwargs
    )

def create_test_generation_task(
    description: str,
    source_file: str,
    test_framework: str,
    coverage_target: float = 80.0,
    priority: Union[Priority, str] = Priority.MEDIUM,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test generation task.
    
    Args:
        description: Description of the task
        source_file: Source file to generate tests for
        test_framework: Testing framework to use
        coverage_target: Target coverage percentage
        priority: Priority level
        **kwargs: Additional task fields
        
    Returns:
        A validated test generation task
    """
    metadata = {
        "source_file": source_file,
        "test_framework": test_framework,
        "coverage_target": coverage_target
    }
    
    return create_task(
        task_type=TaskType.TEST_GENERATION,
        description=description,
        priority=priority,
        metadata=metadata,
        **kwargs
    )

def create_refactoring_task(
    description: str,
    target_files: List[str],
    refactoring_type: str,
    preserve_behavior: bool = True,
    priority: Union[Priority, str] = Priority.MEDIUM,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a refactoring task.
    
    Args:
        description: Description of the task
        target_files: Files to refactor
        refactoring_type: Type of refactoring
        preserve_behavior: Whether to ensure behavior is preserved
        priority: Priority level
        **kwargs: Additional task fields
        
    Returns:
        A validated refactoring task
    """
    metadata = {
        "target_files": target_files,
        "refactoring_type": refactoring_type,
        "preserve_behavior": preserve_behavior
    }
    
    return create_task(
        task_type=TaskType.REFACTORING,
        description=description,
        priority=priority,
        metadata=metadata,
        **kwargs
    )

def get_task_schema() -> Dict[str, Any]:
    """Get the full task schema definition"""
    return TASK_SCHEMA

def get_type_specific_schema(task_type: Union[TaskType, str]) -> Dict[str, Any]:
    """Get the schema for a specific task type's metadata"""
    if isinstance(task_type, TaskType):
        task_type = task_type.value
    
    return TYPE_SPECIFIC_SCHEMAS.get(task_type, {"type": "object"})

def is_valid_task_id(task_id: str) -> bool:
    """Check if a string is a valid task ID (UUID)"""
    pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    return bool(pattern.match(task_id))

def get_dependencies_closure(tasks: Dict[TaskId, Dict[str, Any]], task_id: TaskId) -> Set[TaskId]:
    """
    Get the complete set of dependencies for a task, including transitive dependencies.
    
    Args:
        tasks: Dictionary mapping task IDs to task data
        task_id: ID of the task to get dependencies for
        
    Returns:
        Set of all dependency task IDs
    """
    if task_id not in tasks:
        return set()
    
    dependencies = set(tasks[task_id].get("dependencies", []))
    for dep_id in list(dependencies):  # Create a copy to iterate over
        dependencies.update(get_dependencies_closure(tasks, dep_id))
    
    return dependencies

def export_schema_to_json(file_path: str) -> None:
    """
    Export the task schema to a JSON file.
    
    Args:
        file_path: Path to save the schema
    """
    schema_data = {
        "task_schema": TASK_SCHEMA,
        "type_specific_schemas": TYPE_SPECIFIC_SCHEMAS
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, indent=2)

def get_example_task() -> Dict[str, Any]:
    """Get an example task for reference"""
    return create_task(
        task_type=TaskType.CODE_GENERATION,
        description="Generate a utility function for parsing command line arguments",
        priority=Priority.MEDIUM,
        tags=["backend", "utilities"],
        assignee="cursor",
        metadata={
            "language": "python",
            "target_file": "src/utils/cli_parser.py",
            "requirements": ["Support positional arguments", "Support flags", "Support help text"]
        }
    ) 
