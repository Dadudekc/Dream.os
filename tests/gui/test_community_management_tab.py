"""
Tests for the Community Management Tab component of the PyQt5 GUI.
"""

import pytest
from PyQt5.QtWidgets import QWidget, QComboBox, QTableWidget
from PyQt5.QtCore import Qt

from chat_mate.gui.tabs.community_management_tab import CommunityManagementTab


class TestCommunityManagementTab:
    """Test suite for the Community Management Tab component."""
    
    def test_community_tab_init(self, qapp, qtbot):
        """Test that CommunityManagementTab initializes correctly."""
        # Arrange & Act
        tab = CommunityManagementTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab, QWidget)
        assert hasattr(tab, 'platform_combo')
        assert hasattr(tab, 'metrics_table')
        assert hasattr(tab, 'refresh_btn')
    
    def test_platform_combo_initialization(self, qapp, qtbot):
        """Test that the platform combo box initializes with correct platforms."""
        # Arrange & Act
        tab = CommunityManagementTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab.platform_combo, QComboBox)
        
        # Check that the combo box contains typical social media platforms
        platform_items = [tab.platform_combo.itemText(i) for i in range(tab.platform_combo.count())]
        assert "Twitter" in platform_items
        assert "Facebook" in platform_items
        assert "Reddit" in platform_items
    
    def test_metrics_table_initialization(self, qapp, qtbot):
        """Test that the metrics table initializes correctly."""
        # Arrange & Act
        tab = CommunityManagementTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab.metrics_table, QTableWidget)
        assert tab.metrics_table.columnCount() == 2
        assert tab.metrics_table.horizontalHeaderItem(0).text() == "Metric"
        assert tab.metrics_table.horizontalHeaderItem(1).text() == "Value"
    
    def test_refresh_metrics_empty_manager(self, qapp, qtbot):
        """Test refresh_metrics when community_manager is None."""
        # Arrange
        tab = CommunityManagementTab()  # No manager provided
        qtbot.addWidget(tab)
        
        # Act - Should not raise exception
        tab.refresh_metrics()
        
        # Assert - Table should still be initialized but empty
        assert tab.metrics_table.rowCount() == 0
    
    def test_refresh_metrics_with_manager(self, qapp, qtbot, mock_community_manager, mock_analytics_manager):
        """Test refresh_metrics with a community manager."""
        # Arrange
        tab = CommunityManagementTab(
            community_manager=mock_community_manager,
            analytics_manager=mock_analytics_manager
        )
        qtbot.addWidget(tab)
        
        # Mock the refresh_metrics method to track if it was called
        original_refresh = tab.refresh_metrics
        refresh_called = [False]
        
        def mock_refresh():
            refresh_called[0] = True
            return original_refresh()
        
        tab.refresh_metrics = mock_refresh
        
        # Act
        tab.refresh_metrics()
        
        # Assert
        assert refresh_called[0] is True
    
    def test_update_managers(self, qapp, qtbot, mock_community_manager, mock_analytics_manager):
        """Test that update_managers properly updates both managers."""
        # Arrange
        tab = CommunityManagementTab()
        qtbot.addWidget(tab)
        
        # Mock the refresh_metrics method
        original_refresh = tab.refresh_metrics
        refresh_called = [False]
        
        def mock_refresh():
            refresh_called[0] = True
            return original_refresh()
        
        tab.refresh_metrics = mock_refresh
        
        # Initial state
        assert tab.community_manager is None
        assert tab.analytics_manager is None
        
        # Act
        tab.update_managers(
            community_manager=mock_community_manager,
            analytics_manager=mock_analytics_manager
        )
        
        # Assert
        assert tab.community_manager == mock_community_manager
        assert tab.analytics_manager == mock_analytics_manager
        assert refresh_called[0] is True  # Should call refresh_metrics
    
    def test_execute_action(self, qapp, qtbot):
        """Test the execute_action method."""
        # Arrange
        tab = CommunityManagementTab()
        qtbot.addWidget(tab)
        
        # Act
        tab.execute_action("post", "Twitter")
        
        # Assert - Should update the content_input field
        assert "Executing post on Twitter" in tab.content_input.toPlainText() 