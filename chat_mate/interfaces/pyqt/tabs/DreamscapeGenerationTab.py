import os
import re
import logging
from datetime import datetime
from typing import List, Dict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter, QListWidget,
    QPushButton, QLabel, QCheckBox, QComboBox, QTextEdit, QPlainTextEdit,
    QTreeWidget, QTreeWidgetItem, QGroupBox, QLineEdit, QFileDialog, QMessageBox, QProgressDialog, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot

from asyncqt import asyncSlot

from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
from core.TemplateManager import TemplateManager

from interfaces.pyqt.tabs.dreamscape_generation import (
    EpisodeGenerator, ContextManager, UIManager
)

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
        self.output_display = None  # Initialize early for logging
        
        # Inject Services
        self._inject_services(prompt_manager, chat_manager, response_handler, memory_manager, discord_manager)

        # Initialize Core Engines
        self._initialize_services()

        # Initialize UI
        self.init_ui()
        
        # Task Management
        self.running_tasks = {}
        
        # Initialize Component Managers
        self._initialize_component_managers()
        
        # Setup Timers
        self._setup_timers()
        
        # Initial Data Load
        self._load_initial_data()

    def _inject_services(self, prompt_manager, chat_manager, response_handler, memory_manager, discord_manager):
        """Inject services directly or fetch from ui_logic controller."""
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
        """Initialize core processing engines using provided services."""
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

    def _initialize_component_managers(self):
        """Initialize the component managers for modularized functionality."""
        try:
            # Template manager initialization
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            dreamscape_dir = os.path.join(base_dir, 'templates', 'dreamscape_templates')
            self.template_manager = TemplateManager(template_dir=dreamscape_dir)
            
            # Episode generator
            self.episode_generator = EpisodeGenerator(
                parent_widget=self,
                logger=self.logger,
                chat_manager=self.chat_manager,
                config_manager=self.config_manager
            )
            
            # Context manager
            self.context_manager = ContextManager(
                parent_widget=self,
                logger=self.logger,
                chat_manager=self.chat_manager,
                dreamscape_generator=self.dreamscape_generator,
                template_manager=self.template_manager
            )
            
            # UI manager
            self.ui_manager = UIManager(
                parent_widget=self,
                logger=self.logger,
                episode_list=self.episode_list if hasattr(self, 'episode_list') else None,
                template_manager=self.template_manager,
                output_dir=self.output_dir
            )
            
            self.log_output("✅ Component managers initialized successfully")
            
        except Exception as e:
            self.log_output(f"❌ Error initializing component managers: {str(e)}")

    def _get_output_directory(self):
        """Get the output directory path from config or default."""
        try:
            if hasattr(self.config_manager, "get"):
                return self.config_manager.get("dreamscape_output_dir", "outputs/dreamscape")
            return getattr(self.config_manager, "dreamscape_output_dir", "outputs/dreamscape")
        except Exception as e:
            self.log_output(f"⚠️ Warning: Using default output directory due to error: {str(e)}")
            return "outputs/dreamscape"

    def init_ui(self):
        """Set up the UI layout and components for the Dreamscape tab."""
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
        """Set up the left panel containing episode list and controls."""
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
        """Set up the episode list group box."""
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
        """Set up the generation controls group box."""
        controls_group = QGroupBox("Generation Controls")
        controls_layout = QVBoxLayout()
        
        # Checkboxes
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.headless_checkbox.setToolTip("Run browser in headless mode (no visible window)")
        controls_layout.addWidget(self.headless_checkbox)
        
        self.post_discord_checkbox = QCheckBox("Post to Discord")
        self.post_discord_checkbox.setToolTip("Send episode summaries to Discord when generated")
        self.post_discord_checkbox.setChecked(True)
        controls_layout.addWidget(self.post_discord_checkbox)

        self.reverse_order_checkbox = QCheckBox("Reverse Order")
        self.reverse_order_checkbox.setToolTip("Process chats in reverse chronological order when generating episodes")
        controls_layout.addWidget(self.reverse_order_checkbox)
        
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
        
        # Process All Chats Checkbox
        self.process_all_chats_checkbox = QCheckBox("Process All Chats")
        self.process_all_chats_checkbox.setToolTip("When checked, will process all available chats instead of just the selected one")
        controls_layout.addWidget(self.process_all_chats_checkbox)
        
        # Prompt Text Edit (added here since it's needed for episode generation)
        self.prompt_text_edit = QTextEdit()
        self.prompt_text_edit.setPlaceholderText("Enter your prompt here...")
        self.prompt_text_edit.setMaximumHeight(100)
        controls_layout.addWidget(QLabel("Prompt:"))
        controls_layout.addWidget(self.prompt_text_edit)
        
        controls_group.setLayout(controls_layout)
        return controls_group

    def _setup_context_controls(self):
        """Set up the context management controls."""
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
        """Set up the right panel containing content, context, and log tabs."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self._setup_content_tab(), "Content")
        self.tab_widget.addTab(self._setup_context_tab(), "Context")
        self.tab_widget.addTab(self._setup_log_tab(), "Log")
        self.tab_widget.addTab(self._setup_template_tab(), "Templates")
        
        right_layout.addWidget(self.tab_widget)
        return right_widget

    def _setup_content_tab(self):
        """Set up the episode content tab."""
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
        """Set up the context memory tab with filtering."""
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
        """Set up the activity log tab."""
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        log_layout.addWidget(self.output_display)
        
        return log_tab

    def _setup_template_tab(self):
        """Set up the template management tab."""
        template_widget = QWidget()
        layout = QVBoxLayout(template_widget)
        
        # Template selection
        template_group = QGroupBox("Template Selection")
        template_layout = QFormLayout()
        
        self.template_dropdown = QComboBox()
        self.template_dropdown.currentTextChanged.connect(self._on_template_selected)
        template_layout.addRow("Active Template:", self.template_dropdown)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Template preview
        preview_group = QGroupBox("Template Preview")
        preview_layout = QVBoxLayout()
        
        self.template_preview = QPlainTextEdit()
        self.template_preview.setReadOnly(True)
        preview_layout.addWidget(self.template_preview)
        
        # Preview button
        self.preview_button = QPushButton("Preview Template")
        self.preview_button.clicked.connect(self.render_dreamscape_template)
        preview_layout.addWidget(self.preview_button)
        
        # Context validation
        validation_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate Context")
        self.validate_btn.clicked.connect(self._validate_template_context)
        validation_layout.addWidget(self.validate_btn)
        
        self.missing_vars_label = QLabel()
        validation_layout.addWidget(self.missing_vars_label)
        validation_layout.addStretch()
        
        preview_layout.addLayout(validation_layout)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Save options
        save_group = QGroupBox("Save Options")
        save_layout = QHBoxLayout()
        
        self.save_txt_btn = QPushButton("Save as TXT")
        self.save_txt_btn.clicked.connect(lambda: self._save_rendered_output('txt'))
        save_layout.addWidget(self.save_txt_btn)
        
        self.save_md_btn = QPushButton("Save as MD")
        self.save_md_btn.clicked.connect(lambda: self._save_rendered_output('md'))
        save_layout.addWidget(self.save_md_btn)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        return template_widget

    # ===== EVENT HANDLERS =====
    
    def on_episode_selected(self, current, previous):
        """Handle episode selection in the list."""
        self.ui_manager.update_episode_content(self.episode_content, current)
            
    def share_to_discord(self):
        """Share the currently selected episode to Discord."""
        self.ui_manager.share_to_discord(self.episode_content, self.discord_manager)
    
    def _on_template_selected(self, template_name):
        """Handle template selection change."""
        if not template_name:
            return
        
        context = self.context_manager.get_preview_context()
        self.ui_manager.render_template_preview(
            template_name=template_name,
            preview=self.template_preview,
            context=context
        )
        
    def _validate_template_context(self):
        """Validate the current template against available context."""
        if not self.template_manager.active_template:
            return
        
        context = self.context_manager.get_preview_context()
        missing = self.template_manager.validate_context(
            self.template_manager.active_template,
            context
        )
        
        if missing:
            self.missing_vars_label.setText(f"Missing variables: {', '.join(missing)}")
            self.missing_vars_label.setStyleSheet("color: red")
        else:
            self.missing_vars_label.setText("✓ All variables present")
            self.missing_vars_label.setStyleSheet("color: green")
    
    def _save_rendered_output(self, format='txt'):
        """Save the rendered template output to a file."""
        self.ui_manager.save_rendered_output(format)

    # ===== DATA & STATE MANAGEMENT =====
    
    def refresh_episode_list(self):
        """Refresh the list of episodes from the output directory."""
        reverse_order = self.reverse_order_checkbox.isChecked()
        self.ui_manager.refresh_episode_list(reverse_order)
    
    def refresh_context_memory(self):
        """Refresh the context memory display with optional filtering."""
        filter_text = self.context_filter_input.text() if hasattr(self, 'context_filter_input') else ""
        self.context_manager.refresh_context_display(self.context_tree, filter_text)

    def log_output(self, message: str):
        """Log a message to both the UI and the logger."""
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.log_output(self.output_display, message)
        else:
            # Fallback if UI manager isn't initialized yet
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            
            if hasattr(self, 'output_display') and self.output_display:
                self.output_display.append(formatted_message)
                
            if self.dispatcher and hasattr(self.dispatcher, 'emit_append_output'):
                self.dispatcher.emit_append_output(message)
                
            self.logger.info(message)

    def render_dreamscape_template(self):
        """Render the current template with context data."""
        selected_template = self.template_dropdown.currentText()
        if not selected_template:
            return
            
        context = self.context_manager.get_preview_context()
        self.ui_manager.render_template_preview(
            template_name=selected_template,
            preview=self.template_preview,
            context=context
        )

    def _setup_timers(self):
        """Set up timers for auto-update functionality."""
        if hasattr(self, 'ui_manager'):
            self.ui_manager.setup_auto_update_timer(
                self.auto_update_checkbox,
                self.update_interval_combo
            )

    def _load_initial_data(self):
        """Load initial data after initialization."""
        try:
            # Load templates
            if hasattr(self, 'ui_manager') and hasattr(self, 'template_dropdown'):
                self.ui_manager.load_templates(self.template_dropdown)
                
            # Refresh episode list
            self.refresh_episode_list()
            
            # Refresh context memory
            self.refresh_context_memory()
            
            # Populate chat list if we have one
            if hasattr(self, 'target_chat_input') and self.target_chat_input:
                self.populate_chat_list()
                
            self.log_output("🚀 Initial data loaded")
            
        except Exception as e:
            self.log_output(f"⚠️ Warning: Error loading initial data: {str(e)}")

    # ===== MAIN FUNCTIONALITY =====
    
    def send_context_to_chatgpt(self):
        """Send the current Dreamscape context to the selected ChatGPT chat."""
        chat_url = self.get_selected_chat_url()
        self.context_manager.send_context_to_chat(chat_url)

    def save_context_schedule(self):
        """Save scheduling configuration for auto context updates."""
        enabled = self.auto_update_checkbox.isChecked()
        interval = self.update_interval_combo.currentText()
        success = self.context_manager.save_context_schedule(enabled, interval)
        
        if success:
            self._setup_timers()
            QMessageBox.information(self, "Schedule Saved", "Context update schedule saved successfully.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save context schedule.")

    @asyncSlot()
    async def generate_dreamscape_episodes(self):
        """Generate dreamscape episodes from chat history."""
        try:
            # Get process mode
            process_all = self.process_all_chats_checkbox.isChecked()
            
            # Get prompt text
            prompt_text = self.prompt_text_edit.toPlainText()
            
            # Get selected chat URL if not processing all
            chat_url = None if process_all else self.get_selected_chat_url()
            
            # Get model
            model = self.model_dropdown.currentText()
            
            # Get reverse order setting
            reverse_order = self.reverse_order_checkbox.isChecked()
            
            # Populate chat list if empty
            if not process_all and not chat_url:
                self.populate_chat_list()
                chat_url = self.get_selected_chat_url()
                
            # Generate episodes
            success = await self.episode_generator.generate_episodes(
                prompt_text=prompt_text,
                chat_url=chat_url,
                model=model,
                process_all=process_all,
                reverse_order=reverse_order
            )
            
            # Refresh episode list if successful
            if success:
                self.refresh_episode_list()
                
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def populate_chat_list(self):
        """Populate the chat dropdown with available chats."""
        try:
            # Clear existing items
            chat_dropdown = getattr(self, 'target_chat_input', None)
            if not chat_dropdown:
                return 0
                
            chat_dropdown.clear()
            
            # Get all chats
            if not self.chat_manager:
                self.logger.error("Chat manager not available")
                return 0
                
            chat_list = self.chat_manager.get_all_chat_titles()
            self.logger.info(f"Found {len(chat_list)} chats")
            
            # Populate dropdown
            for chat in chat_list:
                title = chat.get("title", "Untitled")
                url = chat.get("link", "")
                chat_dropdown.addItem(title, userData=url)
                
            return len(chat_list)
            
        except Exception as e:
            self.logger.error(f"Error populating chat list: {str(e)}")
            return 0

    def get_selected_chat_url(self):
        """Get the URL of the currently selected chat."""
        if self.process_all_chats_checkbox and self.process_all_chats_checkbox.isChecked():
            return None
            
        if hasattr(self, 'target_chat_input') and self.target_chat_input.currentIndex() >= 0:
            return self.target_chat_input.currentData()
            
        return None
