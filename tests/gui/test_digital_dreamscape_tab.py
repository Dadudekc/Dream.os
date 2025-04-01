import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from gui.tabs.DigitalDreamscapeTab import DigitalDreamscapeTab
from backend.template_loader import TemplateManager
from unittest.mock import MagicMock, patch

class TestDigitalDreamscapeTab:
    """Test suite for the DigitalDreamscapeTab and its components."""
    
    @pytest.fixture
    def app(self):
        """Create a QApplication instance for testing."""
        return QApplication([])
    
    @pytest.fixture
    def template_manager(self):
        """Create a mocked TemplateManager instance."""
        manager = MagicMock(spec=TemplateManager)
        manager.get_templates.return_value = {
            "test_template": {
                "name": "Test Template",
                "description": "A test template",
                "content": "Test content"
            }
        }
        return manager
    
    @pytest.fixture
    def chat_engine(self):
        """Create a mocked chat engine instance."""
        engine = MagicMock()
        engine.execute_prompt.return_value = "Test response"
        return engine
    
    @pytest.fixture
    def tab(self, app, template_manager, chat_engine):
        """Create a DigitalDreamscapeTab instance for testing."""
        tab = DigitalDreamscapeTab(chat_engine=chat_engine, template_manager=template_manager)
        yield tab
        tab.close()
    
    def test_tab_initialization(self, tab):
        """Test that the tab initializes correctly with all components."""
        # Check that all major panels are created
        assert hasattr(tab, 'template_control_panel')
        assert hasattr(tab, 'context_management_panel')
        assert hasattr(tab, 'cycle_feedback_panel')
        assert hasattr(tab, 'adaptive_loop_panel')
        assert hasattr(tab, 'template_watchdog_panel')
        assert hasattr(tab, 'metrics_dashboard_panel')
        assert hasattr(tab, 'prompt_debug_panel')
        assert hasattr(tab, 'episode_publishing_panel')
        assert hasattr(tab, 'cursor_integration_panel')
    
    def test_view_mode_changes(self, tab):
        """Test that view mode changes affect the UI appropriately."""
        # Test compact mode
        tab.view_mode.setCurrentText("Compact")
        assert tab.compact_mode is True
        assert tab.minimalist_mode is False
        
        # Test minimalist mode
        tab.view_mode.setCurrentText("Minimalist")
        assert tab.compact_mode is True
        assert tab.minimalist_mode is True
        
        # Test standard mode
        tab.view_mode.setCurrentText("Standard")
        assert tab.compact_mode is False
        assert tab.minimalist_mode is False
    
    def test_theme_toggle(self, tab):
        """Test that theme toggle works correctly."""
        # Test dark mode toggle
        tab.toggle_theme.setChecked(True)
        assert tab.dark_mode is True
        
        tab.toggle_theme.setChecked(False)
        assert tab.dark_mode is False
    
    def test_template_control_panel(self, tab, template_manager):
        """Test template control panel functionality."""
        # Test template refresh
        tab.template_control_panel.refresh_templates()
        template_manager.get_templates.assert_called_once()
        
        # Test template activation signal
        with patch.object(tab.context_management_panel, 'update_template_preview') as mock_update:
            tab.template_control_panel.template_activated.emit("test_template")
            mock_update.assert_called_once_with("test_template")
    
    def test_prompt_debug_panel(self, tab, chat_engine):
        """Test prompt debug panel functionality."""
        test_prompt = "Test prompt"
        
        # Set prompt text
        tab.prompt_debug_panel.prompt_input.setPlainText(test_prompt)
        assert tab.prompt_debug_panel.prompt_input.toPlainText() == test_prompt
        
        # Test prompt execution
        with patch.object(tab.prompt_debug_panel, 'execute_prompt') as mock_execute:
            QTest.mouseClick(tab.prompt_debug_panel.execute_button, Qt.LeftButton)
            mock_execute.assert_called_once()
    
    def test_cycle_feedback_panel(self, tab):
        """Test cycle feedback panel functionality."""
        # Test autonomous mode toggle
        tab.adaptive_loop_panel.autonomous_toggle.setChecked(True)
        assert tab.cycle_feedback_panel.autonomous_mode is True
        
        tab.adaptive_loop_panel.autonomous_toggle.setChecked(False)
        assert tab.cycle_feedback_panel.autonomous_mode is False
    
    def test_metrics_dashboard_update(self, tab):
        """Test metrics dashboard updates."""
        test_metrics = {
            "cycle_success_rate": 0.85,
            "avg_response_quality": 0.92,
            "template_usage": {"test_template": 10},
            "time_to_adapt": 1.5
        }
        
        # Update metrics
        with patch.object(tab.metrics_dashboard_panel, 'update_metrics') as mock_update:
            tab.metrics = test_metrics
            tab.metrics_dashboard_panel.update_metrics()
            mock_update.assert_called_once()
    
    def test_episode_publishing(self, tab):
        """Test episode publishing functionality."""
        test_episode = {
            "title": "Test Episode",
            "summary": "Test summary",
            "content": "Test content"
        }
        
        # Test episode publishing signal
        with patch.object(tab.cursor_integration_panel.prompt_text, 'setPlainText') as mock_set_text:
            tab.episode_publishing_panel.episode_published.emit(test_episode)
            expected_text = f"Create code for: {test_episode['title']}\n{test_episode['summary']}"
            mock_set_text.assert_called_once_with(expected_text)
    
    def test_cleanup(self, tab):
        """Test cleanup when tab is closed."""
        with patch.object(tab.update_timer, 'stop') as mock_stop:
            with patch.object(tab.template_watchdog_panel, 'stop_watchdog') as mock_watchdog_stop:
                tab.closeEvent(None)
                mock_stop.assert_called_once()
                mock_watchdog_stop.assert_called_once()
    
    def test_ui_density_changes(self, tab):
        """Test UI density changes propagate to all components."""
        components = [
            tab.template_control_panel,
            tab.context_management_panel,
            tab.cycle_feedback_panel,
            tab.adaptive_loop_panel,
            tab.template_watchdog_panel,
            tab.metrics_dashboard_panel,
            tab.prompt_debug_panel,
            tab.episode_publishing_panel,
            tab.cursor_integration_panel
        ]
        
        # Test compact mode propagation
        tab.ui_density_changed.emit(True)
        for component in components:
            if hasattr(component, 'set_compact_mode'):
                assert component.compact_mode is True
        
        # Test standard mode propagation
        tab.ui_density_changed.emit(False)
        for component in components:
            if hasattr(component, 'set_compact_mode'):
                assert component.compact_mode is False 
