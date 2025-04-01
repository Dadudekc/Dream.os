import os
import sys
import pytest
from pathlib import Path
from core.PathManager import PathManager
from core.TemplateManager import TemplateManager
from core.response_handler import PromptResponseHandler
from core.services.dreamscape.engine import DreamscapeGenerationService

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
print(f"[minimal_test.py] Current directory: {current_dir}")
print(f"[minimal_test.py] Project root: {project_root}")
# print(f"[minimal_test.py] Python path: {sys.path}") # Keep this commented unless needed

# Try to import the components directly in the script
success = True

try:
    from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab import DreamscapeGenerationTab
    print("[minimal_test.py] DreamscapeGenerationTab import success!")
except ImportError as e:
    print(f"[minimal_test.py] DreamscapeGenerationTab import failed: {e}")
    success = False

try:
    from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
    print("[minimal_test.py] UIManager import success!")
except ImportError as e:
    print(f"[minimal_test.py] UIManager import failed: {e}")
    success = False

try:
    from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
    print("[minimal_test.py] ContextManager import success!")
except ImportError as e:
    print(f"[minimal_test.py] ContextManager import failed: {e}")
    success = False

try:
    from interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer import ServiceInitializer
    print("[minimal_test.py] ServiceInitializer import success!")
except ImportError as e:
    print(f"[minimal_test.py] ServiceInitializer import failed: {e}")
    success = False

# Simple test function that can be discovered by pytest
def test_imports():
    """Test that all components can be imported within pytest context."""
    print("\n[minimal_test.py] Running test_imports() via pytest...")
    # print(f"[minimal_test.py test_imports] sys.path: {sys.path}") # Keep commented unless needed
    try:
        from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab import DreamscapeGenerationTab
        from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
        from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
        from interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer import ServiceInitializer
        print("[minimal_test.py test_imports] All imports successful!")
        assert True
    except ImportError as e:
        print(f"[minimal_test.py test_imports] Import error: {e}")
        assert False, f"Import error: {e}"

if __name__ == "__main__":
    print(f"[minimal_test.py] Overall direct import success: {success}") 
