import os
import logging
from datetime import datetime
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter, QListWidget,
    QPushButton, QLabel, QCheckBox, QComboBox, QTextEdit, QPlainTextEdit,
    QTreeWidget, QGroupBox, QLineEdit, QFileDialog, QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from qasync import asyncSlot

# Import the ServiceInitializer and component managers
from interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer import ServiceInitializer
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager

logger = logging.getLogger(__name__)

class DreamscapeGenerationTab(QWidget):
    """
    Main UI tab for generating and managing Dreamscape episodes.
    Uses DreamscapeSystemLoader for service initialization and management.
    """

    def __init__(self, dispatcher=None, prompt_manager=None, chat_manager=None, response_handler=None,
                 memory_manager=None, discord_manager=None, ui_logic=None, config_manager=None, logger=None):
        super().__init__()

        # -------------------------
        # 1) INIT LOGGER & SERVICES
        # -------------------------
        self.logger = logger or logging.getLogger(__name__)

        # Initialize UI elements to None
        self._initialize_ui_vars()

        # -------------------------
        # 2) SET UP THE UI FIRST
        # -------------------------
        self.init_ui()

        # -------------------------
        # 3) INIT SERVICES
        # -------------------------
        # Use ServiceInitializer with DreamscapeSystemLoader to inject and initialize required services
        self.service_initializer = ServiceInitializer(self, config_manager, self.logger)
        services = self.service_initializer.initialize_services(
            prompt_manager, chat_manager, response_handler,
            memory_manager, discord_manager, ui_logic
        )
        self._store_service_references(services)

        # -------------------------
        # 4) TIMERS & DATA LOAD
        # -------------------------
        # Ensure the UI is built, then set up timers and connect signals
        self._setup_timers()
        QTimer.singleShot(500, self._load_initial_data)
        self._connect_ui_signals()

    def _initialize_ui_vars(self):
        """Helper to set all UI instance variables to None initially."""
        self.auto_update_checkbox = None
        self.update_interval_combo = None
        self.target_chat_input = None
        self.template_dropdown = None
        self.process_all_chats_checkbox = None
        self.reverse_order_checkbox = None
        self.prompt_text_edit = None
        self.model_dropdown = None
        self.episode_list = None
        self.headless_checkbox = None
        self.post_discord_checkbox = None
        self.generate_button = None
        self.cancel_button = None
        self.output_display = None
        self.context_filter_input = None
        self.context_tree = None
        self.episode_content = None
        self.template_preview = None
        self.preview_button = None
        self.validate_btn = None
        self.missing_vars_label = None
        self.save_txt_btn = None
        self.save_md_btn = None
        self.tab_widget = None

    def _store_service_references(self, services):
        """Store references to all initialized core services/components."""
        core_services = services['core_services']
        component_managers = services['component_managers']

        # Store core services
        self.cycle_service = core_services.get('cycle_service')
        self.prompt_handler = core_services.get('prompt_handler')
        self.discord_processor = core_services.get('discord_processor')
        self.task_orchestrator = core_services.get('task_orchestrator')
        self.dreamscape_generator = core_services.get('dreamscape_generator')

        # Store component managers
        self.template_manager = component_managers.get('template_manager')
        self.episode_generator = component_managers.get('episode_generator')
        self.context_manager = component_managers.get('context_manager')
        self.ui_manager = component_managers.get('ui_manager')

        # Store output directory
        self.output_dir = services.get('output_dir')

        # Log service initialization status
        self._log_service_status()

    def _log_service_status(self):
        """Log the status of all initialized services."""
        services_status = {
            'Core Services': {
                'Cycle Service': bool(self.cycle_service),
                'Prompt Handler': bool(self.prompt_handler),
                'Discord Processor': bool(self.discord_processor),
                'Task Orchestrator': bool(self.task_orchestrator),
                'Dreamscape Generator': bool(self.dreamscape_generator)
            },
            'Component Managers': {
                'Template Manager': bool(self.template_manager),
                'Episode Generator': bool(self.episode_generator),
                'Context Manager': bool(self.context_manager),
                'UI Manager': bool(self.ui_manager)
            }
        }

        self.logger.info("Service initialization status:")
        for category, services in services_status.items():
            self.logger.info(f"\n{category}:")
            for service, status in services.items():
                status_symbol = "✅" if status else "❌"
                self.logger.info(f"  {status_symbol} {service}")

    def _setup_timers(self):
        """Set up any required timers for the UI."""
        pass  # Implement if needed

    def _load_initial_data(self):
        """Load initial data after UI setup."""
        if self.ui_manager:
            # Pass the specific widgets required by UIManager methods
            if hasattr(self, 'template_dropdown'):
                 self.ui_manager.load_templates()
            else:
                 self.logger.error("Cannot load templates: template_dropdown not found on self.")
            
            self.ui_manager.refresh_episode_list()
        else:
            self.logger.error("UI Manager not initialized - cannot load initial data")

    # ------------------------------------------------------------
    # UI INIT
    # ------------------------------------------------------------
    def init_ui(self):
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

    def _setup_title(self, layout):
        title = QLabel("Dreamscape Episode Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

    def _setup_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        episodes_group = self._setup_episode_list_group()
        left_layout.addWidget(episodes_group)

        controls_group = self._setup_controls_group()
        left_layout.addWidget(controls_group)

        return left_widget

    def _setup_episode_list_group(self):
        episodes_group = QGroupBox("Dreamscape Episodes")
        episodes_layout = QVBoxLayout()
        self.episode_list = QListWidget()
        episodes_layout.addWidget(self.episode_list)
        self.refresh_episodes_btn = QPushButton("Refresh Episodes")
        episodes_layout.addWidget(self.refresh_episodes_btn)
        episodes_group.setLayout(episodes_layout)
        return episodes_group

    def _setup_controls_group(self):
        controls_group = QGroupBox("Generation Controls")
        controls_layout = QVBoxLayout()

        # -- CREATE CHECKBOXES --
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.headless_checkbox.setToolTip("Run browser in headless mode")

        self.post_discord_checkbox = QCheckBox("Post to Discord")
        self.post_discord_checkbox.setToolTip("Send episode summaries to Discord when generated")
        self.post_discord_checkbox.setChecked(True)

        self.reverse_order_checkbox = QCheckBox("Reverse Order")
        self.reverse_order_checkbox.setToolTip("Process chats in reverse order")

        # -- LAYOUT FOR CHECKBOXES --
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.headless_checkbox)
        checkbox_layout.addWidget(self.post_discord_checkbox)
        checkbox_layout.addWidget(self.reverse_order_checkbox)
        controls_layout.addLayout(checkbox_layout)

        # -- MODEL DROPDOWN --
        form_layout = QFormLayout()
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["gpt-4o", "gpt-4o-mini", "gpt-4"])
        form_layout.addRow("Model:", self.model_dropdown)
        controls_layout.addLayout(form_layout)

        # -- GENERATE BUTTON --
        self.generate_button = QPushButton("Generate Episodes")
        controls_layout.addWidget(self.generate_button)

        # -- CANCEL BUTTON --
        self.cancel_button = QPushButton("Cancel Generation")
        self.cancel_button.setEnabled(False)
        controls_layout.addWidget(self.cancel_button)

        # -- CONTEXT CONTROLS --
        context_layout = self._setup_context_controls()
        controls_layout.addLayout(context_layout)

        # -- PROCESS ALL CHATS CHECKBOX --
        self.process_all_chats_checkbox = QCheckBox("Process All Chats")
        self.process_all_chats_checkbox.setToolTip("Process all available chats instead of the selected one")
        controls_layout.addWidget(self.process_all_chats_checkbox)

        # -- PROMPT TEXT --
        self.prompt_text_edit = QTextEdit()
        self.prompt_text_edit.setPlaceholderText("Enter your prompt here...")
        self.prompt_text_edit.setMaximumHeight(100)
        controls_layout.addWidget(QLabel("Prompt:"))
        controls_layout.addWidget(self.prompt_text_edit)

        controls_group.setLayout(controls_layout)
        return controls_group

    def _setup_context_controls(self):
        context_layout = QVBoxLayout()
        context_layout.setContentsMargins(0, 10, 0, 0)

        self.send_context_btn = QPushButton("Send Context to ChatGPT")
        context_layout.addWidget(self.send_context_btn)

        # -- AUTO UPDATE --
        auto_update_layout = QHBoxLayout()
        self.auto_update_checkbox = QCheckBox("Schedule Auto-Updates")
        self.auto_update_checkbox.setToolTip("Automatically update context at set intervals")
        self.update_interval_combo = QComboBox()
        self.update_interval_combo.addItems(["1 day", "3 days", "7 days", "14 days", "30 days"])
        self.update_interval_combo.setCurrentIndex(2)
        auto_update_layout.addWidget(self.auto_update_checkbox)
        auto_update_layout.addWidget(self.update_interval_combo)
        context_layout.addLayout(auto_update_layout)

        # -- TARGET CHAT --
        target_chat_layout = QHBoxLayout()
        target_chat_layout.addWidget(QLabel("Target Chat:"))
        self.target_chat_input = QComboBox()
        self.target_chat_input.setEditable(True)
        self.target_chat_input.setToolTip("Enter a specific chat name or leave empty to auto-select")
        target_chat_layout.addWidget(self.target_chat_input)
        context_layout.addLayout(target_chat_layout)

        self.save_schedule_btn = QPushButton("Save Schedule")
        context_layout.addWidget(self.save_schedule_btn)

        return context_layout

    def _setup_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._setup_content_tab(), "Content")
        self.tab_widget.addTab(self._setup_context_tab(), "Context")
        self.tab_widget.addTab(self._setup_log_tab(), "Log")
        self.tab_widget.addTab(self._setup_template_tab(), "Templates")

        right_layout.addWidget(self.tab_widget)
        return right_widget

    def _setup_content_tab(self):
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)

        self.episode_content = QTextEdit()
        self.episode_content.setReadOnly(True)
        content_layout.addWidget(self.episode_content)

        share_layout = QHBoxLayout()
        self.share_discord_btn = QPushButton("Share to Discord")
        share_layout.addWidget(self.share_discord_btn)
        content_layout.addLayout(share_layout)

        return content_tab

    def _setup_context_tab(self):
        context_tab = QWidget()
        context_layout = QVBoxLayout(context_tab)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by Theme:")
        self.context_filter_input = QLineEdit()
        self.context_filter_input.setPlaceholderText("Enter theme or keyword")
        self.context_filter_input.textChanged.connect(self.refresh_context_memory)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.context_filter_input)
        context_layout.addLayout(filter_layout)

        self.context_tree = QTreeWidget()
        self.context_tree.setHeaderLabels(["Property", "Value"])
        self.context_tree.setColumnWidth(0, 200)
        context_layout.addWidget(self.context_tree)

        self.refresh_context_btn = QPushButton("Refresh Context Memory")
        context_layout.addWidget(self.refresh_context_btn)

        return context_tab

    def _setup_log_tab(self):
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        log_layout.addWidget(self.output_display)

        return log_tab

    def _setup_template_tab(self):
        template_widget = QWidget()
        layout = QVBoxLayout(template_widget)

        template_group = QGroupBox("Template Selection")
        template_layout = QFormLayout()
        self.template_dropdown = QComboBox()
        self.template_dropdown.currentTextChanged.connect(self._on_template_selected)
        template_layout.addRow("Active Template:", self.template_dropdown)
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        preview_group = QGroupBox("Template Preview")
        preview_layout = QVBoxLayout()
        self.template_preview = QPlainTextEdit()
        self.template_preview.setReadOnly(True)
        preview_layout.addWidget(self.template_preview)
        self.preview_button = QPushButton("Preview Template")
        self.preview_button.clicked.connect(self.render_dreamscape_template)
        preview_layout.addWidget(self.preview_button)

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

    # ------------------------------------------------------------
    # EVENT HANDLERS
    # ------------------------------------------------------------
    def on_episode_selected(self, current, previous):
        """Handle episode selection change and update content display."""
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.error("UI Manager is not initialized - cannot update episode content.")
            return
            
        try:
            self.ui_manager.update_episode_content(self.episode_content, current)
        except Exception as e:
            self.logger.error(f"Error updating episode content: {str(e)}")

    def share_to_discord(self):
        """Share the current episode content to Discord via UIManager."""
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.error("UI Manager is not initialized - cannot share to Discord.")
            QMessageBox.warning(self, "Error", "UI manager is not available. Cannot share to Discord.")
            return
            
        if not hasattr(self, 'discord_manager') or self.discord_manager is None:
            self.logger.error("Discord Manager is not initialized - cannot share to Discord.")
            QMessageBox.warning(self, "Error", "Discord manager is not available. Cannot share to Discord.")
            return
            
        try:
            self.ui_manager.share_to_discord(self.episode_content, self.discord_manager)
        except Exception as e:
            self.logger.error(f"Error sharing to Discord: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to share to Discord: {str(e)}")

    def _on_template_selected(self, template_name):
        if not template_name:
            return
        
        # Ensure context_manager is initialized before using it
        if not hasattr(self, 'context_manager') or self.context_manager is None:
            self.logger.warning("_on_template_selected called before context_manager was initialized. Skipping.")
            return
        
        # Ensure ui_manager is also initialized
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.warning("_on_template_selected called before ui_manager was initialized. Skipping.")
            return
        
        context = self.context_manager.get_preview_context()
        self.ui_manager.render_template_preview(template_name, self.template_preview, context)

    def _validate_template_context(self):
        """Handle template context validation trigger by calling UIManager."""
        if hasattr(self, 'ui_manager') and self.ui_manager:
            # Pass the context_manager instance
            if hasattr(self, 'context_manager'):
                self.ui_manager.validate_and_display_template_status(self.context_manager)
            else:
                self.logger.error("ContextManager not available to pass for validation.")
                if hasattr(self.parent, 'missing_vars_label'): # Direct update as fallback
                    self.missing_vars_label.setText('Context Mgr Err')
                    self.missing_vars_label.setStyleSheet('color: red')
        else:
            self.logger.error("UIManager not available for template validation.")
            if hasattr(self.parent, 'missing_vars_label'): # Direct update as fallback
                 self.missing_vars_label.setText('UI Mgr Err')
                 self.missing_vars_label.setStyleSheet('color: red')

    def _save_rendered_output(self, format='txt'):
        self.ui_manager.save_rendered_output(format)

    # ------------------------------------------------------------
    # DATA & STATE MANAGEMENT
    # ------------------------------------------------------------
    def refresh_episode_list(self, reverse_order=False):
        """Refresh the episode list using the ui_manager."""
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.error("UI Manager is not initialized - cannot refresh episode list.")
            
            # Fallback implementation in case UI Manager is not available
            if hasattr(self, 'episode_list') and self.episode_list:
                self.logger.info("Using fallback episode list refresh implementation...")
                try:
                    import os
                    
                    # Simple fallback for the most essential functionality
                    output_dir = getattr(self, 'output_dir', os.path.join(os.getcwd(), "outputs", "dreamscape"))
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                        return
                    
                    self.episode_list.clear()
                    for filename in sorted(os.listdir(output_dir), reverse=reverse_order):
                        if filename.endswith(".txt") and filename != "dreamscape_context.json":
                            self.episode_list.addItem(filename.replace('_', ' ').replace('.txt', ''))
                            
                    self.logger.info(f"Fallback episode list refresh completed for directory: {output_dir}")
                except Exception as e:
                    self.logger.error(f"Error in fallback episode list refresh: {str(e)}")
            return
            
        # Normal operation with UIManager
        self.ui_manager.refresh_episode_list(reverse_order)

    def refresh_context_memory(self):
        """Refresh context memory display via ContextManager."""
        # Ensure context_manager is initialized before using it
        if not hasattr(self, 'context_manager') or self.context_manager is None:
            self.logger.warning("refresh_context_memory called before context_manager was initialized. Skipping.")
            return
        
        filter_text = ""
        if hasattr(self, 'context_filter_input') and self.context_filter_input:
            filter_text = self.context_filter_input.text()
        
        # Ensure context_tree is also initialized
        if not hasattr(self, 'context_tree') or self.context_tree is None:
            self.logger.warning("refresh_context_memory called before context_tree was initialized. Skipping.")
            return
        
        self.context_manager.refresh_context_display(self.context_tree, filter_text)

    def log_output(self, message: str):
        """Log a message in the UI log display and via the central logger."""
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.log_output(self.output_display, message)
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            if self.output_display:
                self.output_display.append(formatted_message)
            self.logger.info(message)

    def render_dreamscape_template(self):
        """Render the selected template with current context data."""
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.error("UI Manager is not initialized - cannot render template.")
            return
            
        selected_template = self.template_dropdown.currentText()
        if not selected_template:
            return
        context = self.context_manager.get_preview_context()
        self.ui_manager.render_template_preview(selected_template, self.template_preview, context)

    # ------------------------------------------------------------
    # MAIN FUNCTIONALITY
    # ------------------------------------------------------------
    @asyncSlot()
    async def on_generate_clicked(self):
        """Asynchronously handle the generate button click."""
        try:
            self.generate_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.log_output("Starting episode generation...")
            
            # Check episode_generator before proceeding
            if not hasattr(self, 'episode_generator') or self.episode_generator is None:
                self.logger.error("Episode generator is not initialized")
                QMessageBox.critical(self, "Error", "Episode generator is not available")
                return
            
            await self.generate_dreamscape_episodes()
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        finally:
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

    def on_cancel_clicked(self):
        """Handle the cancel button click."""
        try:
            if hasattr(self, 'episode_generator') and self.episode_generator:
                self.episode_generator.cancel_generation()
                self.log_output("Generation cancelled by user")
                self.cancel_button.setEnabled(False)
                self.generate_button.setEnabled(True)
            else:
                self.logger.warning("Episode generator not available for cancellation")
        except Exception as e:
            self.logger.error(f"Error cancelling generation: {str(e)}")

    async def generate_dreamscape_episodes(self):
        """Core method to generate episodes, delegating parameter gathering and execution."""
        try:
            self.log_output("Preparing episode generation...")
            
            # Validate required components
            if not hasattr(self, 'ui_manager') or self.ui_manager is None:
                self.logger.error("UI Manager is not initialized")
                QMessageBox.critical(self, "Error", "UI manager is not available")
                return
                
            if not hasattr(self, 'episode_generator') or self.episode_generator is None:
                self.logger.error("Episode generator is not initialized")
                QMessageBox.critical(self, "Error", "Episode generator is not available")
                return
            
            if not hasattr(self, 'chat_manager') or self.chat_manager is None:
                self.logger.error("Chat manager is not initialized")
                QMessageBox.critical(self, "Error", "Chat manager is not available")
                return
            
            # Get generation parameters from UIManager
            try:
                params = self.ui_manager.get_generation_parameters()
                self.log_output(f"Parameters: model={params.get('model')}, process_all={params.get('process_all')}, reverse={params.get('reverse_order')}")
                
                # Basic validation on retrieved parameters
                if not params.get("prompt_text"):
                    self.log_output("Warning: Using default prompt as no prompt text was provided")
                
                if not params.get("process_all") and not params.get("chat_url"):
                    self.log_output("No chat selected. Attempting to populate chat list...")
                    # Attempt to populate and re-get parameters if successful
                    count = await asyncio.to_thread(self.ui_manager.populate_chat_dropdown, self.chat_manager) # Assume populate_chat_dropdown exists
                    if count > 0:
                        params = self.ui_manager.get_generation_parameters() # Re-fetch params
                        self.log_output(f"Selected chat: {params.get('chat_url')}")
                        if not params.get("chat_url"):
                            self.log_output("Still no chat selected after populating.")
                            QMessageBox.warning(self, "Warning", "No chat selected after refreshing list.")
                            return
                    else:
                        self.log_output("No chats available")
                        QMessageBox.warning(self, "Warning", "No chat selected and no chats available")
                        return
            except Exception as e:
                self.logger.error(f"Error retrieving parameters from UIManager: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to retrieve generation parameters: {str(e)}")
                return
            
            self.log_output(f"Generating episode(s) using {params.get('model')}...")
            
            # Call the episode_generator with parameters
            try:
                success = await self.episode_generator.generate_episodes(
                    prompt_text=params.get("prompt_text", ""),
                    chat_url=params.get("chat_url"),
                    model=params.get("model", "gpt-4o"),
                    process_all=params.get("process_all", False),
                    reverse_order=params.get("reverse_order", False)
                )
                
                if success:
                    self.log_output("Episode generation completed successfully!")
                    self.log_output("Refreshing episode list...")
                    self.refresh_episode_list()
                else:
                    self.log_output("Episode generation did not complete successfully")
            except Exception as e:
                self.logger.error(f"Error in episode_generator.generate_episodes: {str(e)}", exc_info=True)
                self.log_output(f"Generation error: {str(e)}")
                # Let the outer handler show the message box
                raise

        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
            self.log_output(f"Fatal error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def send_context_to_chatgpt(self):
        """Send the current context to ChatGPT via ContextManager."""
        if self.target_chat_input:
            chat_url = self.target_chat_input.currentText()
            self.context_manager.send_context_to_chat(chat_url)

    def save_context_schedule(self):
        """Save context update schedule and reset timers."""
        if not self.auto_update_checkbox:
            return
            
        # Check if context_manager is available
        if not hasattr(self, 'context_manager') or self.context_manager is None:
            self.logger.error("Context Manager is not initialized - cannot save context schedule.")
            QMessageBox.warning(self, "Error", "Context manager is not available. Cannot save schedule.")
            return
            
        enabled = self.auto_update_checkbox.isChecked()
        interval = self.update_interval_combo.currentText() if self.update_interval_combo else "7 days"
        
        try:
            success = self.context_manager.save_context_schedule(enabled, interval)
            if success:
                self._setup_timers()
                QMessageBox.information(self, "Schedule Saved", "Context update schedule saved successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to save context schedule.")
        except Exception as e:
            self.logger.error(f"Error saving context schedule: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save schedule: {str(e)}")

    def cleanup(self):
        """
        Clean up resources used by this tab.
        Called when the application is shutting down.
        """
        self.logger.info("Cleaning up DreamscapeGenerationTab resources...")
        
        try:
            # Cancel any ongoing generation
            if hasattr(self, 'episode_generator') and self.episode_generator:
                self.logger.info("Cancelling any ongoing episode generation...")
                self.episode_generator.cancel_generation()
            
            # Stop any timers
            if hasattr(self, 'ui_manager') and self.ui_manager:
                self.logger.info("Stopping UI timers...")
                self.ui_manager.stop_timers()
            
            # Clean up resources in component managers
            component_managers = [
                ('episode_generator', 'shutdown'),
                ('template_manager', 'cleanup'),
                ('context_manager', 'cleanup'),
                ('ui_manager', 'cleanup')
            ]
            
            for manager_name, method_name in component_managers:
                if hasattr(self, manager_name):
                    manager = getattr(self, manager_name)
                    if manager and hasattr(manager, method_name):
                        try:
                            self.logger.info(f"Cleaning up {manager_name}...")
                            method = getattr(manager, method_name)
                            method()
                        except Exception as e:
                            self.logger.error(f"Error cleaning up {manager_name}: {str(e)}")
            
            # Clean up core services
            core_services = [
                ('cycle_service', 'shutdown'),
                ('prompt_handler', 'cleanup'),
                ('discord_processor', 'cleanup'),
                ('task_orchestrator', 'shutdown'),
                ('dreamscape_generator', 'shutdown')
            ]
            
            for service_name, method_name in core_services:
                if hasattr(self, service_name):
                    service = getattr(self, service_name)
                    if service and hasattr(service, method_name):
                        try:
                            self.logger.info(f"Cleaning up {service_name}...")
                            method = getattr(service, method_name)
                            method()
                        except Exception as e:
                            self.logger.error(f"Error cleaning up {service_name}: {str(e)}")
            
            self.logger.info("DreamscapeGenerationTab cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during DreamscapeGenerationTab cleanup: {str(e)}")

    def _connect_ui_signals(self):
        """Connect signals for all UI elements after services are initialized."""
        self.logger.info("Connecting DreamscapeGenerationTab UI signals...")
        try:
            # Left Panel Connections
            if self.episode_list: self.episode_list.currentItemChanged.connect(self.on_episode_selected)
            if hasattr(self, 'refresh_episodes_btn') and self.refresh_episodes_btn: self.refresh_episodes_btn.clicked.connect(self.refresh_episode_list)
            if self.generate_button: self.generate_button.clicked.connect(self.on_generate_clicked)
            if self.cancel_button: self.cancel_button.clicked.connect(self.on_cancel_clicked)
            if hasattr(self, 'send_context_btn') and self.send_context_btn: self.send_context_btn.clicked.connect(self.send_context_to_chatgpt)
            if hasattr(self, 'save_schedule_btn') and self.save_schedule_btn: self.save_schedule_btn.clicked.connect(self.save_context_schedule)

            # Right Panel Connections (Tabs)
            if hasattr(self, 'share_discord_btn') and self.share_discord_btn: self.share_discord_btn.clicked.connect(self.share_to_discord)
            if self.context_filter_input: self.context_filter_input.textChanged.connect(self.refresh_context_memory)
            if hasattr(self, 'refresh_context_btn') and self.refresh_context_btn: self.refresh_context_btn.clicked.connect(self.refresh_context_memory)
            if self.template_dropdown: self.template_dropdown.currentTextChanged.connect(self._on_template_selected)
            if self.preview_button: self.preview_button.clicked.connect(self.render_dreamscape_template)
            if self.validate_btn: self.validate_btn.clicked.connect(self._validate_template_context)
            if self.save_txt_btn: self.save_txt_btn.clicked.connect(lambda: self._save_rendered_output('txt'))
            if self.save_md_btn: self.save_md_btn.clicked.connect(lambda: self._save_rendered_output('md'))

            self.logger.info("✅ DreamscapeGenerationTab UI signals connected successfully.")
        except Exception as e:
            self.logger.error(f"❌ Error connecting DreamscapeGenerationTab UI signals: {str(e)}", exc_info=True)
