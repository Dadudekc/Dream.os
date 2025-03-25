import discord
from discord.ext import commands
import asyncio
import logging
import threading
import json
import os
from typing import Union, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QComboBox
)
from core.EventMessageBuilder import EventMessageBuilder  # Adjust path if necessary
from utils.json_paths import JsonPaths

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DiscordManager:
    CONFIG_FILE = "discord_manager_config.json"

    def __init__(self, bot_token: str = None, channel_id: Union[int, str] = None) -> None:
        """
        Initialize Discord Manager.
        :param bot_token: Discord Bot Token (optional, loaded from config if not provided)
        :param channel_id: Default Channel ID (optional, loaded from config if not provided)
        """
        # Log callback for external logging integration.
        self.log_callback = None

        # Initialize configuration.
        self.config: Dict[str, Any] = {
            "bot_token": bot_token or "",
            "default_channel_id": int(channel_id) if channel_id else 0,
            "prompt_channel_map": {}
        }
        self.load_config()
        self.bot_token: str = self.config.get("bot_token", "")
        self.default_channel_id: int = self.config.get("default_channel_id", 0)
        self.prompt_channel_map: Dict[str, int] = self.config.get("prompt_channel_map", {})

        self.is_running: bool = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.status_data: Dict[str, Any] = {
            "cycle_active": False,
            "current_prompt": None,
            "completed_prompts": [],
            "progress_message": "Idle"
        }

        # Set up Discord bot intents.
        intents = discord.Intents.default()
        intents.message_content = True

        # Initialize bot.
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self._register_events()
        self._register_commands()

        self.bot_loop_thread: Union[threading.Thread, None] = None

        # Initialize EventMessageBuilder for templated notifications.
        self.event_message_builder = EventMessageBuilder()

    # ---------------------------
    # Logging Methods
    # ---------------------------
    def set_log_callback(self, callback) -> None:
        """Set a callback function for log messages."""
        self.log_callback = callback

    def _log(self, message: str, level=logging.INFO) -> None:
        """Log a message and call the external log callback if set."""
        logger.log(level, message)
        if self.log_callback:
            self.log_callback(message)

    # ------------------------------------------------------
    # CONFIG MANAGEMENT
    # ------------------------------------------------------
    def load_config(self) -> None:
        """Load configuration from file."""
        config_path = JsonPaths.get_path("discord_config")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
                logger.info(f"Loaded Discord configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading Discord configuration: {e}")

    def save_config(self) -> None:
        """Save configuration to file."""
        config_path = JsonPaths.get_path("discord_config")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Saved Discord configuration to {config_path}")
        except Exception as e:
            logger.error(f"Error saving Discord configuration: {e}")

    def update_credentials(self, bot_token: str, default_channel_id: int) -> None:
        """Update bot token and default channel ID in the configuration."""
        self.config["bot_token"] = bot_token
        self.config["default_channel_id"] = default_channel_id
        self.bot_token = bot_token
        self.default_channel_id = default_channel_id
        self.save_config()
        self._log("🔑 Discord bot token and default channel updated.")

    def map_prompt_to_channel(self, prompt_type: str, channel_id: Union[int, str]) -> None:
        """Map a specific prompt type to a channel ID."""
        self.prompt_channel_map[prompt_type] = int(channel_id)
        self.config["prompt_channel_map"] = self.prompt_channel_map
        self.save_config()
        self._log(f"🔗 Mapped prompt '{prompt_type}' to channel ID {channel_id}")

    def unmap_prompt_channel(self, prompt_type: str) -> None:
        """Remove mapping for a given prompt type."""
        if prompt_type in self.prompt_channel_map:
            del self.prompt_channel_map[prompt_type]
            self.config["prompt_channel_map"] = self.prompt_channel_map
            self.save_config()
            self._log(f"❌ Unmapped channel for prompt '{prompt_type}'")

    def get_channel_for_prompt(self, prompt_type: str) -> int:
        """Retrieve channel ID for the given prompt type, defaulting if necessary."""
        return self.prompt_channel_map.get(prompt_type, self.default_channel_id)

    # ------------------------------------------------------
    # BOT EVENTS & COMMANDS
    # ------------------------------------------------------
    def _register_events(self) -> None:
        @self.bot.event
        async def on_ready() -> None:
            self._log(f"✅ Discord Bot is ready! Logged in as {self.bot.user}")

        @self.bot.event
        async def on_command_error(ctx, error) -> None:
            self._log(f"❌ Command error: {error}", level=logging.ERROR)
            await ctx.send(f"An error occurred: {error}")

    def _register_commands(self) -> None:
        @self.bot.command(name="ping")
        async def ping_command(ctx) -> None:
            await ctx.send("🏓 Pong!")

        @self.bot.command(name="status")
        async def status_command(ctx) -> None:
            status_msg = self._build_status_message()
            await ctx.send(status_msg)

    def _build_status_message(self) -> str:
        """Build a status message from current status data."""
        if not self.status_data["cycle_active"]:
            return "🟢 No prompt cycle running."
        current = self.status_data.get("current_prompt", "N/A")
        done = ", ".join(self.status_data.get("completed_prompts", [])) or "None"
        progress = self.status_data.get("progress_message", "Idle")
        return (
            f"🚀 **Prompt Cycle Status**\n"
            f"- **Active**: ✅\n"
            f"- **Current Prompt**: `{current}`\n"
            f"- **Completed**: `{done}`\n"
            f"- **Progress**: `{progress}`"
        )

    # ------------------------------------------------------
    # BACKGROUND DISPATCHER
    # ------------------------------------------------------
    async def _message_dispatcher(self) -> None:
        await self.bot.wait_until_ready()
        self._log("🚀 Message dispatcher started.")
        while self.is_running:
            try:
                msg_data = await self.message_queue.get()
                prompt_type = msg_data.get("prompt_type")
                msg = msg_data.get("message")
                is_file = msg_data.get("is_file", False)
                file_path = msg_data.get("file_path", "")
                description = msg_data.get("description", "")

                channel_id = self.get_channel_for_prompt(prompt_type)
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self._log(f"⚠️ Channel {channel_id} not found for prompt '{prompt_type}'.", level=logging.WARNING)
                    continue

                if is_file and file_path:
                    if os.path.exists(file_path):
                        await channel.send(content=description, file=discord.File(file_path))
                        self._log(f"📤 Sent file {file_path} to channel {channel_id}")
                    else:
                        self._log(f"❌ File not found: {file_path}", level=logging.ERROR)
                else:
                    await channel.send(msg)
                    self._log(f"📤 Sent message to channel {channel_id}: {msg}")
            except Exception as e:
                self._log(f"❌ Dispatcher error: {e}", level=logging.ERROR)

    # ------------------------------------------------------
    # BOT CONTROL
    # ------------------------------------------------------
    def run_bot(self) -> None:
        """Start the Discord bot in a separate thread."""
        if self.is_running:
            self._log("⚠️ Bot already running.", level=logging.WARNING)
            return
        # Reload configuration to ensure latest settings are used.
        self.load_config()
        self.bot_token = self.config.get("bot_token", "")
        self.default_channel_id = self.config.get("default_channel_id", 0)
        if not self.bot_token or not self.default_channel_id:
            error_message = "❌ Bot token and default channel ID must be set in the config file."
            self._log(error_message, level=logging.ERROR)
            QMessageBox.warning(None, "Launch Error", error_message)
            return

        self._log("🚀 Starting Discord bot...")
        self.is_running = True
        self.bot_loop_thread = threading.Thread(target=self._run_bot_loop, daemon=True)
        self.bot_loop_thread.start()

    def _run_bot_loop(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(self._message_dispatcher())
            loop.run_until_complete(self.bot.start(self.bot_token))
        except Exception as e:
            self._log(f"❌ Bot loop error: {e}", level=logging.ERROR)
        finally:
            self._log("🛑 Bot loop closed.")
            self.is_running = False

    def stop_bot(self) -> None:
        """Stop the Discord bot."""
        self._log("🛑 Stopping Discord bot...")
        if not self.is_running:
            self._log("⚠️ Bot not running.", level=logging.WARNING)
            return
        self.is_running = False
        if self.bot.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                self._log(f"❌ Failed to stop bot: {e}", level=logging.ERROR)
        if self.bot_loop_thread:
            self.bot_loop_thread.join(timeout=5)
            self._log("✅ Bot loop thread stopped.")

    # ------------------------------------------------------
    # EXTERNAL SENDER METHODS
    # ------------------------------------------------------
    def send_message(self, prompt_type: str, message: str) -> None:
        """Queue a text message to be sent for a specific prompt."""
        if not self.is_running:
            self._log("⚠️ Bot not running. Cannot send message.", level=logging.WARNING)
            return
        msg_data = {"prompt_type": prompt_type, "message": message, "is_file": False}
        try:
            asyncio.run_coroutine_threadsafe(self.message_queue.put(msg_data), self.bot.loop)
            self._log(f"✅ Queued message for prompt '{prompt_type}': {message}")
        except Exception as e:
            self._log(f"❌ Failed to queue message: {e}", level=logging.ERROR)

    def send_file(self, prompt_type: str, file_path: str, description: str = "📜 New file uploaded") -> None:
        """Queue a file to be sent for a specific prompt."""
        if not self.is_running:
            self._log("⚠️ Bot not running. Cannot send file.", level=logging.WARNING)
            return
        msg_data = {"prompt_type": prompt_type, "is_file": True, "file_path": file_path, "description": description}
        try:
            asyncio.run_coroutine_threadsafe(self.message_queue.put(msg_data), self.bot.loop)
            self._log(f"✅ Queued file for prompt '{prompt_type}': {file_path}")
        except Exception as e:
            self._log(f"❌ Failed to queue file: {e}", level=logging.ERROR)

    def send_dreamscape_episode(self, prompt_type: str, episode_file_path: str, post_full_text: bool = False) -> None:
        """
        Send a Dreamscape episode either as text or file depending on its length.
        :param prompt_type: The prompt type to send the episode to.
        :param episode_file_path: Path to the episode text file.
        :param post_full_text: Whether to post full text if within character limits.
        """
        if not os.path.exists(episode_file_path):
            self._log(f"❌ Episode file does not exist: {episode_file_path}", level=logging.ERROR)
            return
        try:
            with open(episode_file_path, "r", encoding="utf-8") as f:
                episode_text = f.read()
            episode_title = os.path.basename(episode_file_path).replace("_", " ").replace(".txt", "")
            if post_full_text and len(episode_text) <= 1800:
                message = (
                    f"📜 **New Dreamscape Episode Released!**\n\n"
                    f"**{episode_title}**\n\n{episode_text}"
                )
                self.send_message(prompt_type, message)
                self._log(f"✅ Sent Dreamscape episode text for prompt '{prompt_type}'")
            else:
                description = f"📜 **New Dreamscape Episode Released!**\n\n**{episode_title}**"
                self.send_file(prompt_type, episode_file_path, description)
                self._log(f"✅ Sent Dreamscape episode file for prompt '{prompt_type}'")
        except Exception as e:
            self._log(f"❌ Failed to send Dreamscape episode: {e}", level=logging.ERROR)

    def send_prompt_response(self, prompt_type: str, response_text: str = None, response_file: str = None) -> None:
        """
        Post a saved response from a prompt to Discord.
        Either response_text or response_file must be provided.
        If the text is short (<= 2000 characters), it is sent as a message;
        otherwise or if a file is provided, it is sent as a file.
        """
        if not self.is_running:
            self._log("⚠️ Bot not running. Cannot send prompt response.", level=logging.WARNING)
            return

        if response_file and os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) <= 2000:
                self.send_message(prompt_type, content)
            else:
                self.send_file(prompt_type, response_file, description="📜 Prompt response")
        elif response_text:
            if len(response_text) <= 2000:
                self.send_message(prompt_type, response_text)
            else:
                temp_file = "temp_prompt_response.txt"
                try:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(response_text)
                    self.send_file(prompt_type, temp_file, description="📜 Prompt response")
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        else:
            self._log("⚠️ No response provided to send.", level=logging.WARNING)

    def send_event_notification(self, event_type: str, event_data: dict) -> None:
        """
        Build and send a Discord notification for a specific event type using templated messages.
        :param event_type: Type of event (e.g., "quest_complete", "protocol_unlock", "tier_up").
        :param event_data: Dictionary with event-specific data.
        """
        message = self.event_message_builder.build_message(event_type, event_data)
        self.send_message(event_type, message)

    # ------------------------------------------------------
    # STATUS UPDATE
    # ------------------------------------------------------
    def update_status(self, key: str, value: Any) -> None:
        """Update internal status information."""
        if key not in self.status_data:
            self._log(f"⚠️ Unknown status key: {key}", level=logging.WARNING)
        self.status_data[key] = value
        logger.debug(f" Updated status_data[{key}] = {value}")


class DiscordSettingsDialog(QDialog):
    def __init__(self, parent=None, discord_manager: DiscordManager = None) -> None:
        """
        Initialize the Discord Settings dialog.
        :param discord_manager: Instance of DiscordManager (required).
        """
        super().__init__(parent)
        self.setWindowTitle("Discord Settings")
        if discord_manager is None:
            raise ValueError("DiscordManager instance is required!")
        self.discord_manager = discord_manager
        self.initUI()

    def initUI(self) -> None:
        layout = QVBoxLayout()

        # Bot Token & Default Channel ID
        layout.addWidget(QLabel("Bot Token:"))
        self.bot_token_input = QLineEdit(self.discord_manager.bot_token)
        layout.addWidget(self.bot_token_input)

        layout.addWidget(QLabel("Default Channel ID:"))
        self.channel_id_input = QLineEdit(str(self.discord_manager.default_channel_id))
        layout.addWidget(self.channel_id_input)

        update_credentials_btn = QPushButton("Update Credentials")
        update_credentials_btn.clicked.connect(self.update_credentials)
        layout.addWidget(update_credentials_btn)

        # Prompt → Channel Mapping
        layout.addWidget(QLabel("Prompt → Channel Mapping:"))
        self.prompt_channel_list = QListWidget()
        self.refresh_prompt_channel_list()
        layout.addWidget(self.prompt_channel_list)

        # Load available prompt types from prompts.json.
        layout.addWidget(QLabel("Select Prompt Type to Map:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.addItems(self.load_prompt_types())
        layout.addWidget(self.prompt_type_combo)

        # Input for channel ID mapping.
        self.prompt_channel_input = QLineEdit()
        self.prompt_channel_input.setPlaceholderText("Channel ID")
        layout.addWidget(self.prompt_channel_input)

        map_prompt_btn = QPushButton("Map Prompt to Channel")
        map_prompt_btn.clicked.connect(self.map_prompt_to_channel)
        layout.addWidget(map_prompt_btn)

        unmap_prompt_btn = QPushButton("Unmap Selected Prompt")
        unmap_prompt_btn.clicked.connect(self.unmap_selected_prompt)
        layout.addWidget(unmap_prompt_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_prompt_types(self) -> list:
        """Load available prompt types from prompts.json."""
        prompts_file = "prompts.json"
        if os.path.exists(prompts_file):
            try:
                with open(prompts_file, "r", encoding="utf-8") as f:
                    prompts_data = json.load(f)
                return list(prompts_data.keys())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load prompts: {e}")
        return []

    def update_credentials(self) -> None:
        """Update bot token and default channel ID via the DiscordManager."""
        token = self.bot_token_input.text().strip()
        channel_id_str = self.channel_id_input.text().strip()
        if not token or not channel_id_str.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Bot token and channel ID are required.")
            return
        channel_id = int(channel_id_str)
        self.discord_manager.update_credentials(token, channel_id)
        QMessageBox.information(self, "Success", "Bot token and default channel ID updated.")

    def map_prompt_to_channel(self) -> None:
        """Map a selected prompt type to a specified channel."""
        prompt_type = self.prompt_type_combo.currentText()
        channel_id_str = self.prompt_channel_input.text().strip()
        if not prompt_type or not channel_id_str.isdigit():
            QMessageBox.warning(self, "Invalid Input", "A prompt type and numeric channel ID are required.")
            return
        channel_id = int(channel_id_str)
        self.discord_manager.map_prompt_to_channel(prompt_type, channel_id)
        self.refresh_prompt_channel_list()
        self.prompt_channel_input.clear()
        QMessageBox.information(self, "Success", f"Mapped '{prompt_type}' to channel {channel_id}.")

    def unmap_selected_prompt(self) -> None:
        """Unmap the selected prompt(s) from their channels."""
        selected_items = self.prompt_channel_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a prompt to unmap.")
            return
        for item in selected_items:
            prompt_type = item.text().split(" -> ")[0]
            self.discord_manager.unmap_prompt_channel(prompt_type)
        self.refresh_prompt_channel_list()
        QMessageBox.information(self, "Success", "Selected prompts unmapped.")

    def refresh_prompt_channel_list(self) -> None:
        """Refresh the list of prompt-channel mappings."""
        self.prompt_channel_list.clear()
        mappings = self.discord_manager.prompt_channel_map
        if not mappings:
            self.prompt_channel_list.addItem(QListWidgetItem("No mappings found."))
            return
        for prompt_type, channel_id in mappings.items():
            item_text = f"{prompt_type} -> {channel_id}"
            self.prompt_channel_list.addItem(QListWidgetItem(item_text))


# If needed, you can instantiate and run the manager and settings dialog here.
# For example:
# if __name__ == "__main__":
#     from PyQt5.QtWidgets import QApplication
#     import sys
#     app = QApplication(sys.argv)
#     manager = DiscordManager()
#     settings_dialog = DiscordSettingsDialog(discord_manager=manager)
#     settings_dialog.show()
#     sys.exit(app.exec_())
