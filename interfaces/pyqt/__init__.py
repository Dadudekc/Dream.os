"""
Dream.OS PyQt Interface Module

This module provides the PyQt-based graphical user interface for Dream.OS.
"""

import logging

# Configure package-level logging
logger = logging.getLogger(__name__)

# Import all interface components
from .DreamOsMainWindow import DreamOsMainWindow

__version__ = "0.1.0"
__all__ = ['DreamOsMainWindow']
