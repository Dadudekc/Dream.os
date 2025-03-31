#!/usr/bin/env python3
"""
Core services for Cursor enhanced operations.
"""

# Debug, Fix, and Rollback services
from core.services.debug_service import DebugService
from core.services.fix_service import FixService
from core.services.rollback_service import RollbackService

# Prompt execution
try:
    from core.services.prompt_execution_service import UnifiedPromptService
except ImportError:
    # Fallback for testing
    UnifiedPromptService = None

# New services
try:
    from core.services.TestGeneratorService import TestGeneratorService
except ImportError:
    # Fallback for testing
    TestGeneratorService = None
    
try:
    from core.services.TestCoverageAnalyzer import TestCoverageAnalyzer
except ImportError:
    # Fallback for testing
    TestCoverageAnalyzer = None

try:
    from core.services.PromptLifecycleHooksService import (
        PromptLifecycleHooksService,
        basic_validation_hook,
        priority_normalization_hook,
        sanitize_prompt_hook
    )
except ImportError:
    # Fallback for testing
    PromptLifecycleHooksService = None
    basic_validation_hook = None
    priority_normalization_hook = None
    sanitize_prompt_hook = None

__all__ = [
    # Legacy services
    'DebugService',
    'FixService',
    'RollbackService',
    'UnifiedPromptService',
    
    # New services
    'TestGeneratorService',
    'TestCoverageAnalyzer',
    'PromptLifecycleHooksService',
    
    # Utility hooks
    'basic_validation_hook',
    'priority_normalization_hook',
    'sanitize_prompt_hook'
]
