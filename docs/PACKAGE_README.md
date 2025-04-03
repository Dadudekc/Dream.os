# Chat Mate: AI-Powered Community Management

## Installation

### Development Installation

For development, install the package in editable mode:

```bash
# Method 1: Use the provided script
python install_dev.py

# Method 2: Install directly with pip
pip install -e .
```

This makes Python recognize your project structure and enables absolute imports.

### Production Installation

For production deployment:

```bash
pip install .
```

## Project Structure

The project follows a clean architecture with clear separation of concerns:

```
chat_mate/
├── core/            # Core business logic
│   ├── social/      # Social media integration
│   ├── agents/      # AI agents and tools
│   └── ...
├── interfaces/      # User interfaces
│   ├── pyqt/        # PyQT5 desktop interface
│   ├── web/         # Web interface (FastAPI)
│   └── cli/         # Command-line interface
├── services/        # Service layer
├── utils/           # Utility functions
└── tests/           # Test suite
```

## Running the Application

After installation, you can run the application in several ways:

```bash
# Method 1: Run as a module
python -m interfaces.pyqt

# Method 2: Run the main script directly
python interfaces/pyqt/dreamscape_gui.py
```

## Import Style

The project uses absolute imports for clarity and maintainability:

```python
# Correct import style
from core.social.CommunityDashboard import CommunityDashboard
from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow

# Avoid relative imports or sys.path manipulation
```

## Development Guidelines

1. **Namespace packages**: Every directory should have an `__init__.py` file
2. **Absolute imports**: Always use absolute imports from the project root
3. **No path manipulation**: Avoid using `sys.path.append()` or similar hacks
4. **Entry points**: Create proper entry points for modules with `__main__.py` 