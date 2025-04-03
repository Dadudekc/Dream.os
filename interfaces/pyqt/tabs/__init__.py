"""
PyQt Interface Tabs Module

This module provides the tab implementations for the Dream.OS PyQt interface.
"""

from .main_tab import MainTab
from .chat_tab import ChatTab, ChatTabManager, ChatTabWidget, ChatTabWidgetManager
from .ConfigurationTab import ConfigurationTab
from .LogsTab import LogsTab
from .SyncOpsTab import SyncOpsTab
from .prompt_sync import PromptSyncTab
from .contextual_chat import ContextualChatTab
from .task_board import TaskBoardTab
from .settings_tab import SettingsTab
from .SocialDashboardTab import SocialDashboardTab
from .PromptExecutionTab import PromptExecutionTab # Assuming FullSyncTab is not needed or defined elsewhere
from .DependencyMapTab import DependencyMapTab
from .voice_mode_tab import VoiceModeTab
from .unified_dashboard import UnifiedDashboardTab
from .meredith_tab import MeredithTab
from .draggable_prompt_board_tab import DraggablePromptBoardTab
from .metrics_viewer import MetricsViewerTab
# Note: Dreamscape tabs might need specific handling depending on usage
# from .dreamscape import DreamscapeTab, DreamscapeGenerationTab 

__all__ = [
    "MainTab",
    # "DreamscapeGenerationTab", # Removed until clarification
    "ConfigurationTab",
    "LogsTab",
    "SyncOpsTab",
    "ChatTab",
    "ChatTabManager",
    "ChatTabWidget",
    "ChatTabWidgetManager",
    "PromptSyncTab",
    "ContextualChatTab",
    "TaskBoardTab",
    "SettingsTab",
    "SocialDashboardTab",
    "PromptExecutionTab",
    "DependencyMapTab",
    "VoiceModeTab",
    "UnifiedDashboardTab",
    "MeredithTab",
    "DraggablePromptBoardTab",
    "MetricsViewerTab",
    # Add other exported tabs as needed
]

"""
PyQt tab interfaces for Dream.OS
"""
