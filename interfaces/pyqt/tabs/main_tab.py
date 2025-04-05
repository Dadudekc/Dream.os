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
    QMessageBox,
    QGridLayout,
    QGroupBox,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer

# Import necessary services
from core.config.config_manager import ConfigManager
# Assuming system_loader acts as service_manager
from core.system_loader import DreamscapeSystemLoader 

logger = logging.getLogger(__name__)

class MainTab(QWidget):
    """Main tab for the Dream.OS interface."""
    
    # Signals
    log_updated = pyqtSignal(str)
    
    def __init__(self, config_manager: ConfigManager, service_manager: DreamscapeSystemLoader, logger: logging.Logger, parent=None):
        """Initialize the main tab."""
        super().__init__(parent)
        
        # Store dependencies
        self.config_manager = config_manager
        self.service_manager = service_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Retrieve services from the service_manager (system_loader)
        self.services = service_manager.get_all_services() if service_manager and hasattr(service_manager, 'get_all_services') else {}
        
        # Placeholder for system status data
        self.system_status = {
            "Service Status": "Initializing...",
            "Task Queue Length": 0,
            "Last Event": "None",
            "CPU Usage": "0%",
            "Memory Usage": "0 MB",
            "Active Threads": 1
        }
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.log_updated.connect(self._append_log)
        
        # Set up log handler
        self.log_handler = self.setup_log_handler()
        
        # Start status updates
        self._start_status_updates()
        
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
        main_layout = QVBoxLayout(self)
        
        # Add header
        header = QLabel("Dream.OS Control Center")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # --- Status Overview Group ---
        status_group = QGroupBox("System Status Overview")
        status_layout = QGridLayout(status_group)

        self.status_labels = {}
        row = 0
        for key, value in self.system_status.items():
            key_label = QLabel(f"{key}:")
            value_label = QLabel(str(value))
            self.status_labels[key] = value_label # Store reference to update later
            status_layout.addWidget(key_label, row, 0)
            status_layout.addWidget(value_label, row, 1)
            row += 1

        main_layout.addWidget(status_group)
        
        # --- Control Panel Group ---
        control_group = QGroupBox("Control Panel")
        control_layout = QVBoxLayout(control_group)
        
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
        
        # --- Task Queue Processing --- 
        self.process_queue_button = QPushButton("Process Task Queue")
        self.process_queue_button.clicked.connect(self._process_task_queue)
        button_layout.addWidget(self.process_queue_button)
        
        control_layout.addLayout(button_layout)
        main_layout.addWidget(control_group)
        
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
        main_layout.addWidget(scroll_area)
        
        # Initial status update
        self.refresh_status()
        
    def setup_log_handler(self):
        """Set up custom log handler to capture logs."""
        class QTextEditHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
                self.widget_ref = widget  # Store a reference
                
            def emit(self, record):
                if self.widget_ref:  # Check if reference is still valid
                    try:
                        msg = self.format(record)
                        self.widget.log_updated.emit(msg)
                    except RuntimeError:
                        # Widget has been deleted, remove the handler
                        self.widget_ref = None
                        root_logger = logging.getLogger()
                        if self in root_logger.handlers:
                            root_logger.removeHandler(self)
                
        # Create and add handler
        handler = QTextEditHandler(self)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(handler)
        return handler
        
    def closeEvent(self, event):
        """Handle widget close event to clean up resources."""
        # Remove the log handler when the widget is being destroyed
        root_logger = logging.getLogger()
        if self.log_handler in root_logger.handlers:
            root_logger.removeHandler(self.log_handler)
        # Call the parent's closeEvent
        super().closeEvent(event)
        
    def refresh_status(self) -> None:
        """Refresh the service status display."""
        try:
            # Update system status
            self._update_status_display()
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

    def _process_task_queue(self):
        """Handle the button click to process the task queue."""
        self.logger.info("'Process Task Queue' button clicked.")
        task_queue_service = self.services.get('task_queue_service')
        
        if task_queue_service:
            try:
                self.process_queue_button.setEnabled(False)
                self.process_queue_button.setText("Processing...")
                QApplication.processEvents() # Allow UI to update
                
                self.logger.info("Calling task_queue_service.process_queue()...")
                # This might be blocking; consider running in a thread for complex tasks
                result = task_queue_service.process_queue()
                self.logger.info(f"Task queue processing completed. Result: {result}") # Log result if any
                
                # Update status immediately after processing (e.g., queue length)
                self.refresh_status()
                
            except Exception as e:
                self.logger.error(f"Error during task queue processing: {e}", exc_info=True)
            finally:
                # Re-enable button
                self.process_queue_button.setEnabled(True)
                self.process_queue_button.setText("Process Task Queue")
        else:
            self.logger.error("TaskQueueService not found in services. Cannot process queue.")

    def _start_status_updates(self):
        """Start a timer to periodically update system status."""
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_display)
        self.status_timer.start(5000) # Update every 5 seconds
        self._update_status_display() # Initial update

    def _update_status_display(self):
        """Fetch latest status and update the labels."""
        # Fetch real data - Placeholder logic
        # In a real scenario, query relevant services
        try:
            # Example: Query TaskQueueService if available
            task_queue_service = self.services.get('task_queue_service')
            if task_queue_service and hasattr(task_queue_service, 'get_queue_length'):
                self.system_status["Task Queue Length"] = task_queue_service.get_queue_length()
            else:
                self.system_status["Task Queue Length"] = "N/A"
                
            self.system_status["CPU Usage"] = "N/A"
            self.system_status["Memory Usage"] = "N/A"
            self.system_status["Active Threads"] = "N/A"
                
            # General service status check
            # Check specifically required services for a more accurate status
            required_operational = ['system_loader', 'prompt_manager', 'chat_manager'] # Example critical set
            operational = True
            for service_name in required_operational:
                service = self.services.get(service_name)
                if not service or hasattr(service, '__class__') and service.__class__.__name__.startswith('Mock'):
                    operational = False
                    break
            
            self.system_status["Service Status"] = "OK" if operational else "Degraded"

            # Update labels
            for key, value_label in self.status_labels.items():
                if key in self.system_status:
                    value_label.setText(str(self.system_status[key]))
        except Exception as e:
            self.logger.error(f"Error updating status display: {e}")
            if "Service Status" in self.status_labels:
                self.status_labels["Service Status"].setText("Error Updating") 