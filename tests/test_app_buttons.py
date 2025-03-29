import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from unittest.mock import MagicMock, patch
from interfaces.pyqt.tabs.CursorExecutionTab import CursorExecutionTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.LogsTab import LogsTab
from interfaces.pyqt.components.prompt_panel import PromptPanel
from interfaces.pyqt.components.community_dashboard_tab import CommunityDashboardTab

class TestCursorExecutionTab:
    """Test suite for CursorExecutionTab button functionality."""

    @pytest.fixture
    def execution_tab(self, qapp, mock_services):
        """Create a CursorExecutionTab instance for testing."""
        tab = CursorExecutionTab(**mock_services)
        return tab

    def test_run_prompt_button(self, execution_tab, mock_services):
        """Test that the Run Prompt button triggers execute_prompt()."""
        # Arrange
        with patch.object(execution_tab, 'execute_prompt') as mock_execute:
            # Act
            QTest.mouseClick(execution_tab.run_seq_button, Qt.LeftButton)
            
            # Assert
            mock_execute.assert_called_once()
            mock_services['logger'].info.assert_called_with("Executing prompt sequence...")

    def test_generate_tests_button(self, execution_tab, mock_services):
        """Test that the Generate Tests button triggers generate_tests()."""
        # Arrange
        with patch.object(execution_tab, 'generate_tests') as mock_generate:
            # Act
            QTest.mouseClick(execution_tab.generate_test_button, Qt.LeftButton)
            
            # Assert
            mock_generate.assert_called_once()
            mock_services['logger'].info.assert_called_with("Generating tests...")

    def test_git_commit_button(self, execution_tab, mock_services):
        """Test that the Git Commit button triggers commit_changes()."""
        # Arrange
        with patch.object(execution_tab, 'commit_changes') as mock_commit:
            # Act
            QTest.mouseClick(execution_tab.commit_button, Qt.LeftButton)
            
            # Assert
            mock_commit.assert_called_once()
            mock_services['logger'].info.assert_called_with("Committing changes...")

class TestConfigurationTab:
    """Test suite for ConfigurationTab button functionality."""

    @pytest.fixture
    def config_tab(self, qapp, mock_services):
        """Create a ConfigurationTab instance for testing."""
        tab = ConfigurationTab(**mock_services)
        return tab

    def test_exclusions_manager_button(self, config_tab, mock_services):
        """Test that the Exclusions Manager button opens the dialog."""
        # Arrange
        with patch('interfaces.pyqt.tabs.ConfigurationTab.ExclusionsDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance
            
            # Act
            QTest.mouseClick(config_tab.exclusions_button, Qt.LeftButton)
            
            # Assert
            mock_dialog.assert_called_once_with(config_tab)
            mock_instance.exec_.assert_called_once()
            mock_services['logger'].info.assert_called_with("Opened Exclusions Manager.")

    def test_discord_settings_button(self, config_tab, mock_services):
        """Test that the Discord Settings button opens the dialog."""
        # Arrange
        with patch.object(config_tab, 'open_discord_settings_dialog') as mock_open:
            # Act
            QTest.mouseClick(config_tab.discord_button, Qt.LeftButton)
            
            # Assert
            mock_open.assert_called_once()

    def test_reinforcement_tools_button(self, config_tab, mock_services):
        """Test that the Reinforcement Tools button opens the dialog."""
        # Arrange
        with patch.object(config_tab, 'open_reinforcement_tools_dialog') as mock_open:
            # Act
            QTest.mouseClick(config_tab.reinforcement_button, Qt.LeftButton)
            
            # Assert
            mock_open.assert_called_once()

class TestLogsTab:
    """Test suite for LogsTab button functionality."""

    @pytest.fixture
    def logs_tab(self, qapp, mock_services):
        """Create a LogsTab instance for testing."""
        tab = LogsTab(parent=None, logger=mock_services['logger'])
        return tab

    def test_clear_logs_button(self, logs_tab):
        """Test that the Clear Logs button clears the log display."""
        # Arrange
        logs_tab.log_display.append("Test log message")
        
        # Act
        clear_button = [btn for btn in logs_tab.findChildren(QPushButton) if btn.text() == "Clear Logs"][0]
        QTest.mouseClick(clear_button, Qt.LeftButton)
        
        # Assert
        assert logs_tab.log_display.toPlainText() == ""

class TestPromptPanel:
    """Test suite for PromptPanel button functionality."""

    @pytest.fixture
    def prompt_panel(self, qapp, mock_services):
        """Create a PromptPanel instance for testing."""
        panel = PromptPanel(**mock_services)
        return panel

    def test_add_custom_prompt_button(self, prompt_panel):
        """Test that the Add Custom Prompt button triggers add_custom_prompt()."""
        # Arrange
        with patch.object(prompt_panel, 'add_custom_prompt') as mock_add:
            # Act
            QTest.mouseClick(prompt_panel.add_custom_btn, Qt.LeftButton)
            
            # Assert
            mock_add.assert_called_once()

    def test_remove_custom_prompt_button(self, prompt_panel):
        """Test that the Remove Custom Prompt button triggers remove_custom_prompt()."""
        # Arrange
        with patch.object(prompt_panel, 'remove_custom_prompt') as mock_remove:
            # Act
            QTest.mouseClick(prompt_panel.remove_custom_btn, Qt.LeftButton)
            
            # Assert
            mock_remove.assert_called_once()

class TestCommunityDashboardTab:
    """Test suite for CommunityDashboardTab button functionality."""

    @pytest.fixture
    def dashboard_tab(self, qapp, mock_services):
        """Create a CommunityDashboardTab instance for testing."""
        tab = CommunityDashboardTab(**mock_services)
        return tab

    def test_refresh_data_button(self, dashboard_tab):
        """Test that the Refresh Data button triggers refresh_data()."""
        # Arrange
        with patch.object(dashboard_tab, 'refresh_data') as mock_refresh:
            # Act
            QTest.mouseClick(dashboard_tab.refresh_button, Qt.LeftButton)
            
            # Assert
            mock_refresh.assert_called_once()

    def test_generate_insights_button(self, dashboard_tab):
        """Test that the Generate Insights button triggers generate_insights()."""
        # Arrange
        with patch.object(dashboard_tab, 'generate_insights') as mock_generate:
            # Act
            QTest.mouseClick(dashboard_tab.insights_button, Qt.LeftButton)
            
            # Assert
            mock_generate.assert_called_once()

    def test_platform_selector_change(self, dashboard_tab):
        """Test that changing the platform selector triggers on_platform_changed()."""
        # Arrange
        with patch.object(dashboard_tab, 'on_platform_changed') as mock_change:
            # Act
            dashboard_tab.platform_selector.setCurrentIndex(1)
            
            # Assert
            mock_change.assert_called_once() 