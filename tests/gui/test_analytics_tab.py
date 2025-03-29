"""
Tests for the Analytics Tab component of the PyQt5 GUI.
"""

import pytest
from PyQt5.QtWidgets import QWidget, QComboBox, QTableWidget, QDateEdit
from PyQt5.QtCore import Qt

from chat_mate.gui.tabs.analytics_tab import AnalyticsTab


class TestAnalyticsTab:
    """Test suite for the Analytics Tab component."""
    
    def test_analytics_tab_init(self, qapp, qtbot):
        """Test that AnalyticsTab initializes correctly."""
        # Arrange & Act
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab, QWidget)
        assert hasattr(tab, 'platform_combo')
        assert hasattr(tab, 'date_range_combo')
        assert hasattr(tab, 'results_table')
        assert hasattr(tab, 'refresh_btn')
        assert hasattr(tab, 'export_btn')
    
    def test_platform_combo_initialization(self, qapp, qtbot):
        """Test that the platform combo box initializes correctly."""
        # Arrange & Act
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab.platform_combo, QComboBox)
        
        # All platforms should be available
        all_platforms = [tab.platform_combo.itemText(i) for i in range(tab.platform_combo.count())]
        assert "All Platforms" in all_platforms
        assert "Twitter" in all_platforms
        assert "Facebook" in all_platforms
    
    def test_date_range_combo_initialization(self, qapp, qtbot):
        """Test that the date range combo box initializes correctly."""
        # Arrange & Act
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab.date_range_combo, QComboBox)
        
        # Date ranges should be available
        date_ranges = [tab.date_range_combo.itemText(i) for i in range(tab.date_range_combo.count())]
        assert "Last 7 Days" in date_ranges
        assert "Last 30 Days" in date_ranges
        assert "Last 90 Days" in date_ranges
        assert "Custom Range" in date_ranges
    
    def test_custom_date_range_visibility(self, qapp, qtbot):
        """Test that custom date range fields toggle visibility correctly."""
        # Arrange
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Initial state - custom date range should be hidden
        assert hasattr(tab, 'start_date')
        assert hasattr(tab, 'end_date')
        assert not tab.start_date.isVisible()
        assert not tab.end_date.isVisible()
        
        # Act - Select custom range
        tab.date_range_combo.setCurrentText("Custom Range")
        
        # Assert
        assert tab.start_date.isVisible()
        assert tab.end_date.isVisible()
        
        # Act - Select non-custom range
        tab.date_range_combo.setCurrentText("Last 7 Days")
        
        # Assert
        assert not tab.start_date.isVisible()
        assert not tab.end_date.isVisible()
    
    def test_results_table_initialization(self, qapp, qtbot):
        """Test that the results table initializes correctly."""
        # Arrange & Act
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Assert
        assert isinstance(tab.results_table, QTableWidget)
        assert tab.results_table.columnCount() >= 2  # Should have at least metric and value columns
    
    def test_refresh_analytics_empty_manager(self, qapp, qtbot):
        """Test refresh_analytics when analytics_manager is None."""
        # Arrange
        tab = AnalyticsTab()  # No manager provided
        qtbot.addWidget(tab)
        
        # Act - Should not raise exception
        tab.refresh_analytics()
        
        # Assert
        # No assertion needed - just checking that it doesn't crash
    
    def test_refresh_analytics_with_manager(self, qapp, qtbot, mock_analytics_manager):
        """Test refresh_analytics with an analytics manager."""
        # Arrange
        tab = AnalyticsTab(analytics_manager=mock_analytics_manager)
        qtbot.addWidget(tab)
        
        # Act
        tab.refresh_analytics()
        
        # Assert
        # Check that table has been populated
        assert tab.results_table.rowCount() > 0
    
    def test_export_data(self, qapp, qtbot, mocker):
        """Test the export_data method."""
        # Arrange
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Mock QFileDialog.getSaveFileName
        mocker.patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', 
                    return_value=('test_export.csv', 'CSV Files (*.csv)'))
        
        # Mock file operations
        mock_open = mocker.patch('builtins.open', mocker.mock_open())
        
        # Act
        tab.export_data()
        
        # Assert
        mock_open.assert_called_once_with('test_export.csv', 'w', newline='')
        assert tab.results_table.rowCount() >= 1  # Table should have at least one confirmation row
    
    def test_update_managers(self, qapp, qtbot, mock_analytics_manager):
        """Test that update_managers properly updates the analytics manager."""
        # Arrange
        tab = AnalyticsTab()
        qtbot.addWidget(tab)
        
        # Mock the refresh_analytics method
        original_refresh = tab.refresh_analytics
        refresh_called = [False]
        
        def mock_refresh():
            refresh_called[0] = True
            return original_refresh()
        
        tab.refresh_analytics = mock_refresh
        
        # Initial state
        assert tab.analytics_manager is None
        
        # Act
        tab.update_managers(analytics_manager=mock_analytics_manager)
        
        # Assert
        assert tab.analytics_manager == mock_analytics_manager
        assert refresh_called[0] is True  # Should call refresh_analytics 