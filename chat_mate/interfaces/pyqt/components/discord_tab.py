from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLineEdit, QLabel, QTextEdit
)

class DiscordTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self._create_discord_group())
        self.setLayout(layout)

    def _create_discord_group(self):
        group = QGroupBox("Discord Bot Settings")
        layout = QVBoxLayout()

        # Token Input
        self.discord_token_input = QLineEdit()
        self.discord_token_input.setPlaceholderText("Enter Discord Bot Token")
        layout.addWidget(QLabel("Discord Bot Token:"))
        layout.addWidget(self.discord_token_input)

        # Channel ID Input
        self.discord_channel_input = QLineEdit()
        self.discord_channel_input.setPlaceholderText("Enter Default Channel ID")
        layout.addWidget(QLabel("Default Channel ID:"))
        layout.addWidget(self.discord_channel_input)

        # Control Buttons
        self.launch_bot_btn = QPushButton("Launch Discord Bot")
        self.stop_bot_btn = QPushButton("Stop Discord Bot")
        layout.addWidget(self.launch_bot_btn)
        layout.addWidget(self.stop_bot_btn)

        # Status Label
        self.discord_status_label = QLabel("Status: 🔴 Disconnected")
        layout.addWidget(self.discord_status_label)

        # Log Viewer
        self.discord_log_viewer = QTextEdit()
        self.discord_log_viewer.setReadOnly(True)
        layout.addWidget(QLabel("Discord Bot Logs:"))
        layout.addWidget(self.discord_log_viewer)

        group.setLayout(layout)
        return group

    def update_status(self, connected: bool):
        """Update the Discord connection status display"""
        self.discord_status_label.setText(
            "Status: 🟢 Connected" if connected else "Status: 🔴 Disconnected"
        )

    def append_log(self, message: str):
        """Add a message to the Discord log viewer"""
        self.discord_log_viewer.append(message)

    def get_bot_config(self):
        """Get the current Discord bot configuration"""
        return {
            'token': self.discord_token_input.text().strip(),
            'channel_id': self.discord_channel_input.text().strip()
        } 