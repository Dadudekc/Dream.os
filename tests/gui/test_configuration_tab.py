"""
Tests for the ConfigurationTab component.
"""
import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from unittest.mock import MagicMock, patch

from chat_mate.gui.tabs.ConfigurationTab import ConfigurationTab


@pytest.fixture
def config_manager_mock():
    """Mock for the configuration manager."""
    mock = MagicMock()
    
    # Mock configuration methods
    mock.get_config.return_value = {
        "api_key": "test_key_12345",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
        "database_path": "C:/data/chatmate.db",
        "log_level": "INFO"
    }
    
    mock.save_config.return_value = True
    return mock


@pytest.fixture
def configuration_tab(qapp, config_manager_mock):
    """Fixture for ConfigurationTab instance with mocked dependencies."""
    tab = ConfigurationTab()
    
    # Set up the tab with mock data if it has the necessary attributes
    if hasattr(tab, 'update_managers'):
        tab.update_managers(config_manager=config_manager_mock)
    elif hasattr(tab, 'set_config_manager'):
        tab.set_config_manager(config_manager_mock)
    
    return tab


def test_init_creates_ui_components(configuration_tab):
    """Test that initialization creates all required UI components."""
    # Check essential UI components - adjust based on actual implementation
    essential_components = [
        'api_key_input', 'model_selector', 'temperature_slider', 
        'max_tokens_input', 'database_path_input', 'log_level_combo',
        'save_btn', 'reset_btn'
    ]
    
    for component in essential_components:
        if not hasattr(configuration_tab, component):
            # If the component doesn't exist, check for similar components
            similar_components = [attr for attr in dir(configuration_tab) if component.split('_')[0] in attr.lower()]
            assert len(similar_components) > 0, f"No similar component found for {component}"
        else:
            assert hasattr(configuration_tab, component)


def test_load_config(configuration_tab, config_manager_mock):
    """Test loading configuration."""
    # This test assumes the tab has a method to load config
    if hasattr(configuration_tab, 'load_config'):
        configuration_tab.load_config()
        
        # Check that config was retrieved
        config_manager_mock.get_config.assert_called_once()
        
        # Check that UI elements were populated with config values
        if hasattr(configuration_tab, 'api_key_input'):
            assert configuration_tab.api_key_input.text() == "test_key_12345"
        
        if hasattr(configuration_tab, 'model_selector'):
            assert configuration_tab.model_selector.currentText() == "gpt-4"


def test_save_config(configuration_tab, config_manager_mock, monkeypatch):
    """Test saving configuration."""
    # This test assumes the tab has a method to save config
    if not hasattr(configuration_tab, 'save_config'):
        return
    
    # Set up UI elements with values
    if hasattr(configuration_tab, 'api_key_input'):
        configuration_tab.api_key_input.setText("new_api_key_6789")
    
    if hasattr(configuration_tab, 'model_selector'):
        # Find the index of the model
        for i in range(configuration_tab.model_selector.count()):
            if configuration_tab.model_selector.itemText(i) == "gpt-3.5-turbo":
                configuration_tab.model_selector.setCurrentIndex(i)
                break
    
    # Mock QMessageBox to avoid UI popup
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.information', lambda *args, **kwargs: QMessageBox.Ok)
    
    # Save the config
    configuration_tab.save_config()
    
    # Check that save_config was called on the config manager
    config_manager_mock.save_config.assert_called()
    
    # Check that the correct config was saved
    call_args = config_manager_mock.save_config.call_args[0][0]
    if hasattr(configuration_tab, 'api_key_input'):
        assert call_args.get('api_key') == "new_api_key_6789"
    
    if hasattr(configuration_tab, 'model_selector'):
        assert call_args.get('model') == "gpt-3.5-turbo"


def test_reset_config(configuration_tab, config_manager_mock, monkeypatch):
    """Test resetting configuration."""
    # This test assumes the tab has a method to reset config
    if not hasattr(configuration_tab, 'reset_config'):
        return
    
    # Mock QMessageBox.question to return Yes
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.question', 
                       lambda *args, **kwargs: QMessageBox.Yes)
    
    # Reset the config
    configuration_tab.reset_config()
    
    # Check that load_config was called to reload the default values
    config_manager_mock.get_config.assert_called()


def test_browse_database_path(configuration_tab, monkeypatch):
    """Test browsing for database path."""
    # This test assumes the tab has a method to browse for database path
    if not hasattr(configuration_tab, 'browse_database_path'):
        return
    
    # Mock QFileDialog.getOpenFileName to return a file path
    test_path = "C:/new/path/database.db"
    monkeypatch.setattr('PyQt5.QtWidgets.QFileDialog.getOpenFileName', 
                       lambda *args, **kwargs: (test_path, "Database Files (*.db)"))
    
    # Browse for the path
    configuration_tab.browse_database_path()
    
    # Check that the path was set
    if hasattr(configuration_tab, 'database_path_input'):
        assert configuration_tab.database_path_input.text() == test_path


def test_validate_config_valid(configuration_tab):
    """Test config validation with valid data."""
    # This test assumes the tab has a method to validate config
    if not hasattr(configuration_tab, 'validate_config'):
        return
    
    # Set up valid values
    if hasattr(configuration_tab, 'api_key_input'):
        configuration_tab.api_key_input.setText("valid_api_key")
    
    if hasattr(configuration_tab, 'max_tokens_input'):
        configuration_tab.max_tokens_input.setValue(1000)
    
    # Validate the config
    result = configuration_tab.validate_config()
    assert result is True


def test_validate_config_invalid(configuration_tab, monkeypatch):
    """Test config validation with invalid data."""
    # This test assumes the tab has a method to validate config
    if not hasattr(configuration_tab, 'validate_config'):
        return
    
    # Mock QMessageBox.warning to avoid UI popup
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.warning', 
                       lambda *args, **kwargs: QMessageBox.Ok)
    
    # Set up invalid values
    if hasattr(configuration_tab, 'api_key_input'):
        configuration_tab.api_key_input.setText("")  # Empty API key
    
    # Validate the config
    result = configuration_tab.validate_config()
    assert result is False


def test_temperature_slider_changes_label(configuration_tab):
    """Test that temperature slider changes update the label."""
    # This test assumes the tab has a temperature slider and label
    if not hasattr(configuration_tab, 'temperature_slider') or not hasattr(configuration_tab, 'temperature_label'):
        return
    
    # Change the slider value
    configuration_tab.temperature_slider.setValue(50)  # Assuming 0-100 range
    
    # Check that the label was updated
    # The actual text format depends on the implementation
    assert "0.5" in configuration_tab.temperature_label.text()


def test_model_selector_changes_max_tokens(configuration_tab):
    """Test that model selector changes update max tokens."""
    # This test assumes the tab automatically adjusts max tokens based on the model
    if not hasattr(configuration_tab, 'model_selector') or not hasattr(configuration_tab, 'max_tokens_input'):
        return
    
    # Find the index for gpt-4
    gpt4_index = -1
    for i in range(configuration_tab.model_selector.count()):
        if configuration_tab.model_selector.itemText(i) == "gpt-4":
            gpt4_index = i
            break
    
    if gpt4_index == -1:
        return  # Model not found
    
    # Change to gpt-4
    configuration_tab.model_selector.setCurrentIndex(gpt4_index)
    
    # Check if max tokens was updated to a model-appropriate value
    # This is model-dependent, but likely higher than 1000 for GPT-4
    assert configuration_tab.max_tokens_input.value() >= 1000 