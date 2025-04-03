"""
UI setup and layout management for Dream.OS main window.
"""

import logging
from typing import Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLabel, QTabWidget
)

from interfaces.pyqt.tabs.MainTabs import MainTabs


class WindowUI:
    """Manages UI setup and layout for the Dream.OS main window."""
    
    def __init__(self, parent_widget: QWidget, logger: logging.Logger):
        """
        Initialize the window UI manager.
        
        Args:
            parent_widget: Parent widget to attach UI elements to
            logger: Logger instance for UI-related messages
        """
        self.parent = parent_widget
        self.logger = logger
        self.tabs = None
        self.fallback_output = None
        
    def setup_ui(self, services: dict, dispatcher, ui_logic) -> None:
        """
        Set up the user interface components.
        
        Args:
            services: Dictionary of service instances
            dispatcher: Signal dispatcher instance
            ui_logic: UI logic instance
        """
        self.parent.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.parent.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.parent.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Initialize main tabs
        self._setup_tabs(services, dispatcher, ui_logic, layout)
        
        # Add control buttons
        self._setup_buttons(layout)
        
        # Add chat interface
        self._setup_chat_interface(layout)
        
        self.parent.statusBar().showMessage("Ready")
        
    def _setup_tabs(self, services: dict, dispatcher, ui_logic, layout: QVBoxLayout) -> None:
        """Set up the main tab interface."""
        try:
            self.tabs = MainTabs(
                dispatcher=dispatcher,
                ui_logic=ui_logic,
                config_manager=services.get('config_manager'),
                logger=services.get('logger'),
                prompt_manager=services.get('prompt_manager'),
                chat_manager=services.get('chat_manager'),
                memory_manager=services.get('memory_manager'),
                discord_manager=services.get('discord_service'),
                cursor_manager=services.get('cursor_manager'),
                **services.get('extra_dependencies', {})
            )
            layout.addWidget(self.tabs)
            self.logger.info("MainTabs initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MainTabs: {e}")
            self._setup_fallback_tabs(layout, str(e))
            
    def _setup_fallback_tabs(self, layout: QVBoxLayout, error_message: str) -> None:
        """Set up fallback tabs when main tabs fail to initialize."""
        self.tabs = None
        fallback_tabs = QTabWidget()
        layout.addWidget(fallback_tabs)
        fallback_text = QTextEdit()
        fallback_text.setReadOnly(True)
        fallback_text.append("Tab initialization failed. Check logs for details.")
        fallback_text.append(f"Error: {error_message}")
        fallback_tabs.addTab(fallback_text, "Error Info")
        self.fallback_output = fallback_text
        
    def _setup_buttons(self, layout: QVBoxLayout) -> None:
        """Set up control buttons."""
        button_layout = QHBoxLayout()
        
        # OpenAI Login Button
        openai_button = QPushButton("🔓 Check OpenAI Login")
        button_layout.addWidget(openai_button)
        
        # Project Scan Button
        scan_button = QPushButton("Scan Project")
        button_layout.addWidget(scan_button)
        
        # Assistant Control Buttons
        start_button = QPushButton("Start Assistant")
        button_layout.addWidget(start_button)
        
        stop_button = QPushButton("Stop Assistant")
        stop_button.setEnabled(False)
        button_layout.addWidget(stop_button)
        
        layout.addLayout(button_layout)
        
        # Store buttons as attributes
        self.openai_login_button = openai_button
        self.scan_button = scan_button
        self.start_button = start_button
        self.stop_button = stop_button
        
    def _setup_chat_interface(self, layout: QVBoxLayout) -> None:
        """Set up the chat interface."""
        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("Send")
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
    def show_startup_warnings(self, warnings: List[str]) -> None:
        """Display startup warnings in the UI."""
        if warnings:
            warning_label = QLabel("⚠️ Startup Warnings Present")
            warning_label.setStyleSheet("color: orange;")
            self.parent.layout().insertWidget(0, warning_label)
            
    def get_tabs(self) -> Optional[MainTabs]:
        """Get the main tabs instance."""
        return self.tabs 