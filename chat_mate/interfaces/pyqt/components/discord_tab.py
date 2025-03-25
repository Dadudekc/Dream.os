from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLineEdit, QLabel, QTextEdit
)
import asyncio
from qasync import asyncSlot

class DiscordTab(QWidget):
    def __init__(self, parent=None, dispatcher=None, config=None, logger=None, discord_manager=None, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.dispatcher = dispatcher
        self.config = config
        self.logger = logger
        self.discord_manager = discord_manager
        
        # Track running tasks
        self.running_tasks = {}
        
        self.initUI()
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect dispatcher signals if available
        if self.dispatcher:
            self.dispatcher.discord_event.connect(self.handle_discord_event)
            self.dispatcher.dreamscape_generated.connect(self.handle_dreamscape_generated)
            
        # Connect UI button signals
        self.launch_bot_btn.clicked.connect(self.launch_discord_bot)
        self.stop_bot_btn.clicked.connect(self.stop_discord_bot)

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
        
        # Log status change via dispatcher
        if self.dispatcher:
            status_msg = f"Discord bot {'connected' if connected else 'disconnected'}"
            self.dispatcher.emit_discord_log(status_msg)

    def append_log(self, message: str):
        """Add a message to the Discord log viewer"""
        self.discord_log_viewer.append(message)
        
        # Also log through dispatcher if available
        if self.dispatcher:
            self.dispatcher.emit_discord_log(message)

    def get_bot_config(self):
        """Get the current Discord bot configuration"""
        return {
            'token': self.discord_token_input.text().strip(),
            'channel_id': self.discord_channel_input.text().strip()
        }
        
    @asyncSlot()
    async def launch_discord_bot(self):
        """Launch the Discord bot asynchronously."""
        # Get configuration
        config = self.get_bot_config()
        
        # Validate configuration
        if not config['token']:
            self.append_log("❌ Error: Discord token is required")
            return
            
        if not config['channel_id']:
            self.append_log("❌ Error: Channel ID is required")
            return
            
        # Generate unique task ID
        task_id = "discord_launch"
        
        # Signal task start
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
            
        # Create and track task
        task = asyncio.create_task(self._launch_discord_async(task_id, config))
        self.running_tasks[task_id] = task
        
        # Add done callback
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))
            
    async def _launch_discord_async(self, task_id, config):
        """Async implementation of Discord bot launch."""
        try:
            # Update UI
            self.append_log("🚀 Launching Discord bot...")
            
            # Report progress
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 25, "Initializing Discord client")
                
            # Simulated async work
            await asyncio.sleep(0.5)
            
            # In a real implementation, this would be where you'd initialize the Discord bot
            # Using asyncio.to_thread for blocking operations
            # result = await asyncio.to_thread(
            #     self.discord_manager.connect,
            #     token=config['token'],
            #     channel_id=config['channel_id']
            # )
            
            # For now, simulate a successful connection
            await asyncio.sleep(1)
            
            # Report progress
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 75, "Connecting to Discord")
                
            # Update status UI
            self.update_status(True)
            self.append_log("✅ Discord bot connected successfully")
            
            # Report completion
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Connected")
                
            # Return result
            return {"status": "connected", "config": config}
            
        except Exception as e:
            error_msg = f"Error launching Discord bot: {str(e)}"
            self.append_log(f"❌ {error_msg}")
            self.update_status(False)
            
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, error_msg)
                
            raise e
    
    @asyncSlot()
    async def stop_discord_bot(self):
        """Stop the Discord bot asynchronously."""
        # Generate unique task ID
        task_id = "discord_stop"
        
        # Signal task start
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
            
        # Create and track task
        task = asyncio.create_task(self._stop_discord_async(task_id))
        self.running_tasks[task_id] = task
        
        # Add done callback
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))
    
    async def _stop_discord_async(self, task_id):
        """Async implementation of Discord bot shutdown."""
        try:
            # Update UI
            self.append_log("🛑 Stopping Discord bot...")
            
            # Report progress
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 50, "Disconnecting from Discord")
                
            # Simulated async work
            await asyncio.sleep(1)
            
            # In a real implementation, this would be where you'd disconnect the Discord bot
            # Using asyncio.to_thread for blocking operations
            # result = await asyncio.to_thread(
            #     self.discord_manager.disconnect
            # )
            
            # Update status UI
            self.update_status(False)
            self.append_log("✅ Discord bot disconnected successfully")
            
            # Report completion
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Disconnected")
                
            # Return result
            return {"status": "disconnected"}
            
        except Exception as e:
            error_msg = f"Error stopping Discord bot: {str(e)}"
            self.append_log(f"❌ {error_msg}")
            
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, error_msg)
                
            raise e
            
    def _on_task_done(self, task_id, task):
        """Handle task completion or failure."""
        # Remove task from tracking
        self.running_tasks.pop(task_id, None)
        
        try:
            # Get the result (will raise exception if the task failed)
            result = task.result()
            
            # Emit completion signal through dispatcher
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                
        except asyncio.CancelledError:
            self.append_log(f"❌ Task {task_id} was cancelled.")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, "Task was cancelled.")
                
        except Exception as e:
            # Task failure will already have been handled in the task itself
            pass
            
    def handle_discord_event(self, event_type, event_data):
        """Handle discord_event signal from the dispatcher."""
        self.append_log(f"📝 Discord event: {event_type}")
        
    def handle_dreamscape_generated(self, data):
        """Handle dreamscape_generated signal from the dispatcher."""
        self.append_log(f"🔮 Dreamscape content generated")
        
        # In a real application, you might want to prepare this content for sharing on Discord
        episode_count = data.get('episodes_created', 0)
        if episode_count > 0:
            self.append_log(f"✨ {episode_count} new episodes available for sharing to Discord")
            
    def handle_prompt_executed(self, prompt_name, response_data):
        """Handle prompt_executed signal from the dispatcher."""
        self.append_log(f"🔄 Prompt '{prompt_name}' executed")
        
        # In a real application, you might want to prepare this content for sharing on Discord
        if response_data and 'response' in response_data:
            preview = response_data['response'][:30] + "..." if len(response_data['response']) > 30 else response_data['response']
            self.append_log(f"📋 Response preview: {preview}")
            self.append_log(f"Available for sharing to Discord") 