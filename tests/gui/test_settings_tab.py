"""
Tests for the Settings Tab component of the PyQt5 GUI.
"""

import pytest
from PyQt5.QtWidgets import QWidget, QLineEdit, QComboBox, QSpinBox, QCheckBox
from PyQt5.QtCore import Qt

from chat_mate.gui.tabs.settings_tab import SettingsTab


class TestSettingsTab:
    """Test suite for the Settings Tab component."""
    
    def test_settings_tab_init(self, qapp, qtbot):
        """Test that SettingsTab initializes correctly."""
        # Arrange & Act
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Assert
        assert isinstance(settings_tab, QWidget)
        assert hasattr(settings_tab, 'openai_key')
        assert hasattr(settings_tab, 'linkedin_email')
        assert hasattr(settings_tab, 'linkedin_password')
        assert hasattr(settings_tab, 'twitter_email')
        assert hasattr(settings_tab, 'twitter_password')
        assert hasattr(settings_tab, 'facebook_email')
        assert hasattr(settings_tab, 'facebook_password')
        assert hasattr(settings_tab, 'instagram_email')
        assert hasattr(settings_tab, 'instagram_password')
        assert hasattr(settings_tab, 'reddit_username')
        assert hasattr(settings_tab, 'reddit_password')
        assert hasattr(settings_tab, 'stocktwits_username')
        assert hasattr(settings_tab, 'stocktwits_password')
    
    def test_password_fields_masked(self, qapp, qtbot):
        """Test that password fields are properly masked."""
        # Arrange & Act
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Assert - Check all password fields
        password_fields = [
            settings_tab.openai_key,
            settings_tab.linkedin_password,
            settings_tab.twitter_password,
            settings_tab.facebook_password,
            settings_tab.instagram_password,
            settings_tab.reddit_password,
            settings_tab.stocktwits_password
        ]
        
        for field in password_fields:
            assert isinstance(field, QLineEdit)
            assert field.echoMode() == QLineEdit.Password
    
    def test_placeholder_text(self, qapp, qtbot):
        """Test that fields have appropriate placeholder text."""
        # Arrange & Act
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Assert - Check sample of placeholders
        assert settings_tab.openai_key.placeholderText() == "Enter OpenAI API key"
        assert settings_tab.linkedin_email.placeholderText() == "Enter LinkedIn email"
        assert settings_tab.twitter_password.placeholderText() == "Enter Twitter password"
        assert settings_tab.reddit_username.placeholderText() == "Enter Reddit username"
    
    def test_general_settings_init(self, qapp, qtbot):
        """Test that general settings initialize with correct default values."""
        # Arrange & Act
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Assert
        assert isinstance(settings_tab.default_model, QComboBox)
        assert settings_tab.default_model.count() == 2  # Should have 2 models
        assert "gpt-4" in [settings_tab.default_model.itemText(i) for i in range(settings_tab.default_model.count())]
        
        assert isinstance(settings_tab.max_tokens, QSpinBox)
        assert settings_tab.max_tokens.minimum() == 100
        assert settings_tab.max_tokens.maximum() == 4000
        assert settings_tab.max_tokens.value() == 1000
        
        assert isinstance(settings_tab.temperature, QSpinBox)
        assert settings_tab.temperature.minimum() == 0
        assert settings_tab.temperature.maximum() == 100
        assert settings_tab.temperature.value() == 70
    
    def test_automation_settings_init(self, qapp, qtbot):
        """Test that automation settings initialize correctly."""
        # Arrange & Act
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Assert
        assert isinstance(settings_tab.auto_post, QCheckBox)
        assert isinstance(settings_tab.auto_engage, QCheckBox)
        assert isinstance(settings_tab.post_frequency, QSpinBox)
        
        assert settings_tab.post_frequency.minimum() == 1
        assert settings_tab.post_frequency.maximum() == 24
        assert settings_tab.post_frequency.value() == 4
    
    def test_validate_credentials_missing(self, qapp, qtbot):
        """Test validation when credentials are missing."""
        # Arrange
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Leave fields empty - validation should fail
        
        # Act
        result = settings_tab.validate_credentials()
        
        # Assert
        assert result is False
        assert "Missing credentials" in settings_tab.status_label.text()
        assert "color: #FFA500" in settings_tab.status_label.styleSheet()  # Orange warning color
    
    def test_validate_credentials_complete(self, qapp, qtbot):
        """Test validation when all credentials are provided."""
        # Arrange
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Fill in all credential fields
        credential_fields = [
            settings_tab.linkedin_email,
            settings_tab.linkedin_password,
            settings_tab.twitter_email,
            settings_tab.twitter_password,
            settings_tab.facebook_email,
            settings_tab.facebook_password,
            settings_tab.instagram_email,
            settings_tab.instagram_password,
            settings_tab.reddit_username,
            settings_tab.reddit_password,
            settings_tab.stocktwits_username,
            settings_tab.stocktwits_password
        ]
        
        for field in credential_fields:
            field.setText("test_value")
        
        # Act
        result = settings_tab.validate_credentials()
        
        # Assert
        assert result is True
        assert "All credentials provided" in settings_tab.status_label.text()
        assert "color: #4CAF50" in settings_tab.status_label.styleSheet()  # Green success color
    
    def test_save_settings_validates_first(self, qapp, qtbot, mocker):
        """Test that save_settings calls validate_credentials first."""
        # Arrange
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Mock the validate_credentials method
        mock_validate = mocker.patch.object(settings_tab, 'validate_credentials', return_value=False)
        mock_message_box = mocker.patch('PyQt5.QtWidgets.QMessageBox.warning')
        
        # Act
        settings_tab.save_settings()
        
        # Assert
        mock_validate.assert_called_once()
        mock_message_box.assert_called_once()
    
    def test_save_settings_success(self, qapp, qtbot, mock_config_manager):
        """Test successful settings save with all fields populated."""
        # Arrange
        settings_tab = SettingsTab(config_manager=mock_config_manager)
        qtbot.addWidget(settings_tab)
        
        # Fill in all credential fields
        settings_tab.linkedin_email.setText("linkedin@test.com")
        settings_tab.linkedin_password.setText("linkedin_pass")
        settings_tab.twitter_email.setText("twitter@test.com")
        settings_tab.twitter_password.setText("twitter_pass")
        settings_tab.facebook_email.setText("facebook@test.com")
        settings_tab.facebook_password.setText("facebook_pass")
        settings_tab.instagram_email.setText("instagram@test.com")
        settings_tab.instagram_password.setText("instagram_pass")
        settings_tab.reddit_username.setText("reddit_user")
        settings_tab.reddit_password.setText("reddit_pass")
        settings_tab.stocktwits_username.setText("stocktwits_user")
        settings_tab.stocktwits_password.setText("stocktwits_pass")
        
        # Configure other settings
        settings_tab.default_model.setCurrentText("gpt-4")
        settings_tab.max_tokens.setValue(2000)
        settings_tab.temperature.setValue(80)
        settings_tab.auto_post.setChecked(True)
        settings_tab.post_frequency.setValue(8)
        settings_tab.auto_engage.setChecked(True)
        
        # Act
        settings_tab.save_settings()
        
        # Assert
        # Check that credentials were saved
        assert mock_config_manager.credentials['LINKEDIN_EMAIL'] == "linkedin@test.com"
        assert mock_config_manager.credentials['TWITTER_PASSWORD'] == "twitter_pass"
        assert mock_config_manager.credentials['REDDIT_USERNAME'] == "reddit_user"
        
        # Check that settings were saved
        assert mock_config_manager.settings['default_model'] == "gpt-4"
        assert mock_config_manager.settings['max_tokens'] == 2000
        assert mock_config_manager.settings['temperature'] == 0.8  # Should be scaled to 0-1
        assert mock_config_manager.settings['auto_post'] is True
        assert mock_config_manager.settings['post_frequency'] == 8
        assert mock_config_manager.settings['auto_engage'] is True
        
        # Check status message
        assert "Settings saved successfully" in settings_tab.status_label.text()
        assert "color: #4CAF50" in settings_tab.status_label.styleSheet()  # Green success color
    
    def test_load_settings(self, qapp, qtbot, mock_config_manager):
        """Test loading settings from config manager."""
        # Arrange
        mock_config_manager.credentials = {
            'LINKEDIN_EMAIL': 'linkedin@example.com',
            'LINKEDIN_PASSWORD': 'linkedin123',
            'TWITTER_EMAIL': 'twitter@example.com',
            'TWITTER_PASSWORD': 'twitter123',
            'FACEBOOK_EMAIL': 'facebook@example.com',
            'FACEBOOK_PASSWORD': 'facebook123',
            'INSTAGRAM_EMAIL': 'instagram@example.com',
            'INSTAGRAM_PASSWORD': 'instagram123',
            'REDDIT_USERNAME': 'reddituser',
            'REDDIT_PASSWORD': 'reddit123',
            'STOCKTWITS_USERNAME': 'stocktwitsuser',
            'STOCKTWITS_PASSWORD': 'stocktwits123'
        }
        
        mock_config_manager.settings = {
            'default_model': 'gpt-3.5-turbo',
            'max_tokens': 3000,
            'temperature': 0.5,
            'auto_post': True,
            'post_frequency': 12,
            'auto_engage': True
        }
        
        settings_tab = SettingsTab(config_manager=mock_config_manager)
        qtbot.addWidget(settings_tab)
        
        # Act
        settings_tab.load_settings()
        
        # Assert - Check that fields were populated correctly
        assert settings_tab.linkedin_email.text() == 'linkedin@example.com'
        assert settings_tab.linkedin_password.text() == 'linkedin123'
        assert settings_tab.twitter_email.text() == 'twitter@example.com'
        assert settings_tab.twitter_password.text() == 'twitter123'
        
        assert settings_tab.default_model.currentText() == 'gpt-3.5-turbo'
        assert settings_tab.max_tokens.value() == 3000
        assert settings_tab.temperature.value() == 50  # Should be scaled to 0-100
        assert settings_tab.auto_post.isChecked() is True
        assert settings_tab.post_frequency.value() == 12
        assert settings_tab.auto_engage.isChecked() is True
    
    def test_update_managers(self, qapp, qtbot, mock_config_manager):
        """Test that update_managers properly updates the config manager."""
        # Arrange
        settings_tab = SettingsTab()
        qtbot.addWidget(settings_tab)
        
        # Mock the load_settings method
        original_load_settings = settings_tab.load_settings
        load_settings_called = [False]
        
        def mock_load_settings():
            load_settings_called[0] = True
            return original_load_settings()
        
        settings_tab.load_settings = mock_load_settings
        
        # Act
        settings_tab.update_managers(config_manager=mock_config_manager)
        
        # Assert
        assert settings_tab.config_manager == mock_config_manager
        assert load_settings_called[0] is True 