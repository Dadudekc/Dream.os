from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QListWidget, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt


class DiscordSettingsDialog(QDialog):
    """
    Dialog window for configuring Discord bot settings and prompt channel mappings.
    """
    def __init__(self, parent=None, discord_manager=None):
        super().__init__(parent)
        self.discord_manager = discord_manager

        self.setWindowTitle("Discord Bot Settings")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # --- Discord Bot Credentials Form ---
        form_layout = QFormLayout()
        self.bot_token_field = QLineEdit()
        self.bot_token_field.setPlaceholderText("Enter Discord Bot Token...")

        self.guild_id_field = QLineEdit()
        self.guild_id_field.setPlaceholderText("Enter Discord Server (Guild) ID...")

        self.status_field = QLineEdit()
        self.status_field.setPlaceholderText("Enter Bot Status Message...")

        form_layout.addRow(QLabel("Bot Token:"), self.bot_token_field)
        form_layout.addRow(QLabel("Guild ID:"), self.guild_id_field)
        form_layout.addRow(QLabel("Bot Status:"), self.status_field)

        layout.addLayout(form_layout)

        # --- Save Credentials Button ---
        save_credentials_btn = QPushButton("Save Credentials")
        save_credentials_btn.clicked.connect(self.save_credentials)
        layout.addWidget(save_credentials_btn)

        # --- Prompt to Channel Mapping ---
        mapping_layout = QVBoxLayout()
        mapping_layout.addWidget(QLabel("Prompt Type to Discord Channel Mapping:"))

        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.addItems(self.discord_manager.load_prompt_types())

        self.channel_id_field = QLineEdit()
        self.channel_id_field.setPlaceholderText("Enter Discord Channel ID...")

        map_button = QPushButton("Map Prompt to Channel")
        map_button.clicked.connect(self.map_prompt_to_channel)

        mapping_layout.addWidget(QLabel("Prompt Type:"))
        mapping_layout.addWidget(self.prompt_type_combo)
        mapping_layout.addWidget(QLabel("Channel ID:"))
        mapping_layout.addWidget(self.channel_id_field)
        mapping_layout.addWidget(map_button)

        layout.addLayout(mapping_layout)

        # --- Mappings List & Unmap Button ---
        self.mapping_list = QListWidget()
        self.refresh_prompt_channel_list()

        unmap_button = QPushButton("Unmap Selected Prompt")
        unmap_button.clicked.connect(self.unmap_selected_prompt)

        layout.addWidget(QLabel("Current Prompt Mappings:"))
        layout.addWidget(self.mapping_list)
        layout.addWidget(unmap_button)

        # --- Close Button ---
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def save_credentials(self):
        """
        Save Discord bot token, guild ID, and bot status.
        """
        token = self.bot_token_field.text().strip()
        guild_id = self.guild_id_field.text().strip()
        status = self.status_field.text().strip()

        if not token or not guild_id:
            QMessageBox.warning(self, "Input Error", "Bot token and Guild ID are required.")
            return

        self.discord_manager.update_credentials(token, guild_id, status)
        QMessageBox.information(self, "Success", "Credentials saved successfully.")

    def map_prompt_to_channel(self):
        """
        Map a selected prompt type to a Discord channel ID.
        """
        prompt_type = self.prompt_type_combo.currentText()
        channel_id = self.channel_id_field.text().strip()

        if not channel_id:
            QMessageBox.warning(self, "Input Error", "Channel ID cannot be empty.")
            return

        self.discord_manager.map_prompt_to_channel(prompt_type, channel_id)
        QMessageBox.information(self, "Success", f"Mapped {prompt_type} to channel {channel_id}.")

        self.refresh_prompt_channel_list()
        self.channel_id_field.clear()

    def unmap_selected_prompt(self):
        """
        Unmap the selected prompt type from the mappings list.
        """
        selected_items = self.mapping_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a prompt mapping to unmap.")
            return

        for item in selected_items:
            text = item.text()
            prompt_type = text.split(":")[0].strip()
            self.discord_manager.unmap_prompt_channel(prompt_type)

        self.refresh_prompt_channel_list()

    def refresh_prompt_channel_list(self):
        """
        Reload the mappings and refresh the list view.
        """
        self.mapping_list.clear()
        mappings = self.discord_manager.get_channel_for_prompt()
        if not mappings:
            return

        for prompt_type, channel_id in mappings.items():
            self.mapping_list.addItem(f"{prompt_type}: {channel_id}")

