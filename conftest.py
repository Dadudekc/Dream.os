import sys
from pathlib import Path

# Determine the project root (adjust as necessary)
project_root = Path(__file__).parent.resolve()
# Insert project root into sys.path so imports work as expected.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"[conftest.py] Added project root to sys.path: {project_root}") 
