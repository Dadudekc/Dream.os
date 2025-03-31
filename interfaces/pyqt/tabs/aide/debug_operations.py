"""
Debug Operations Handler for AIDE

This module contains the DebugOperationsHandler class that manages debug-related
operations including running debug sessions, applying fixes, and integrating with Cursor.
"""

class DebugOperationsHandler:
    def __init__(self, parent, helpers, dispatcher=None, logger=None, 
                 debug_service=None, fix_service=None, rollback_service=None, cursor_manager=None):
        """
        Initialize the DebugOperationsHandler.
        
        Args:
            parent: Parent widget
            helpers: GuiHelpers instance
            dispatcher: Signal dispatcher
            logger: Logger instance
            debug_service: Debug service
            fix_service: Fix service
            rollback_service: Rollback service
            cursor_manager: Cursor manager service
        """
        self.parent = parent
        self.helpers = helpers
        self.dispatcher = dispatcher
        self.logger = logger
        self.debug_service = debug_service
        self.fix_service = fix_service
        self.rollback_service = rollback_service
        self.cursor_manager = cursor_manager
        
    def on_run_debug(self):
        """Run a debug session."""
        self.append_output("Starting debug session...")
        if self.debug_service:
            try:
                result = self.debug_service.run_debug_cycle()
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

    def on_apply_fix(self):
        """Apply a fix."""
        self.append_output("Applying fix...")
        if self.fix_service:
            try:
                result = self.fix_service.apply_fix()
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

    def on_rollback_fix(self):
        """Roll back a fix."""
        self.append_output("Rolling back fix...")
        if self.rollback_service:
            try:
                result = self.rollback_service.rollback_fix()
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

    def on_cursor_execute(self):
        """Execute a prompt via the Cursor integration by adding it to the task queue."""
        self.append_output("Queueing debug prompt for execution via Cursor...")
        if self.cursor_manager and hasattr(self.cursor_manager, 'queue_task'):
            try:
                # Use the queue_task method instead of a direct execute_prompt
                prompt = "## DEBUG PROMPT\nPlease analyze the current error state and generate a suggested fix."
                self.cursor_manager.queue_task(prompt)
                self.append_output(f"✅ Debug task queued: {prompt[:50]}...")
            except Exception as e:
                error_msg = f"Error queueing prompt via Cursor: {e}"
                self.append_output(error_msg)
                if self.dispatcher and hasattr(self.dispatcher, "emit_cursor_error"):
                    self.dispatcher.emit_cursor_error(str(e))
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
        else:
            self.append_output("❌ Cursor manager not available or doesn't support queue_task.")
            
    def append_output(self, message):
        """Pass the message to the parent for output handling."""
        if self.parent:
            self.parent.append_output(message) 