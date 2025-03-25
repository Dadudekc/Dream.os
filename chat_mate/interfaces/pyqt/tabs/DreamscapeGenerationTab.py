import os
import json
import re
import logging
import asyncio
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog, QListWidget, QSplitter, QCheckBox, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QComboBox, QFormLayout, QTabWidget, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer
from qasync import asyncSlot

# Core Services
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator


class DreamscapeGenerationTab(QWidget):
    """
    Dreamscape Generation Tab integrates:
    1. CycleExecutionService for Single/Multi Chat Cycles.
    2. UnifiedDreamscapeGenerator for advanced Dreamscape episode creation.
    
    This tab provides a comprehensive interface for managing and generating
    Dreamscape episodes, including context management, scheduling, and
    Discord integration.
    """

    def __init__(self, dispatcher=None, prompt_manager=None, chat_manager=None, response_handler=None, 
                 memory_manager=None, discord_manager=None, ui_logic=None, 
                 config_manager=None, logger=None):
        """
        Initialize the DreamscapeGenerationTab with dependency injection support.
        
        Args:
            dispatcher: Event dispatcher for system-wide communication
            prompt_manager: Service for managing prompts
            chat_manager: Service for managing chat interactions
            response_handler: Service for processing responses
            memory_manager: Service for managing memory/context
            discord_manager: Service for Discord integration
            ui_logic: Service for UI-specific logic and service delegation
            config_manager: Service for managing configuration
            logger: Logger instance for debugging and monitoring
        """
        super().__init__()

        # Service References
        self.dispatcher = dispatcher
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)

        # Inject Services
        self._inject_services(prompt_manager, chat_manager, response_handler, memory_manager, discord_manager)

        # Initialize Core Engines
        self._initialize_services()

        # Initialize UI
        self.init_ui()
        
        # Task Management
        self.running_tasks = {}
        
        # Setup Timers
        self._setup_timers()
        
        # Initial Data Load
        self._load_initial_data()

    def _inject_services(self, prompt_manager, chat_manager, response_handler, memory_manager, discord_manager):
        """
        Inject services directly or fetch from ui_logic controller.
        
        This method handles service dependency injection with fallback support,
        prioritizing services from the UI logic controller if available.
        
        Args:
            prompt_manager: Service for managing prompts
            chat_manager: Service for managing chat interactions
            response_handler: Service for processing responses
            memory_manager: Service for managing memory/context
            discord_manager: Service for Discord integration
        """
        try:
            if self.ui_logic and hasattr(self.ui_logic, 'get_service'):
                self.prompt_manager = self.ui_logic.get_service('prompt_manager') or prompt_manager
                self.chat_manager = self.ui_logic.get_service('chat_manager') or chat_manager
                self.response_handler = self.ui_logic.get_service('response_handler') or response_handler
                self.memory_manager = self.ui_logic.get_service('memory_manager') or memory_manager
                self.discord_manager = self.ui_logic.get_service('discord_service') or discord_manager
            else:
                self.prompt_manager = prompt_manager
                self.chat_manager = chat_manager
                self.response_handler = response_handler
                self.memory_manager = memory_manager
                self.discord_manager = discord_manager
                
            if not all([self.chat_manager, self.response_handler]):
                self.log_output("⚠️ Warning: Some core services are not initialized.")
        except Exception as e:
            self.log_output(f"❌ Error injecting services: {str(e)}")
            raise

    def _initialize_services(self):
        """
        Initialize core processing engines using provided services.
        
        This method sets up:
        1. CycleExecutionService for chat cycle management
        2. PromptResponseHandler for response processing
        3. DiscordQueueProcessor for Discord integration
        4. TaskOrchestrator for task management
        5. DreamscapeGenerator for episode generation
        """
        try:
            # Initialize core services
            self.cycle_service = CycleExecutionService(
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                response_handler=self.response_handler,
                memory_manager=self.memory_manager,
                discord_manager=self.discord_manager,
                config_manager=self.config_manager,  
                logger=self.logger 
            )

            self.prompt_handler = PromptResponseHandler(
                config_manager=self.config_manager,
                logger=self.logger
            )
            
            self.discord_processor = DiscordQueueProcessor(
                config_manager=self.config_manager,
                logger=self.logger
            )
            
            self.task_orchestrator = TaskOrchestrator(
                logger=self.logger
            )
            
            # Configure output directory
            self.output_dir = self._get_output_directory()
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Initialize dreamscape generator
            self.dreamscape_generator = DreamscapeEpisodeGenerator(
                chat_manager=self.chat_manager,
                response_handler=self.response_handler,
                output_dir=self.output_dir,
                discord_manager=self.discord_manager
            )
            
            self.log_output("✅ Services initialized successfully")
            
        except Exception as e:
            self.log_output(f"❌ Error initializing services: {str(e)}")
            raise

    def _get_output_directory(self):
        """
        Get the output directory path from config or default.
        
        Returns:
            str: Path to the output directory
        """
        try:
            if hasattr(self.config_manager, "get"):
                return self.config_manager.get("dreamscape_output_dir", "outputs/dreamscape")
            return getattr(self.config_manager, "dreamscape_output_dir", "outputs/dreamscape")
        except Exception as e:
            self.log_output(f"⚠️ Warning: Using default output directory due to error: {str(e)}")
            return "outputs/dreamscape"

    def init_ui(self):
        """
        Set up the UI layout and components for the Dreamscape tab.
        
        This method initializes:
        1. Main layout with title
        2. Left panel with episode list and controls
        3. Right panel with content tabs
        4. Context management controls
        """
        try:
            main_layout = QVBoxLayout()
            self._setup_title(main_layout)
            
            splitter = QSplitter(Qt.Horizontal)
            left_widget = self._setup_left_panel()
            right_widget = self._setup_right_panel()
            
            splitter.addWidget(left_widget)
            splitter.addWidget(right_widget)
            splitter.setSizes([300, 700])  # 30% left, 70% right
            
            main_layout.addWidget(splitter)
            self.setLayout(main_layout)
            
        except Exception as e:
            self.log_output(f"❌ Error initializing UI: {str(e)}")
            raise

    def _setup_title(self, layout):
        """Set up the title section of the UI."""
        title = QLabel("Dreamscape Episode Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

    def _setup_left_panel(self):
        """
        Set up the left panel containing episode list and controls.
        
        Returns:
            QWidget: The configured left panel widget
        """
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Episode List Section
        episodes_group = self._setup_episode_list_group()
        left_layout.addWidget(episodes_group)
        
        # Controls Section
        controls_group = self._setup_controls_group()
        left_layout.addWidget(controls_group)
        
        return left_widget

    def _setup_episode_list_group(self):
        """
        Set up the episode list group box.
        
        Returns:
            QGroupBox: The configured episode list group
        """
        episodes_group = QGroupBox("Dreamscape Episodes")
        episodes_layout = QVBoxLayout()
        
        self.episode_list = QListWidget()
        self.episode_list.currentItemChanged.connect(self.on_episode_selected)
        episodes_layout.addWidget(self.episode_list)
        
        refresh_btn = QPushButton("Refresh Episodes")
        refresh_btn.clicked.connect(self.refresh_episode_list)
        episodes_layout.addWidget(refresh_btn)
        
        episodes_group.setLayout(episodes_layout)
        return episodes_group

    def _setup_controls_group(self):
        """
        Set up the generation controls group box.
        
        Returns:
            QGroupBox: The configured controls group
        """
        controls_group = QGroupBox("Generation Controls")
        controls_layout = QVBoxLayout()
        
        # Checkboxes
        self.headless_checkbox = QCheckBox("Headless Mode")
        controls_layout.addWidget(self.headless_checkbox)
        
        self.post_discord_checkbox = QCheckBox("Post to Discord")
        self.post_discord_checkbox.setChecked(True)
        controls_layout.addWidget(self.post_discord_checkbox)
        
        # Model Selection
        form_layout = QFormLayout()
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["gpt-4o", "gpt-4o-mini", "gpt-4"])
        form_layout.addRow("Model:", self.model_dropdown)
        controls_layout.addLayout(form_layout)
        
        # Generate Button
        self.generate_episodes_btn = QPushButton("Generate Dreamscape Episodes")
        self.generate_episodes_btn.clicked.connect(self.generate_dreamscape_episodes)
        controls_layout.addWidget(self.generate_episodes_btn)
        
        # Context Management
        context_layout = self._setup_context_controls()
        controls_layout.addLayout(context_layout)
        
        controls_group.setLayout(controls_layout)
        return controls_group

    def _setup_context_controls(self):
        """
        Set up the context management controls.
        
        Returns:
            QVBoxLayout: The configured context controls layout
        """
        context_layout = QVBoxLayout()
        context_layout.setContentsMargins(0, 10, 0, 0)
        
        # Send Context Button
        send_context_btn = QPushButton("Send Context to ChatGPT")
        send_context_btn.setToolTip("Send the current Dreamscape context to a ChatGPT chat")
        send_context_btn.clicked.connect(self.send_context_to_chatgpt)
        context_layout.addWidget(send_context_btn)
        
        # Auto-update Controls
        auto_update_layout = QHBoxLayout()
        self.auto_update_checkbox = QCheckBox("Schedule Auto-Updates")
        self.auto_update_checkbox.setToolTip("Schedule automatic context updates to ChatGPT")
        
        self.update_interval_combo = QComboBox()
        self.update_interval_combo.addItems(["1 day", "3 days", "7 days", "14 days", "30 days"])
        self.update_interval_combo.setCurrentIndex(2)  # Default to 7 days
        
        auto_update_layout.addWidget(self.auto_update_checkbox)
        auto_update_layout.addWidget(self.update_interval_combo)
        context_layout.addLayout(auto_update_layout)
        
        # Target Chat Selection
        target_chat_layout = QHBoxLayout()
        target_chat_layout.addWidget(QLabel("Target Chat:"))
        self.target_chat_input = QComboBox()
        self.target_chat_input.setEditable(True)
        self.target_chat_input.setToolTip("Leave empty to auto-select or enter a specific chat name")
        target_chat_layout.addWidget(self.target_chat_input)
        context_layout.addLayout(target_chat_layout)
        
        # Save Schedule Button
        save_schedule_btn = QPushButton("Save Schedule")
        save_schedule_btn.clicked.connect(self.save_context_schedule)
        context_layout.addWidget(save_schedule_btn)
        
        return context_layout

    def _setup_right_panel(self):
        """
        Set up the right panel containing content tabs.
        
        Returns:
            QTabWidget: The configured right panel tab widget
        """
        right_widget = QTabWidget()
        
        # Episode Content Tab
        content_tab = self._setup_content_tab()
        right_widget.addTab(content_tab, "Episode Content")
        
        # Context Memory Tab
        context_tab = self._setup_context_tab()
        right_widget.addTab(context_tab, "Context Memory")
        
        # Activity Log Tab
        log_tab = self._setup_log_tab()
        right_widget.addTab(log_tab, "Activity Log")
        
        return right_widget

    def _setup_content_tab(self):
        """
        Set up the episode content tab.
        
        Returns:
            QWidget: The configured content tab
        """
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)
        
        self.episode_content = QTextEdit()
        self.episode_content.setReadOnly(True)
        content_layout.addWidget(self.episode_content)
        
        share_layout = QHBoxLayout()
        share_discord_btn = QPushButton("Share to Discord")
        share_discord_btn.clicked.connect(self.share_to_discord)
        share_layout.addWidget(share_discord_btn)
        content_layout.addLayout(share_layout)
        
        return content_tab

    def _setup_context_tab(self):
        """
        Set up the context memory tab with filtering.
        
        Returns:
            QWidget: The configured context tab
        """
        context_tab = QWidget()
        context_layout = QVBoxLayout(context_tab)
        
        # Filter Controls
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by Theme:")
        self.context_filter_input = QLineEdit()
        self.context_filter_input.setPlaceholderText("Enter theme or keyword")
        self.context_filter_input.textChanged.connect(self.refresh_context_memory)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.context_filter_input)
        context_layout.addLayout(filter_layout)
        
        # Context Tree
        self.context_tree = QTreeWidget()
        self.context_tree.setHeaderLabels(["Property", "Value"])
        self.context_tree.setColumnWidth(0, 200)
        context_layout.addWidget(self.context_tree)
        
        # Refresh Button
        refresh_context_btn = QPushButton("Refresh Context Memory")
        refresh_context_btn.clicked.connect(self.refresh_context_memory)
        context_layout.addWidget(refresh_context_btn)
        
        return context_tab

    def _setup_log_tab(self):
        """
        Set up the activity log tab.
        
        Returns:
            QWidget: The configured log tab
        """
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        log_layout.addWidget(self.output_display)
        
        return log_tab

    def log_output(self, message: str):
        """
        Log messages to UI and console with consistent formatting.
        
        Args:
            message: The message to log
        """
        try:
            formatted_msg = f"[{datetime.now().strftime('%H:%M:%S')}] DREAMSCAPE: {message}"
            self.output_display.append(formatted_msg)
            
            if self.logger:
                self.logger.info(formatted_msg)
            else:
                print(formatted_msg)
                
            if self.dispatcher:
                self.dispatcher.emit_log_output(formatted_msg)
        except Exception as e:
            print(f"Error logging message: {str(e)}")

    def refresh_episode_list(self):
        """Refresh the list of episodes from the output directory."""
        try:
            self.episode_list.clear()
            
            # Check if output directory exists
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)
                self.log_output(f"Created output directory: {self.output_dir}")
                return
            
            episode_files = []
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".txt") and not filename == "dreamscape_context.json":
                    filepath = os.path.join(self.output_dir, filename)
                    if os.path.isfile(filepath):
                        # Extract timestamp and a guess at the episode # or ID from filename
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            timestamp = parts[0]
                            title_raw = parts[1].replace('.txt', '')
                            
                            # Attempt to parse out "episode #X" or "ds-XXX"
                            # or store it as raw if not found
                            episode_num = None
                            ds_id = None
                            
                            # Example match for: "Episode #10"
                            match_episode_num = re.search(r'episode\s*#(\d+)', title_raw, re.IGNORECASE)
                            if match_episode_num:
                                episode_num = int(match_episode_num.group(1))
                            
                            # Example match for DS-### (like DS-042)
                            match_ds_id = re.search(r'(ds-\d+)', title_raw, re.IGNORECASE)
                            if match_ds_id:
                                ds_id = match_ds_id.group(1).upper()
                            
                            # Reformat title for display
                            display_title = title_raw.replace('_', ' ').title()
                            episode_files.append({
                                'filename': filename,
                                'filepath': filepath,
                                'timestamp': timestamp,
                                'title': display_title,
                                'episode_num': episode_num,
                                'episode_id': ds_id
                            })
            
            # Sort by episode number if available, else by timestamp (descending)
            # This is just a naive approach; adjust as needed
            episode_files.sort(
                key=lambda x: (
                    - (x['episode_num'] or 0),
                    x['timestamp']
                ),
                reverse=True
            )
            
            for episode in episode_files:
                # Build a display label including episode_id if found
                if episode['episode_id']:
                    label = f"[{episode['episode_id']}] "
                else:
                    label = ""
                
                if episode['episode_num']:
                    label += f"Episode #{episode['episode_num']}: "
                
                label += f"{episode['title']} ({episode['timestamp']})"
                
                item_idx = self.episode_list.count()
                self.episode_list.addItem(label)
                # Store full data in item's user role
                self.episode_list.setItemData(item_idx, episode, Qt.UserRole)
            
            self.log_output(f"Found {len(episode_files)} episodes in {self.output_dir}")
            
        except Exception as e:
            self.log_output(f"Error refreshing episode list: {str(e)}")
    
    def refresh_context_memory(self):
        """Refresh the context memory display, optionally filtering by theme."""
        try:
            if not self.dreamscape_generator:
                self.log_output("Dreamscape generator not initialized.")
                return
                
            context = self.dreamscape_generator.get_context_summary()
            
            self.context_tree.clear()
            
            # Filter text
            filter_text = self.context_filter_input.text().strip().lower()  # ADDED
            # We'll only show episodes whose theme or title matches if user typed anything
            
            # Next Episode # (from context)
            next_episode_num = context.get("episode_count", 0) + 1
            next_episode_item = QTreeWidgetItem(self.context_tree, ["Next Episode", f"Episode #{next_episode_num}"])
            
            # Episode Count
            QTreeWidgetItem(self.context_tree, ["Episode Count", str(context.get("episode_count", 0))])
            
            # Last Updated
            QTreeWidgetItem(self.context_tree, ["Last Updated", str(context.get("last_updated", "Never"))])
            
            # Current Themes
            themes_item = QTreeWidgetItem(self.context_tree, ["Active Themes", ""])
            for theme in context.get("active_themes", []):
                # If filter_text is not empty, only show matching themes
                if filter_text and filter_text not in theme.lower():
                    continue
                QTreeWidgetItem(themes_item, ["", theme])
            
            # Recent Episodes
            recent_item = QTreeWidgetItem(self.context_tree, ["Recent Episodes", ""])
            recent_episodes = context.get("recent_episodes", [])
            
            for i, episode in enumerate(recent_episodes):
                ep_title = episode.get("title", "Untitled")
                ep_themes = episode.get("themes", [])
                
                # If filter is present, check if ep_title or any theme matches
                if filter_text:
                    title_match = (filter_text in ep_title.lower())
                    theme_match = any(filter_text in t.lower() for t in ep_themes)
                    if not (title_match or theme_match):
                        continue
                
                # We can show them in order or try to show them reversed
                # For demonstration, we assume the earliest item is first
                ep_num = context.get("episode_count", 0) - i
                ep_item = QTreeWidgetItem(recent_item, [f"Episode #{ep_num}", ep_title])
                
                # Timestamp
                QTreeWidgetItem(ep_item, ["Date", episode.get("timestamp", "")])
                
                # Themes
                ep_themes_parent = QTreeWidgetItem(ep_item, ["Themes", ""])
                for theme in ep_themes:
                    QTreeWidgetItem(ep_themes_parent, ["", theme])
            
            self.context_tree.expandAll()
            
        except Exception as e:
            self.log_output(f"Error refreshing context memory: {str(e)}")
            
    def on_episode_selected(self, current, previous):
        """Handle episode selection in the list."""
        if not current:
            self.episode_content.clear()
            return
            
        try:
            episode_data = current.data(Qt.UserRole)
            if not episode_data:
                return
                
            filepath = os.path.join(self.output_dir, episode_data.get('filename'))
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.episode_content.setPlainText(content)
                
        except Exception as e:
            self.log_output(f"Error loading episode content: {str(e)}")
            
    def share_to_discord(self):
        """Share the currently selected episode to Discord."""
        if not self.episode_content.toPlainText():
            QMessageBox.warning(self, "No Content", "Please select an episode first.")
            return
            
        if not self.discord_manager:
            QMessageBox.warning(self, "Discord Not Available", 
                               "Discord service is not available. Check your Discord configuration.")
            return
            
        try:
            content = self.episode_content.toPlainText()
            # Truncate if too long
            if len(content) > 1900:  # Discord has 2000 char limit
                content = content[:1900] + "..."
                
            self.discord_manager.send_message(content)
            self.log_output("Episode shared to Discord successfully.")
            QMessageBox.information(self, "Success", "Episode shared to Discord successfully.")
            
        except Exception as e:
            self.log_output(f"Error sharing to Discord: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to share to Discord: {str(e)}")
            
    def handle_prompt_executed(self, prompt_name, response_data):
        """Handle prompt_executed signal from the dispatcher."""
        self.log_output(f"Prompt '{prompt_name}' executed with response.")
        
    def handle_discord_event(self, event_type, event_data):
        """Handle discord_event signal from the dispatcher."""
        self.log_output(f"Discord event '{event_type}' received.")

    @asyncSlot()
    async def generate_dreamscape_episodes(self):
        """
        Trigger asynchronous Dreamscape episode generation with validation.
        
        This method:
        1. Validates required services
        2. Confirms user intent
        3. Initiates async generation process
        4. Updates UI state
        """
        if not self._validate_required_services():
            return

        if not self._confirm_generation():
            return

        self.log_output(f"🚀 Starting Dreamscape episode generation in: {self.output_dir}")
        
        headless = self.headless_checkbox.isChecked()
        use_discord = self.post_discord_checkbox.isChecked()
        
        task_id = f"dreamscape_gen_{int(datetime.now().timestamp())}"
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
            
        self._update_ui_for_generation(False)
        
        task = asyncio.create_task(self._generate_episodes_async(task_id, headless, use_discord))
        self.running_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    def _validate_required_services(self):
        """
        Validate that required services are initialized.
        
        Returns:
            bool: True if all required services are available
        """
        if not self.chat_manager or not self.dreamscape_generator:
            self.log_output("❌ Error: Required services not initialized.")
            QMessageBox.critical(self, "Error", "Chat manager or Dreamscape generator not initialized.")
            return False
        return True

    def _confirm_generation(self):
        """
        Confirm with user before starting generation.
        
        Returns:
            bool: True if user confirms
        """
        confirm = QMessageBox.question(
            self, "Confirm Generation",
            "This will open a browser and send prompts to all eligible ChatGPT chats. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        return confirm == QMessageBox.Yes

    def _update_ui_for_generation(self, enabled: bool):
        """
        Update UI elements during generation process.
        
        Args:
            enabled: Whether to enable or disable UI elements
        """
        self.generate_episodes_btn.setEnabled(enabled)
        self.generate_episodes_btn.setText(
            "Generate Dreamscape Episodes" if enabled else "Generation in progress..."
        )

    async def _generate_episodes_async(self, task_id: str, headless: bool, use_discord: bool):
        """
        Async wrapper for episode generation with progress reporting.
        
        Args:
            task_id: Unique identifier for the generation task
            headless: Whether to run in headless mode
            use_discord: Whether to enable Discord integration
            
        Returns:
            dict: Generation results including episode counts and status
        """
        try:
            if not use_discord:
                self.dreamscape_generator.discord_manager = None
                self.log_output("Discord posting disabled for this run.")
            
            next_episode = self.dreamscape_generator.get_episode_number()
            self.log_output(f"Preparing to generate Episode #{next_episode}")
            
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 20, f"Sending context updates for Episode #{next_episode}...")
            
            self.log_output("Running Dreamscape generator with automated context updates...")
            entries = self.dreamscape_generator.generate_dreamscape_episodes()
            
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 90, "Generation complete, refreshing UI...")
            
            self.refresh_episode_list()
            self.refresh_context_memory()
            
            new_count = self.dreamscape_generator.context_memory.get("episode_count", 0)
            
            return {
                "episodes_created": len(entries) if entries else 0,
                "latest_episode": next_episode,
                "total_episodes": new_count,
                "output_directory": self.output_dir,
                "success": True,
                "context_updated": True
            }
            
        except Exception as e:
            self.log_output(f"❌ Error generating episodes: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

    def _on_task_done(self, task_id: str, task: asyncio.Task):
        """
        Handle completion or failure of an asynchronous task.
        
        Args:
            task_id: Unique identifier for the completed task
            task: The completed asyncio task
        """
        self.running_tasks.pop(task_id, None)
        self._update_ui_for_generation(True)
        
        try:
            result = task.result()
            if "latest_episode" in result:
                self.log_output(f"✅ Successfully generated Episode #{result['latest_episode']}!")
            else:
                self.log_output(f"✅ Task {task_id} completed successfully!")
            
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                if task_id.startswith("dreamscape_gen_"):
                    self.dispatcher.emit_dreamscape_generated(result)
                    
        except asyncio.CancelledError:
            self.log_output(f"❌ Task {task_id} was cancelled.")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, "Task was cancelled.")
                
        except Exception as e:
            self.log_output(f"❌ Task {task_id} failed with error: {str(e)}")

    @asyncSlot()
    async def send_context_to_chatgpt(self):
        """
        Send the current Dreamscape context to ChatGPT asynchronously.
        
        This method:
        1. Validates service availability
        2. Confirms target chat
        3. Initiates async context update
        """
        dreamscape_service = self._get_dreamscape_service()
        if not dreamscape_service:
            return
            
        target_chat = self.target_chat_input.currentText().strip() or None
        
        if not self._confirm_context_update(target_chat):
            return
            
        self.log_output(f"🚀 Sending Dreamscape context to {target_chat or 'auto-selected chat'}...")
        
        task_id = f"context_update_{int(datetime.now().timestamp())}"
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
            
        task = asyncio.create_task(self._send_context_async(task_id, dreamscape_service, target_chat))
        self.running_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_context_task_done(task_id, t))

    def _get_dreamscape_service(self):
        """
        Get the Dreamscape service with validation.
        
        Returns:
            object: The Dreamscape service or None if not available
        """
        dreamscape_service = None
        if self.ui_logic and hasattr(self.ui_logic, 'get_service'):
            dreamscape_service = self.ui_logic.get_service('dreamscape_service')
            
        if not dreamscape_service or not hasattr(dreamscape_service, 'send_context_to_chatgpt'):
            QMessageBox.critical(self, "Error", "DreamscapeService not available or doesn't support context sending")
            self.log_output("❌ Error: Cannot send context, service not available.")
            return None
            
        return dreamscape_service

    def _confirm_context_update(self, target_chat):
        """
        Confirm context update with user.
        
        Args:
            target_chat: The target chat name or None for auto-select
            
        Returns:
            bool: True if user confirms
        """
        confirm = QMessageBox.question(
            self, "Confirm Context Update", 
            f"This will open a browser and send the latest Dreamscape context to {target_chat or 'auto-selected chat'}. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        return confirm == QMessageBox.Yes

    async def _send_context_async(self, task_id: str, service, target_chat: str):
        """
        Async wrapper for sending context to ChatGPT.
        
        Args:
            task_id: Unique identifier for the context update task
            service: The Dreamscape service instance
            target_chat: The target chat name or None for auto-select
            
        Returns:
            dict: Context update results
        """
        try:
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 30, "Opening browser...")
                
            result = service.send_context_to_chatgpt(chat_name=target_chat)
            
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Context sent successfully")
                
            return {
                "success": result,
                "target_chat": target_chat or "auto-selected",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_output(f"❌ Error sending context: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

    def _on_context_task_done(self, task_id: str, task: asyncio.Task):
        """
        Handle completion of context update task.
        
        Args:
            task_id: Unique identifier for the completed task
            task: The completed asyncio task
        """
        self.running_tasks.pop(task_id, None)
        
        try:
            result = task.result()
            self.log_output("✅ Context update sent successfully.")
            QMessageBox.information(self, "Success", "Context update sent to ChatGPT successfully.")
            self.refresh_context_memory()
            
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                
        except Exception as e:
            self.log_output(f"❌ Context update failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to send context update: {str(e)}")
            
    def save_context_schedule(self):
        """
        Save the context update schedule to configuration.
        
        This method:
        1. Validates schedule settings
        2. Gets service reference
        3. Saves schedule configuration
        """
        if not self._validate_schedule_settings():
            return

        dreamscape_service = self._get_dreamscape_service()
        if not dreamscape_service:
            return

        interval_days = self._get_schedule_interval()
        target_chat = self.target_chat_input.currentText().strip() or None

        try:
            result = dreamscape_service.schedule_context_updates(
                interval_days=interval_days,
                chat_name=target_chat
            )
            
            if result:
                self.log_output(f"✅ Context updates scheduled every {interval_days} days.")
                QMessageBox.information(
                    self, "Schedule Saved", 
                    f"Dreamscape context will be automatically sent to ChatGPT every {interval_days} days."
                )
            else:
                self.log_output("❌ Failed to save context update schedule.")
                QMessageBox.warning(self, "Scheduling Failed", "Failed to save the context update schedule.")
                
        except Exception as e:
            self.log_output(f"❌ Error scheduling updates: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to schedule updates: {str(e)}")

    def _validate_schedule_settings(self):
        """
        Validate that scheduling is enabled.
        
        Returns:
            bool: True if scheduling is enabled
        """
        if not self.auto_update_checkbox.isChecked():
            QMessageBox.information(
                self, "Scheduling Disabled", 
                "Auto-updates are not enabled. Enable the checkbox to schedule updates."
            )
            return False
        return True

    def _get_schedule_interval(self):
        """
        Get the selected schedule interval in days.
        
        Returns:
            int: Number of days between updates
        """
        interval_text = self.update_interval_combo.currentText()
        return int(interval_text.split()[0])

    def populate_chat_list(self):
        """
        Populate the target chat dropdown with available chat titles.
        
        This method:
        1. Clears existing items
        2. Adds available chats from chat manager
        3. Auto-selects Dreamscape chat if available
        """
        try:
            self.target_chat_input.clear()
            self.target_chat_input.addItem("")
            
            if not self.chat_manager:
                return
                
            all_chats = self.chat_manager.get_all_chat_titles()
            if not all_chats:
                return
                
            for chat in all_chats:
                title = chat.get('title', '')
                if title:
                    self.target_chat_input.addItem(title)
                    
            self._auto_select_dreamscape_chat()
                    
        except Exception as e:
            self.log_output(f"Error populating chat list: {str(e)}")

    def _auto_select_dreamscape_chat(self):
        """Auto-select a chat with 'dreamscape' in the title if available."""
        dreamscape_found = False
        for i in range(self.target_chat_input.count()):
            if "dreamscape" in self.target_chat_input.itemText(i).lower():
                self.target_chat_input.setCurrentIndex(i)
                dreamscape_found = True
                break
                
        if not dreamscape_found and self.auto_update_checkbox.isChecked():
            self.log_output("⚠️ Warning: No dedicated Dreamscape chat found. Consider creating one.")

    def on_tab_shown(self):
        """Refresh all data when the tab becomes visible."""
        self.refresh_episode_list()
        self.refresh_context_memory()
        self.populate_chat_list()

    def load_schedule_settings(self):
        """
        Load scheduling settings from configuration file.
        
        This method:
        1. Reads schedule configuration
        2. Updates UI elements with saved settings
        3. Logs next scheduled update
        """
        try:
            schedule_file = os.path.join(self.output_dir, "context_update_schedule.json")
            if not os.path.exists(schedule_file):
                return
                
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
                
            self._apply_schedule_settings(schedule)
            self._update_schedule_ui(schedule)
            self._log_next_update(schedule)
                    
        except Exception as e:
            self.log_output(f"Error loading schedule settings: {str(e)}")

    def _apply_schedule_settings(self, schedule):
        """
        Apply loaded schedule settings to internal state.
        
        Args:
            schedule: Dictionary containing schedule settings
        """
        self.auto_update_checkbox.setChecked(schedule.get('enabled', False))
        interval_days = schedule.get('interval_days', 7)
        
        for i in range(self.update_interval_combo.count()):
            days_text = self.update_interval_combo.itemText(i).split()[0]
            if days_text.isdigit() and int(days_text) == interval_days:
                self.update_interval_combo.setCurrentIndex(i)
                break

    def _update_schedule_ui(self, schedule):
        """
        Update UI elements with schedule settings.
        
        Args:
            schedule: Dictionary containing schedule settings
        """
        target_chat = schedule.get('target_chat', '')
        if target_chat:
            found = False
            for i in range(self.target_chat_input.count()):
                if self.target_chat_input.itemText(i) == target_chat:
                    self.target_chat_input.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.target_chat_input.addItem(target_chat)
                self.target_chat_input.setCurrentIndex(self.target_chat_input.count() - 1)

    def _log_next_update(self, schedule):
        """
        Log the next scheduled update time.
        
        Args:
            schedule: Dictionary containing schedule settings
        """
        next_update_raw = schedule.get('next_update', '')
        if next_update_raw:
            try:
                next_update_dt = datetime.fromisoformat(next_update_raw.replace('Z', '+00:00'))
                self.log_output(
                    f"Loaded context update schedule (next update: {next_update_dt.strftime('%Y-%m-%d %H:%M')})"
                )
            except Exception:
                pass

    def _setup_timers(self):
        """Initialize and configure timer-based operations."""
        # Episode list refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_episode_list)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Tab visibility refresh timer
        self.tab_shown_timer = QTimer(self)
        self.tab_shown_timer.setSingleShot(True)
        self.tab_shown_timer.timeout.connect(self.on_tab_shown)

    def _load_initial_data(self):
        """Load initial data and settings."""
        self.refresh_episode_list()
        self.refresh_context_memory()
        self.populate_chat_list()
        self.load_schedule_settings()
