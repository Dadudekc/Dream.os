import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Python path:")
for path in sys.path:
    print(f"  - {path}")

print("\nTrying to import config module...")
try:
    from core.config.config_manager import ConfigManager
    print("Successfully imported ConfigManager")
except ImportError as e:
    print("Failed to import ConfigManager:", str(e))
    import traceback
    traceback.print_exc() 
