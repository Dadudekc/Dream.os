import os
import logging
import json

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QFormLayout, QTabWidget, QGroupBox, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSlot

from social.social_config_wrapper import get_social_config

class SocialDashboardTab(QWidget):
    """
    A PyQt5 tab for managing social platform credentials (Discord, Twitter, etc).
    Loads defaults from environment variables and allows editing & saving.
    """
    def __init__(
        self,
        dispatcher=None,
        config_manager=None,
        discord_manager=None,
        logger=None,
        parent=None
    ):
        super().__init__(parent)
        self.dispatcher = dispatcher
        self.config_manager = config_manager
        self.discord_manager = discord_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Get social config from wrapper to avoid circular imports
        self.social_config = get_social_config()

        # Credential storage
        self.credentials = {
            "discord": {
                "token": "",
                "channel_id": "",
                "webhook_url": ""
            },
            "twitter": {
                "api_key": "",
                "api_secret": "",
                "access_token": "",
                "access_secret": ""
            },
            "reddit": {
                "client_id": "",
                "client_secret": "",
                "username": "",
                "password": ""
            },
            "linkedin": {
                "email": "",
                "password": "",
                "api_key": ""
            },
            "facebook": {
                "email": "",
                "password": "",
                "app_id": "",
                "app_secret": ""
            },
            "instagram": {
                "email": "",
                "password": ""
            },
            "stocktwits": {
                "username": "",
                "password": ""
            }
        }

        self._load_defaults_from_env()
        self._load_defaults_from_config()
        self.init_ui()

    def _load_defaults_from_env(self):
        """Load environment variables for initial defaults."""
        # Discord credentials
        self.credentials["discord"]["token"] = os.getenv("DISCORD_TOKEN", "")
        self.credentials["discord"]["channel_id"] = os.getenv("DISCORD_CHANNEL_ID", "")
        self.credentials["discord"]["webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL", "")
        
        # Twitter credentials
        self.credentials["twitter"]["api_key"] = os.getenv("TWITTER_API_KEY", "")
        self.credentials["twitter"]["api_secret"] = os.getenv("TWITTER_API_SECRET", "")
        self.credentials["twitter"]["access_token"] = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.credentials["twitter"]["access_secret"] = os.getenv("TWITTER_ACCESS_SECRET", "")
        
        # Reddit credentials
        self.credentials["reddit"]["client_id"] = os.getenv("REDDIT_CLIENT_ID", "")
        self.credentials["reddit"]["client_secret"] = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.credentials["reddit"]["username"] = os.getenv("REDDIT_USERNAME", "")
        self.credentials["reddit"]["password"] = os.getenv("REDDIT_PASSWORD", "")
        
        # LinkedIn credentials
        self.credentials["linkedin"]["email"] = os.getenv("LINKEDIN_EMAIL", "")
        self.credentials["linkedin"]["password"] = os.getenv("LINKEDIN_PASSWORD", "")
        self.credentials["linkedin"]["api_key"] = os.getenv("LINKEDIN_API_KEY", "")
        
        # Facebook credentials
        self.credentials["facebook"]["email"] = os.getenv("FACEBOOK_EMAIL", "")
        self.credentials["facebook"]["password"] = os.getenv("FACEBOOK_PASSWORD", "")
        self.credentials["facebook"]["app_id"] = os.getenv("FACEBOOK_APP_ID", "")
        self.credentials["facebook"]["app_secret"] = os.getenv("FACEBOOK_APP_SECRET", "")
        
        # Instagram credentials
        self.credentials["instagram"]["email"] = os.getenv("INSTAGRAM_EMAIL", "")
        self.credentials["instagram"]["password"] = os.getenv("INSTAGRAM_PASSWORD", "")
        
        # StockTwits credentials
        self.credentials["stocktwits"]["username"] = os.getenv("STOCKTWITS_USERNAME", "")
        self.credentials["stocktwits"]["password"] = os.getenv("STOCKTWITS_PASSWORD", "")

    def _load_defaults_from_config(self):
        """Load defaults from config manager if available."""
        if not self.config_manager:
            return
            
        # Attempt to load from config if present
        for platform, fields in self.credentials.items():
            for field, _ in fields.items():
                config_key = f"{platform}.{field}"
                value = self.config_manager.get(config_key, None)
                if value:
                    self.credentials[platform][field] = value
                    self._log_output(f"Loaded {platform}.{field} from config")

    def init_ui(self):
        """Build the user interface."""
        main_layout = QVBoxLayout()
        
        # Title and description
        title_label = QLabel("Social Platform Dashboard")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        desc_label = QLabel("Manage credentials for social media integrations")
        desc_label.setStyleSheet("font-size: 12px; color: #666;")
        main_layout.addWidget(desc_label)
        
        # Create scrollable area for form groups
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Create form groups for each platform
        self.input_fields = {}
        
        # Discord group
        discord_group = self._create_platform_group(
            "Discord", 
            self.credentials["discord"],
            {
                "token": {"label": "Bot Token", "password": True},
                "channel_id": {"label": "Channel ID"},
                "webhook_url": {"label": "Webhook URL"}
            },
            test_button=True
        )
        scroll_layout.addWidget(discord_group)
        
        # Twitter group
        twitter_group = self._create_platform_group(
            "Twitter", 
            self.credentials["twitter"],
            {
                "api_key": {"label": "API Key"},
                "api_secret": {"label": "API Secret", "password": True},
                "access_token": {"label": "Access Token"},
                "access_secret": {"label": "Access Secret", "password": True}
            },
            test_button=True
        )
        scroll_layout.addWidget(twitter_group)
        
        # Reddit group
        reddit_group = self._create_platform_group(
            "Reddit", 
            self.credentials["reddit"],
            {
                "client_id": {"label": "Client ID"},
                "client_secret": {"label": "Client Secret", "password": True},
                "username": {"label": "Username"},
                "password": {"label": "Password", "password": True}
            }
        )
        scroll_layout.addWidget(reddit_group)
        
        # LinkedIn group
        linkedin_group = self._create_platform_group(
            "LinkedIn", 
            self.credentials["linkedin"],
            {
                "email": {"label": "Email"},
                "password": {"label": "Password", "password": True},
                "api_key": {"label": "API Key"}
            }
        )
        scroll_layout.addWidget(linkedin_group)
        
        # Facebook group
        facebook_group = self._create_platform_group(
            "Facebook", 
            self.credentials["facebook"],
            {
                "email": {"label": "Email"},
                "password": {"label": "Password", "password": True},
                "app_id": {"label": "App ID"},
                "app_secret": {"label": "App Secret", "password": True}
            }
        )
        scroll_layout.addWidget(facebook_group)
        
        # Instagram group
        instagram_group = self._create_platform_group(
            "Instagram", 
            self.credentials["instagram"],
            {
                "email": {"label": "Email"},
                "password": {"label": "Password", "password": True}
            }
        )
        scroll_layout.addWidget(instagram_group)
        
        # StockTwits group
        stocktwits_group = self._create_platform_group(
            "StockTwits", 
            self.credentials["stocktwits"],
            {
                "username": {"label": "Username"},
                "password": {"label": "Password", "password": True}
            }
        )
        scroll_layout.addWidget(stocktwits_group)
        
        # Add some stretch at the end
        scroll_layout.addStretch()
        
        # Set the scroll content and add to main layout
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Button row for saving all credentials
        button_layout = QHBoxLayout()
        save_all_btn = QPushButton("Save All Credentials")
        save_all_btn.clicked.connect(self.save_all_credentials)
        button_layout.addWidget(save_all_btn)
        
        # If we have a dispatcher, add a refresh button
        if self.dispatcher:
            refresh_btn = QPushButton("Refresh from Config")
            refresh_btn.clicked.connect(self.refresh_from_config)
            button_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(button_layout)
        
        # Set the main layout
        self.setLayout(main_layout)

    def _create_platform_group(self, platform_name, credential_dict, field_specs, test_button=False):
        """Create a group box for platform credentials with specified fields."""
        group = QGroupBox(f"{platform_name} Integration")
        form = QFormLayout()
        
        # Platform-specific field dictionary
        platform_key = platform_name.lower()
        self.input_fields[platform_key] = {}
        
        # Add each field to the form
        for field_key, specs in field_specs.items():
            input_field = QLineEdit(credential_dict.get(field_key, ""))
            
            # Set password mode if specified
            if specs.get("password", False):
                input_field.setEchoMode(QLineEdit.Password)
                
            # Store the input field for later access
            self.input_fields[platform_key][field_key] = input_field
            
            # Add row to form layout
            form.addRow(f"{specs['label']}:", input_field)
        
        # Add a test button if requested
        if test_button:
            test_btn = QPushButton(f"Test {platform_name} Connection")
            test_btn.clicked.connect(lambda: self.test_platform_connection(platform_key))
            form.addRow(test_btn)
        
        # Add a platform-specific save button
        save_btn = QPushButton(f"Save {platform_name} Credentials")
        save_btn.clicked.connect(lambda: self.save_platform_credentials(platform_key))
        form.addRow(save_btn)
        
        group.setLayout(form)
        return group

    def test_platform_connection(self, platform):
        """Test the connection for the specified platform."""
        self._log_output(f"Testing {platform} connection...")
        
        try:
            if platform == "discord" and self.discord_manager:
                # Update credentials first
                token = self.input_fields["discord"]["token"].text().strip()
                channel_id = self.input_fields["discord"]["channel_id"].text().strip()
                webhook_url = self.input_fields["discord"]["webhook_url"].text().strip()
                
                if not token and not webhook_url:
                    QMessageBox.warning(self, "Discord Credentials Missing", 
                                       "Please enter either a Discord token or webhook URL.")
                    return
                
                # Test Discord connection
                if self.discord_manager:
                    success = self.discord_manager.test_connection(token, channel_id, webhook_url)
                    if success:
                        QMessageBox.information(self, "Success", "Discord connection test successful!")
                    else:
                        QMessageBox.critical(self, "Failed", "Discord connection test failed. Check credentials.")
                else:
                    QMessageBox.warning(self, "Not Available", 
                                      "Discord Manager not available to test connection.")
            
            elif platform == "twitter":
                # Get Twitter credentials
                api_key = self.input_fields["twitter"]["api_key"].text().strip()
                api_secret = self.input_fields["twitter"]["api_secret"].text().strip()
                access_token = self.input_fields["twitter"]["access_token"].text().strip()
                access_secret = self.input_fields["twitter"]["access_secret"].text().strip()
                
                if not api_key or not api_secret:
                    QMessageBox.warning(self, "Twitter Credentials Missing",
                                       "Please enter Twitter API key and secret.")
                    return
                
                # Call platform-specific test logic if available
                # For now, just show a placeholder message
                QMessageBox.information(self, "Twitter", 
                                     "Twitter API validation not implemented yet.")
            
            else:
                QMessageBox.information(self, "Test Connection",
                                      f"Testing {platform} connection is not implemented yet.")
        
        except Exception as e:
            self._log_output(f"Error testing {platform} connection: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error testing connection: {str(e)}")

    def save_platform_credentials(self, platform):
        """Save credentials for a specific platform."""
        self._log_output(f"Saving {platform} credentials...")
        
        # Get all field values for this platform
        for field, input_widget in self.input_fields[platform].items():
            new_value = input_widget.text().strip()
            self.credentials[platform][field] = new_value
            
            # Save to config if available
            if self.config_manager:
                config_key = f"{platform}.{field}"
                self.config_manager.set(config_key, new_value)
        
        # Save config or write to file
        self._save_credentials_to_storage()
        
        QMessageBox.information(self, "Saved", f"{platform.capitalize()} credentials updated successfully.")

    def save_all_credentials(self):
        """Save all credentials for all platforms."""
        self._log_output("Saving all credentials...")
        
        # Read all input values into credentials dict
        for platform, fields in self.input_fields.items():
            for field, input_widget in fields.items():
                new_value = input_widget.text().strip()
                self.credentials[platform][field] = new_value
                
                # Save to config if available
                if self.config_manager:
                    config_key = f"{platform}.{field}"
                    self.config_manager.set(config_key, new_value)
        
        # Save config or write to file
        self._save_credentials_to_storage()
        
        QMessageBox.information(self, "Saved", "All social platform credentials updated successfully.")

    def _save_credentials_to_storage(self):
        """Save credentials to config manager or fallback to file."""
        if self.config_manager:
            # Persist the changes to config
            self.config_manager.save()
            self._log_output("Credentials saved to config successfully.")
        else:
            # Fallback to JSON file
            output_dir = "config"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, "social_credentials.json")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.credentials, f, indent=2)
                
            self._log_output(f"Credentials saved to {filepath}.")
            
        # Update social_config if needed
        if hasattr(self.social_config, 'reload'):
            self.social_config.reload()
            self._log_output("Refreshed social_config with new credentials.")

    @pyqtSlot()
    def refresh_from_config(self):
        """Refresh credential fields from config."""
        self._log_output("Refreshing credentials from config...")
        self._load_defaults_from_env()
        self._load_defaults_from_config()
        
        # Update all input fields with refreshed values
        for platform, fields in self.input_fields.items():
            for field, input_widget in fields.items():
                if platform in self.credentials and field in self.credentials[platform]:
                    input_widget.setText(self.credentials[platform][field])
        
        QMessageBox.information(self, "Refreshed", "Social credentials refreshed from config.")

    def _log_output(self, message: str):
        """Log to the logger or dispatcher if available."""
        if self.logger:
            self.logger.info(f"[SOCIAL DASHBOARD] {message}")
            
        if self.dispatcher and hasattr(self.dispatcher, 'emit_log_output'):
            self.dispatcher.emit_log_output(f"[SOCIAL DASHBOARD] {message}")
