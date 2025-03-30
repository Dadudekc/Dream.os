import os
import logging
from datetime import datetime
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter, QListWidget,
    QPushButton, QLabel, QCheckBox, QComboBox, QTextEdit, QPlainTextEdit,
    QTreeWidget, QGroupBox, QLineEdit, QFileDialog, QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt
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
    """

    def __init__(self, dispatcher=None, prompt_manager=None, chat_manager=None, response_handler=None,
                 memory_manager=None, discord_manager=None, ui_logic=None, config_manager=None, logger=None):
        super().__init__()

        # -------------------------
        # 1) INIT LOGGER & SERVICES
        # -------------------------
        self.logger = logger or logging.getLogger(__name__)

        # Initialize UI elements to None
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

        # Use ServiceInitializer to inject and initialize required services
        self.service_initializer = ServiceInitializer(self, config_manager, self.logger)
        services = self.service_initializer.initialize_services(
            prompt_manager, chat_manager, response_handler,
            memory_manager, discord_manager, ui_logic
        )
        self._store_service_references(services)

        # Optionally store prompt_manager from services (if provided)
        self.prompt_manager = services.get("prompt_manager", None)
        if not self.prompt_manager:
            self.logger.warning("No prompt_manager service provided.")

        # -------------------------
        # 2) SET UP THE UI
        # -------------------------
        self.init_ui()

        # -------------------------
        # 3) TIMERS & DATA LOAD
        # -------------------------
        # Ensure the UI is built, then set up timers
        self._setup_timers()
        self._load_initial_data()

    # ------------------------------------------------------------
    # Store references to all initialized core services/components
    # ------------------------------------------------------------
    def _store_service_references(self, services):
        core_services = services['core_services']
        component_managers = services['component_managers']

        self.cycle_service = core_services.get('cycle_service')
        self.prompt_handler = core_services.get('prompt_handler')
        self.discord_processor = core_services.get('discord_processor')
        self.task_orchestrator = core_services.get('task_orchestrator')
        self.dreamscape_generator = core_services.get('dreamscape_generator')

        self.template_manager = component_managers.get('template_manager')
        self.episode_generator = component_managers.get('episode_generator')
        self.context_manager = component_managers.get('context_manager')
        self.ui_manager = component_managers.get('ui_manager')

        self.output_dir = services.get('output_dir')

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
        self.episode_list.currentItemChanged.connect(self.on_episode_selected)
        episodes_layout.addWidget(self.episode_list)

        refresh_btn = QPushButton("Refresh Episodes")
        refresh_btn.clicked.connect(self.refresh_episode_list)
        episodes_layout.addWidget(refresh_btn)

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
        self.generate_button.clicked.connect(self.on_generate_clicked)
        controls_layout.addWidget(self.generate_button)

        # -- CANCEL BUTTON --
        self.cancel_button = QPushButton("Cancel Generation")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
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

        send_context_btn = QPushButton("Send Context to ChatGPT")
        send_context_btn.setToolTip("Send the current context to ChatGPT")
        send_context_btn.clicked.connect(self.send_context_to_chatgpt)
        context_layout.addWidget(send_context_btn)

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

        save_schedule_btn = QPushButton("Save Schedule")
        save_schedule_btn.clicked.connect(self.save_context_schedule)
        context_layout.addWidget(save_schedule_btn)

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
        share_discord_btn = QPushButton("Share to Discord")
        share_discord_btn.clicked.connect(self.share_to_discord)
        share_layout.addWidget(share_discord_btn)
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

        refresh_context_btn = QPushButton("Refresh Context Memory")
        refresh_context_btn.clicked.connect(self.refresh_context_memory)
        context_layout.addWidget(refresh_context_btn)

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
    # Timers & Data Load
    # ------------------------------------------------------------
    def _setup_timers(self):
        """Delegate setting up auto-update timers to UIManager."""
        # Guard if UI not fully ready
        if not self.auto_update_checkbox:
            self.logger.warning("auto_update_checkbox undefined at _setup_timers. Skipping timer setup.")
            return

        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.setup_auto_update_timer(self.auto_update_checkbox, self.update_interval_combo)

    def _load_initial_data(self):
        """Load initial templates, episode list, and context memory."""
        try:
            # If ui_manager is available, use it to load templates; otherwise, fallback
            if hasattr(self, 'ui_manager') and self.ui_manager and hasattr(self, 'template_dropdown'):
                if self.template_manager is not None:
                    self.ui_manager.load_templates(self.template_dropdown)
                else:
                    self.logger.warning("No template_manager available; using fallback directory.")
                    default_template_dir = os.path.join(os.getcwd(), "templates", "dreamscape_templates")
                    if os.path.isdir(default_template_dir):
                        templates = [f for f in os.listdir(default_template_dir) if f.endswith('.j2')]
                        self.template_dropdown.clear()
                        self.template_dropdown.addItems(templates)
                    else:
                        self.logger.error(f"Default template directory not found: {default_template_dir}")

            self.refresh_episode_list()
            self.refresh_context_memory()

            if self.target_chat_input:
                self.populate_chat_list()

            self.log_output("🚀 Initial data loaded")
        except Exception as e:
            self.log_output(f"⚠️ Warning: Error loading initial data: {str(e)}")

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
        context = self.context_manager.get_preview_context()
        self.ui_manager.render_template_preview(template_name, self.template_preview, context)

    def _validate_template_context(self):
        # Guard against template_manager being None or missing active_template attribute
        if not self.template_manager or not hasattr(self.template_manager, 'active_template'):
            self.missing_vars_label.setText('Template Manager unavailable')
            self.missing_vars_label.setStyleSheet('color: red')
            return

        if not self.template_manager.active_template:
            self.missing_vars_label.setText("No active template selected")
            self.missing_vars_label.setStyleSheet("color: red")
            return

        context = self.context_manager.get_preview_context()
        missing = self.template_manager.validate_context(self.template_manager.active_template, context)
        if missing:
            self.missing_vars_label.setText(f"Missing variables: {', '.join(missing)}")
            self.missing_vars_label.setStyleSheet("color: red")
        else:
            self.missing_vars_label.setText("✓ All variables present")
            self.missing_vars_label.setStyleSheet("color: green")

    def _save_rendered_output(self, format='txt'):
        self.ui_manager.save_rendered_output(format)

    # ------------------------------------------------------------
    # DATA & STATE MANAGEMENT
    # ------------------------------------------------------------
    def refresh_episode_list(self, reverse_order=False):
        """Refresh the episode list using the ui_manager."""
        if not hasattr(self, 'ui_manager') or self.ui_manager is None:
            self.logger.error("UI Manager is not initialized - cannot refresh episode list.")
            return
        self.ui_manager.refresh_episode_list(reverse_order)

    def refresh_context_memory(self):
        """Refresh context memory display via ContextManager."""
        filter_text = ""
        if hasattr(self, 'context_filter_input') and self.context_filter_input:
            filter_text = self.context_filter_input.text()
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
            await self.generate_dreamscape_episodes()
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        finally:
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

    def on_cancel_clicked(self):
        """Handle the cancel button click."""
        if self.episode_generator:
            self.episode_generator.cancel_generation()
            self.log_output("Generation cancelled by user")
            self.cancel_button.setEnabled(False)
            self.generate_button.setEnabled(True)

    async def generate_dreamscape_episodes(self):
        """Core method to generate episodes, referencing the episode_generator in async context."""
        try:
            process_all = self.process_all_chats_checkbox.isChecked() if self.process_all_chats_checkbox else False
            prompt_text = self.prompt_text_edit.toPlainText() if self.prompt_text_edit else ""
            chat_url = None if process_all else self.target_chat_input.currentText() if self.target_chat_input else None
            model = self.model_dropdown.currentText() if self.model_dropdown else "gpt-4"
            reverse_order = self.reverse_order_checkbox.isChecked() if self.reverse_order_checkbox else False

            if not process_all and not chat_url:
                self.populate_chat_list()
                if self.target_chat_input:
                    chat_url = self.target_chat_input.currentText()

            success = await self.episode_generator.generate_episodes(
                prompt_text=prompt_text,
                chat_url=chat_url,
                model=model,
                process_all=process_all,
                reverse_order=reverse_order
            )

            if success:
                self.refresh_episode_list()

        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
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

    def populate_chat_list(self):
        """Populate the target chat dropdown with available chats."""
        try:
            if not self.target_chat_input or not self.chat_manager:
                return 0
            self.target_chat_input.clear()
            chat_list = self.chat_manager.get_all_chat_titles()
            self.logger.info(f"Found {len(chat_list)} chats")
            for chat in chat_list:
                title = chat.get("title", "Untitled")
                url = chat.get("link", "")
                self.target_chat_input.addItem(title, userData=url)
            return len(chat_list)
        except Exception as e:
            self.logger.error(f"Error populating chat list: {str(e)}")
            return 0

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
