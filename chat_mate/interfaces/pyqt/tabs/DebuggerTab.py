#!/usr/bin/env python3
"""
DebuggerTab.py

An updated interactive Debugger Tab for the Dreamscape interface.
This tab is designed to be modular and integrates with the signal dispatcher.
It includes additional buttons and logic to connect to the CursorSessionManager,
enabling debug prompts and command execution using the Cursor integration.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import pyqtSlot
import logging

class DebuggerTab(QWidget):
    def __init__(self, dispatcher=None, logger=None, **services):
        """
        Initializes the DebuggerTab.
        
        Args:
            dispatcher: Centralized signal dispatcher.
            logger: Logger instance.
            services: Additional services (e.g. debug_service, fix_service, rollback_service, cursor_manager).
        """
        super().__init__()
        self.dispatcher = dispatcher
        self.logger = logger or logging.getLogger(__name__)
        self.services = services
        
        # Optional: If a cursor manager is provided, initialize it
        self.cursor_manager = self.services.get("cursor_manager")

        self._init_ui()
        self._connect_signals()
        self.logger.info("DebuggerTab initialized.")

    def _init_ui(self):
        """
        Set up the user interface.
        """
        self.setMinimumSize(800, 600)
        self.layout = QVBoxLayout(self)
        
        # Title label
        self.title_label = QLabel("Debugger Tab – Interactive Debugging & Cursor Integration")
        self.layout.addWidget(self.title_label)
        
        # Output display area
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.layout.addWidget(self.output_edit)
        
        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        self.run_debug_btn = QPushButton("Run Debug")
        self.apply_fix_btn = QPushButton("Apply Fix")
        self.rollback_btn = QPushButton("Rollback Fix")
        # New button for Cursor integration
        self.cursor_exec_btn = QPushButton("Execute via Cursor")
        
        self.buttons_layout.addWidget(self.run_debug_btn)
        self.buttons_layout.addWidget(self.apply_fix_btn)
        self.buttons_layout.addWidget(self.rollback_btn)
        self.buttons_layout.addWidget(self.cursor_exec_btn)
        
        self.layout.addLayout(self.buttons_layout)
    
    def _connect_signals(self):
        """
        Connect button clicks and dispatcher signals.
        """
        self.run_debug_btn.clicked.connect(self.on_run_debug)
        self.apply_fix_btn.clicked.connect(self.on_apply_fix)
        self.rollback_btn.clicked.connect(self.on_rollback_fix)
        self.cursor_exec_btn.clicked.connect(self.on_cursor_execute)
        
        # Connect debug output signal if available
        if self.dispatcher and hasattr(self.dispatcher, "debug_output"):
            self.dispatcher.debug_output.connect(self.append_output)

    @pyqtSlot()
    def on_run_debug(self):
        """
        Slot for running a debug session.
        """
        self.append_output("Starting debug session...")
        debug_service = self.services.get("debug_service")
        if debug_service:
            try:
                result = debug_service.run_debug_cycle()
                self.append_output(f"Debug session completed: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_debug_completed(result)
            except Exception as e:
                error_msg = f"Error running debug session: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_debug_error(str(e))
        else:
            self.append_output("Debug service not available.")

    @pyqtSlot()
    def on_apply_fix(self):
        """
        Slot for applying a fix.
        """
        self.append_output("Applying fix...")
        fix_service = self.services.get("fix_service")
        if fix_service:
            try:
                result = fix_service.apply_fix()
                self.append_output(f"Fix applied: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_fix_applied(result)
            except Exception as e:
                error_msg = f"Error applying fix: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_fix_error(str(e))
        else:
            self.append_output("Fix service not available.")

    @pyqtSlot()
    def on_rollback_fix(self):
        """
        Slot for rolling back a fix.
        """
        self.append_output("Rolling back fix...")
        rollback_service = self.services.get("rollback_service")
        if rollback_service:
            try:
                result = rollback_service.rollback_fix()
                self.append_output(f"Rollback successful: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_rollback_completed(result)
            except Exception as e:
                error_msg = f"Error during rollback: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_rollback_error(str(e))
        else:
            self.append_output("Rollback service not available.")

    @pyqtSlot()
    def on_cursor_execute(self):
        """
        Slot to execute a prompt via the Cursor integration.
        Uses the CursorSessionManager to generate code from a debug prompt.
        """
        self.append_output("Executing debug prompt via Cursor...")
        if self.cursor_manager:
            try:
                # Generate a prompt for debugging
                prompt = "## DEBUG PROMPT\nPlease analyze the current error state and generate a suggested fix."
                generated_code = self.cursor_manager.execute_prompt(prompt)
                if generated_code:
                    self.append_output("Cursor generated code:")
                    self.append_output(generated_code)
                    if self.dispatcher:
                        self.dispatcher.emit_cursor_code_generated(generated_code)
                else:
                    self.append_output("Cursor did not generate any code.")
            except Exception as e:
                error_msg = f"Error executing prompt via Cursor: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_cursor_error(str(e))
        else:
            self.append_output("Cursor manager not available. Ensure it is added as a service.")

    @pyqtSlot(str)
    def append_output(self, message: str):
        """
        Append a message to the output text area.
        
        Args:
            message: The message to append.
        """
        self.output_edit.append(message)
        if self.logger:
            self.logger.info(message) 