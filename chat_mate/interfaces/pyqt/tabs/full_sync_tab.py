from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                             QTextEdit, QProgressBar, QLabel, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
import asyncio
import logging
from typing import Dict, List

class FullSyncTab(QWidget):
    """
    Tab interface for running and monitoring full sync operations.
    Provides visual feedback and control over the sync process.
    """
    sync_completed = pyqtSignal(dict)  # Emits results when sync completes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self.sync_completed.connect(self._on_sync_completed)

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        # Status section
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)

        # Control buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Full Sync")
        self.run_button.clicked.connect(self.run_full_sync)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_sync)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)

    def log(self, msg: str, level: str = "info"):
        """Add a log message to the output area."""
        color_map = {
            "error": "red",
            "warning": "orange",
            "success": "green",
            "info": "black"
        }
        color = color_map.get(level, "black")
        self.output.append(f'<span style="color: {color}">{msg}</span>')

    async def run_full_sync(self):
        """Run the full sync process."""
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Syncing...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        try:
            self.log("🚀 Starting full sync process...")
            
            # TODO: Replace with actual sync logic
            await asyncio.sleep(2)  # Simulate work
            
            result = {
                "status": "success",
                "files_processed": 10,
                "errors": [],
                "warnings": []
            }
            
            self.sync_completed.emit(result)
            
        except Exception as e:
            self.log(f"❌ Error during sync: {str(e)}", "error")
            self.sync_completed.emit({"status": "error", "message": str(e)})
        
        finally:
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress_bar.setRange(0, 100)

    def cancel_sync(self):
        """Cancel the current sync operation."""
        self.log("⚠️ Sync cancelled by user", "warning")
        self.status_label.setText("Cancelled")
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def _on_sync_completed(self, result: Dict):
        """Handle sync completion."""
        if result["status"] == "success":
            self.status_label.setText("✅ Sync Complete")
            self.log("✅ Full sync completed successfully!", "success")
            
            if result.get("warnings"):
                for warning in result["warnings"]:
                    self.log(f"⚠️ {warning}", "warning")
        else:
            self.status_label.setText("❌ Sync Failed")
            self.log(f"❌ Sync failed: {result.get('message', 'Unknown error')}", "error")
