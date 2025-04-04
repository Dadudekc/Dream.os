# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

# Remove original imports
# from . import ContextMemoryManager
# from . import TemplateRenderer

# Import specific classes to expose
from ..services.dreamscape.engine import DreamscapeGenerationService
# Use absolute import for ContextMemoryManager
# from chat_mate.core.dreamscape.ContextMemoryManager import ContextMemoryManager
# from .TemplateRenderer import TemplateRenderer # Keep TemplateRenderer if needed

# Re-enable if needed, ensure no circular imports
# from .TemplateRenderer import TemplateRenderer
# from .dreamscape_automation import DreamscapeAutomation

# Attempt to fix ModuleNotFoundError by importing from memory module
try:
    # Don't try to import from self - import from core.memory
    from core.memory.ContextMemoryManager import ContextMemoryManager 
    # Expose DreamscapeGenerationService if it's defined here or imported above
    # from .generation_service import DreamscapeGenerationService 
    # (Assuming DreamscapeGenerationService might be in its own file later)
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not import Dreamscape components: {e}")
    ContextMemoryManager = None # Define as None if import fails
    # DreamscapeGenerationService = None

__all__ = [
    'ContextMemoryManager',
    'DreamscapeGenerationService', 
    # 'TemplateRenderer', 
    # 'DreamscapeAutomation'
]
