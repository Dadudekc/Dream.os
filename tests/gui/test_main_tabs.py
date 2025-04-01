"""
Tests for the MainTabs component of the PyQt5 GUI.
"""

import pytest
from PyQt5.QtWidgets import QTabWidget, QTabBar
from PyQt5.QtCore import Qt

from chat_mate.gui.tabs.MainTabs import MainTabs


class TestMainTabs:
    """Test suite for the MainTabs component."""
    
    def test_main_tabs_init(self, qapp, qtbot):
        """Test that MainTabs initializes correctly."""
        # Arrange & Act
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Assert
        assert isinstance(main_tabs, QTabWidget)
        assert main_tabs.count() == 4  # Should have 4 tabs
        assert main_tabs.tabText(0) == "Dreamscape Generation"
        assert main_tabs.tabText(1) == "Community Management"
        assert main_tabs.tabText(2) == "Analytics"
        assert main_tabs.tabText(3) == "Settings"
    
    def test_tab_properties(self, qapp, qtbot):
        """Test that the tab properties are set correctly."""
        # Arrange & Act
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Assert
        assert main_tabs.tabPosition() == QTabWidget.North
        assert main_tabs.tabShape() == QTabWidget.Rounded
        assert main_tabs.isMovable() is True
        assert main_tabs.tabsClosable() is False
        assert main_tabs.usesScrollButtons() is True
        assert main_tabs.elideMode() == Qt.ElideRight
    
    def test_tab_bar_properties(self, qapp, qtbot):
        """Test that the tab bar properties are set correctly."""
        # Arrange & Act
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        tab_bar = main_tabs.tabBar()
        
        # Assert
        assert tab_bar.isExpanding() is False
        assert tab_bar.drawBase() is True
    
    def test_tab_tooltips(self, qapp, qtbot):
        """Test that tab tooltips are set correctly."""
        # Arrange & Act
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Assert
        assert main_tabs.tabToolTip(0) == "Generate and manage dreamscape content"
        assert main_tabs.tabToolTip(1) == "Manage community interactions and engagement"
        assert main_tabs.tabToolTip(2) == "View analytics and performance metrics"
        assert main_tabs.tabToolTip(3) == "Configure application settings"
    
    def test_tab_dimensions(self, qapp, qtbot):
        """Test that the tab dimensions are set correctly."""
        # Arrange & Act
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Assert
        assert main_tabs.minimumWidth() == 800
        assert main_tabs.minimumHeight() == 600
    
    def test_set_managers(self, qapp, qtbot, mock_config_manager, mock_analytics_manager, mock_community_manager, mock_chat_manager):
        """Test that the set_managers method updates all tab managers correctly."""
        # Arrange
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Mock the update_managers methods in the tabs
        original_dreamscape_update = main_tabs.dreamscape_tab.update_managers
        original_community_update = main_tabs.community_tab.update_managers
        original_analytics_update = main_tabs.analytics_tab.update_managers
        original_settings_update = main_tabs.settings_tab.update_managers
        
        # Create tracking variables
        dreamscape_called = [False]
        community_called = [False]
        analytics_called = [False]
        settings_called = [False]
        
        def mock_dreamscape_update(**kwargs):
            dreamscape_called[0] = True
            return original_dreamscape_update(**kwargs)
            
        def mock_community_update(**kwargs):
            community_called[0] = True
            return original_community_update(**kwargs)
            
        def mock_analytics_update(**kwargs):
            analytics_called[0] = True
            return original_analytics_update(**kwargs)
            
        def mock_settings_update(**kwargs):
            settings_called[0] = True
            return original_settings_update(**kwargs)
        
        # Replace methods with mocks
        main_tabs.dreamscape_tab.update_managers = mock_dreamscape_update
        main_tabs.community_tab.update_managers = mock_community_update
        main_tabs.analytics_tab.update_managers = mock_analytics_update
        main_tabs.settings_tab.update_managers = mock_settings_update
        
        # Act
        main_tabs.set_managers(
            prompt_manager=None,
            chat_manager=mock_chat_manager,
            response_handler=None,
            memory_manager=None,
            discord_manager=None,
            community_manager=mock_community_manager,
            analytics_manager=mock_analytics_manager,
            config_manager=mock_config_manager
        )
        
        # Assert
        assert main_tabs.chat_manager == mock_chat_manager
        assert main_tabs.community_manager == mock_community_manager
        assert main_tabs.analytics_manager == mock_analytics_manager
        assert main_tabs.config_manager == mock_config_manager
        
        # Verify update methods were called
        assert dreamscape_called[0] is True
        assert community_called[0] is True
        assert analytics_called[0] is True
        assert settings_called[0] is True
    
    def test_tab_switching(self, qapp, qtbot):
        """Test that tab switching works correctly."""
        # Arrange
        main_tabs = MainTabs()
        qtbot.addWidget(main_tabs)
        
        # Initial tab should be 0
        assert main_tabs.currentIndex() == 0
        
        # Act - Switch to tab 2
        main_tabs.setCurrentIndex(2)
        
        # Assert
        assert main_tabs.currentIndex() == 2
        assert main_tabs.currentWidget() == main_tabs.analytics_tab
        
        # Act - Switch to settings tab
        main_tabs.setCurrentWidget(main_tabs.settings_tab)
        
        # Assert
        assert main_tabs.currentIndex() == 3
        assert main_tabs.currentWidget() == main_tabs.settings_tab 
