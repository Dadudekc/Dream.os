"""
PyQt Interface Tabs Module

This module provides the tab implementations for the Dream.OS PyQt interface.
"""

from .main_tab import MainTab
from .chat_tab.ChatTab import ChatTab
from .chat_tab.ChatTabManager import ChatTabManager
from .chat_tab.ChatTabWidget import ChatTabWidget
from .chat_tab.ChatTabWidgetManager import ChatTabWidgetManager
from .ConfigurationTab import ConfigurationTab
from .LogsTab import LogsTab
from .SocialDashboardTab import SocialDashboardTab
from .SyncOpsTab import SyncOpsTab

__all__ = [
    "MainTab",
    "DreamscapeGenerationTab",
    "ConfigurationTab",
    "LogsTab",
    "SocialDashboardTab",
    "SyncOpsTab"
]

"""
PyQt tab interfaces for Dream.OS
"""
