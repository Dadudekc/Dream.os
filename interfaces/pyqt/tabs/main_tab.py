"""
Main Tab Module

This module provides the main tab implementation for the Dream.OS PyQt interface.
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QScrollArea,
    QFrame,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)

class MainTab(QWidget):
    """Main tab for the Dream.OS interface."""
    
    # Signals
    log_updated = pyqtSignal(str)
    
    def __init__(self, config_manager=None, service_manager=None, logger=None, parent=None):
        """Initialize the main tab."""
        super().__init__(parent)
        
        # Store dependencies
        self.config_manager = config_manager
        self.service_manager = service_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.log_updated.connect(self._append_log)
        
        # Set up log handler
        self.setup_log_handler()
        
    def _append_log(self, message: str) -> None:
        """Append a message to the log view."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_view.append(formatted_message)
        
    def _show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)
        
    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Create main layout
        layout = QVBoxLayout()
        
        # Add header
        header = QLabel("Dream.OS Control Center")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Add status section
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        status_layout = QVBoxLayout(status_frame)
        
        status_header = QLabel("System Status")
        status_header.setStyleSheet("font-size: 18px; font-weight: bold;")
        status_layout.addWidget(status_header)
        
        # Add service status
        self.service_status = QTextEdit()
        self.service_status.setReadOnly(True)
        self.service_status.setMaximumHeight(150)
        status_layout.addWidget(self.service_status)
        
        layout.addWidget(status_frame)
        
        # Add control buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self.refresh_status)
        refresh_button.setMinimumHeight(30)
        button_layout.addWidget(refresh_button)
        
        restart_button = QPushButton("Restart Services")
        restart_button.clicked.connect(self.restart_services)
        restart_button.setMinimumHeight(30)
        button_layout.addWidget(restart_button)
        
        layout.addLayout(button_layout)
        
        # Add scroll area for logs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_header = QLabel("System Logs")
        log_header.setStyleSheet("font-size: 18px; font-weight: bold;")
        log_layout.addWidget(log_header)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        
        # Add log control buttons
        log_button_layout = QHBoxLayout()
        
        clear_logs_button = QPushButton("Clear Logs")
        clear_logs_button.clicked.connect(self.clear_logs)
        log_button_layout.addWidget(clear_logs_button)
        
        log_layout.addLayout(log_button_layout)
        
        scroll_area.setWidget(log_widget)
        layout.addWidget(scroll_area)
        
        # Set the layout
        self.setLayout(layout)
        
        # Initial status update
        self.refresh_status()
        
    def setup_log_handler(self) -> None:
        """Set up custom log handler to capture logs."""
        class QTextEditHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
                
            def emit(self, record):
                msg = self.format(record)
                self.widget.log_updated.emit(msg)
                
        # Create and add handler
        handler = QTextEditHandler(self)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(handler)
        
    def refresh_status(self) -> None:
        """Refresh the service status display."""
        try:
            status_text = []
            
            # Add service manager status if available
            if self.service_manager:
                # --- FIX: Guard against NoneType before calling .items() ---
                services = self.service_manager.get_services() if hasattr(self.service_manager, 'get_services') else {}
                services = services or {} # Ensure services is a dict
                # --- End FIX ---
                for name, service in services.items():
                    # Check if service is a real service or a mock
                    if hasattr(service, 'is_running') and callable(service.is_running):
                        status = "Running" if service.is_running() else "Stopped"
                    elif isinstance(service, MockService):
                        status = "Mocked"
                    else:
                        status = "Unknown State"
                    status_text.append(f"{name}: {status}")
            else:
                status_text.append("Service Manager: Not Available")
                
            # Add config manager status if available
            if self.config_manager:
                config_status = "Loaded" if self.config_manager.is_loaded() else "Not Loaded"
                status_text.append(f"Configuration: {config_status}")
            else:
                status_text.append("Configuration: Not Available")
            
            # Update the status display
            self.service_status.setText("\n".join(status_text))
            self.logger.info("Status refreshed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh status: {e}")
            self._show_error("Status Error", f"Failed to refresh status: {e}")
            
    def restart_services(self) -> None:
        """Restart all services."""
        try:
            if self.service_manager:
                self.service_manager.restart_all()
                self.logger.info("Services restarted successfully")
                self.refresh_status()
            else:
                raise RuntimeError("Service Manager not available")
        except Exception as e:
            self.logger.error(f"Failed to restart services: {e}")
            self._show_error("Service Error", f"Failed to restart services: {e}")
            
    def clear_logs(self) -> None:
        """Clear the log view."""
        self.log_view.clear()
        self.logger.info("Logs cleared") 