# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

# First, try to import PyQt5.sip directly and make it available
# This is a more direct approach than the sip_patcher
try:
    import PyQt5.sip
    import sys
    sys.modules['sip'] = PyQt5.sip
except Exception as e:
    # If direct import fails, fall back to the patcher
    from .sip_patcher import patch_sip_imports
    patch_sip_imports()

from . import DreamOsMainWindow
from . import IntegratedMainWindow
from . import __main__
from . import bootstrap
from . import dreamscape_gui
from . import dreamscape_services
from . import dreamscape_ui_logic
from . import feedback_dashboard

__all__ = [
    'DreamOsMainWindow',
    'IntegratedMainWindow',
    '__main__',
    'bootstrap',
    'dreamscape_gui',
    'dreamscape_services',
    'dreamscape_ui_logic',
    'feedback_dashboard',
]
