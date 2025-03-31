"""
Task Queue Operations for AIDE

This module contains operations for the TaskQueueHandler class.
To be imported by task_queue.py
"""

import json
from datetime import datetime
from PyQt5.QtWidgets import (QListWidgetItem, QMenu, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from typing import Dict, Any, List, Optional

# Make these methods accessible to TaskQueueHandler
def handle_cursor_manager_update(self, update_data: Dict[str, Any]):
    """Handle updates pushed from the CursorSessionManager via callback."""
    event_type = update_data.get("event_type")
    task_id = update_data.get("task_id")
    
    if event_type == "queue_changed":
        queue_snapshot = update_data.get("queue_snapshot", []) 
        self.update_task_queue_display(queue_snapshot)
        self.append_output("Task queue display updated.")
    elif event_type == "task_started":
        self.append_output(f"▶️ Task [{task_id[:6]}...] started.")
        # Update task data in our dictionary
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id]["status"] = "running"
        self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
        self._update_task_item_status(task_id, "running")
    elif event_type == "task_completed":
        self.append_output(f"✅ Task [{task_id[:6]}...] completed.")
        # Update task data in our dictionary
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id]["status"] = "completed"
        self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
        self.tasks[task_id]["response"] = update_data.get("response", "")
        self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
        
        # Add any test generation data
        if "generated_test_path" in update_data:
            self.tasks[task_id]["generated_test_path"] = update_data.get("generated_test_path")
            
        # Add any coverage analysis
        if "coverage_analysis" in update_data:
            self.tasks[task_id]["coverage_analysis"] = update_data.get("coverage_analysis")
            
        # Include file path if provided
        if "file_path" in update_data:
            self.tasks[task_id]["file_path"] = update_data.get("file_path")
            
        # Include mode if available
        if "mode" in update_data:
            self.tasks[task_id]["mode"] = update_data.get("mode")
            
        self._update_task_item_status(task_id, "completed")
    elif event_type == "task_failed":
        error_msg = update_data.get("error", "Unknown error")
        self.append_output(f"❌ Task [{task_id[:6]}...] failed. Error: {error_msg}")
        # Update task data in our dictionary
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id]["status"] = "failed"
        self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
        self.tasks[task_id]["error"] = error_msg
        self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
        self._update_task_item_status(task_id, "failed")
    elif event_type == "queue_empty":
        self.append_output("Task queue is empty.")
        self.update_task_queue_display([])
    elif event_type == "task_rejected":
        reason = update_data.get("reason", "Unknown reason")
        self.append_output(f"⚠️ Task [{task_id[:6]}...] rejected: {reason}")
        # Update task data in our dictionary
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id]["status"] = "failed"
        self.tasks[task_id]["error"] = f"Rejected: {reason}"
        self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
        self._update_task_item_status(task_id, "failed", f"Rejected: {reason}")
    # Add handlers for lifecycle stages
    elif event_type == "lifecycle_stage_change":
        stage = update_data.get("stage")
        self.append_output(f"🔄 Task [{task_id[:6]}...] in {stage} stage.")
        # Update task data in our dictionary
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id]["status"] = stage
        self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
        self._update_task_item_status(task_id, stage)

def get_status_prefix(self, status: Optional[str]) -> str:
    """Return a prefix string based on task status."""
    status_map = {
        "queued": "[Q]",
        "running": "[R]", # Or ▶️ if unicode preferred
        "processing": "[R]",
        "completed": "[✓]",
        "failed": "[X]",
        # Add lifecycle stages
        "validating": "[V]",
        "injecting": "[I]",
        "approving": "[A]",
        "dispatching": "[D]"
    }
    return status_map.get(status, "[?]") # Default for unknown status

def update_task_queue_display(self, queue_snapshot: List[Dict[str, Any]]):
    """Clear and repopulate the task queue list widget using task dictionaries."""
    self.task_queue_list.clear()
    if not queue_snapshot:
        self.task_queue_list.addItem("(Queue Empty)")
        self.task_queue_list.setEnabled(False)
    else:
        for task in queue_snapshot:
            task_id = task.get("task_id", "NO_ID")
            priority = task.get("priority", "med")
            source = task.get("source", "?")
            prompt = task.get("prompt", "<No Prompt>")
            status = task.get("status", "queued") # Status from manager
            
            # Check for lifecycle stage - show the most recent stage
            lifecycle = task.get("lifecycle", {})
            if lifecycle:
                # Determine the most recent stage based on timestamps
                if "dispatched_at" in lifecycle:
                    status = "dispatching"
                elif "approved_at" in lifecycle:
                    status = "approving"
                elif "validated_at" in lifecycle:
                    status = "validating"
                elif "injected_at" in lifecycle:
                    status = "injecting"
            
            status_prefix = self.get_status_prefix(status)
            display_text = f"{status_prefix} [{priority[:1].upper()}] {source[:3]} | {prompt[:40]}..."
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, task) # Store the full task dict 
            
            # Extended tooltip with lifecycle information
            tooltip = f"ID: {task_id}\nStatus: {status}\nPrompt: {prompt}"
            if lifecycle:
                tooltip += "\n--- Lifecycle ---"
                if "queued_at" in lifecycle:
                    tooltip += f"\nQueued: {lifecycle['queued_at']}"
                if "injected_at" in lifecycle:
                    tooltip += f"\nContext Injected: {lifecycle['injected_at']}"
                if "validated_at" in lifecycle:
                    tooltip += f"\nValidated: {lifecycle['validated_at']}"
                if "approved_at" in lifecycle:
                    tooltip += f"\nApproved: {lifecycle['approved_at']}"
                if "dispatched_at" in lifecycle:
                    tooltip += f"\nDispatched: {lifecycle['dispatched_at']}"
                if "completed_at" in lifecycle:
                    tooltip += f"\nCompleted: {lifecycle['completed_at']}"
            
            # Add coverage information if available in the task
            if 'coverage_analysis' in task:
                coverage = task.get('coverage_analysis', {})
                tooltip += f"\n\nCoverage: {coverage.get('percentage', 0)}%"
                
                if 'trend' in coverage:
                    tooltip += f"\nTrend: {coverage.get('trend')}"
                    
                if coverage.get('needs_improvement', False):
                    tooltip += "\nRecommendation: Improve test coverage"
            
            # Add file path if available
            if 'file_path' in task:
                tooltip += f"\nFile: {task.get('file_path')}"
                
            # Add generated test path if available
            if 'generated_test_path' in task:
                tooltip += f"\nGenerated Test: {task.get('generated_test_path')}"
            
            item.setToolTip(tooltip)
            
            # Apply background color based on status
            if status == 'running' or status == 'processing':
                item.setBackground(QColor(230, 255, 230))  # Light green
            elif status == 'completed':
                item.setBackground(QColor(220, 240, 255))  # Light blue
            elif status == 'failed':
                item.setBackground(QColor(255, 230, 230))  # Light red
            
            self.task_queue_list.addItem(item)
        self.task_queue_list.setEnabled(True)

def _update_task_item_status(self, task_id: str, new_status: str, message: str = None):
    """Finds a task item by ID and updates its display text/status."""
    for i in range(self.task_queue_list.count()):
        item = self.task_queue_list.item(i)
        task_data = item.data(Qt.UserRole)
        if task_data and task_data.get("task_id") == task_id:
            # Update the stored status first (optional but good practice)
            task_data["status"] = new_status 
            item.setData(Qt.UserRole, task_data) 
            
            # Update display text
            priority = task_data.get("priority", "med")
            source = task_data.get("source", "?")
            prompt = task_data.get("prompt", "<No Prompt>")
            status_prefix = self.get_status_prefix(new_status)
            display_text = f"{status_prefix} [{priority[:1].upper()}] {source[:3]} | {prompt[:40]}..."
            item.setText(display_text)
            
            # Update tooltip with optional message
            tooltip = f"ID: {task_id}\nStatus: {new_status}\nPrompt: {prompt}"
            if message:
                tooltip += f"\nMessage: {message}"
            
            # Add lifecycle info if available
            lifecycle = task_data.get("lifecycle", {})
            if lifecycle:
                tooltip += "\n--- Lifecycle ---"
                stages = ["queued_at", "injected_at", "validated_at", "approved_at", "dispatched_at", "completed_at"]
                for stage in stages:
                    if stage in lifecycle:
                        tooltip += f"\n{stage.replace('_at', '').capitalize()}: {lifecycle[stage]}"
            
            item.setToolTip(tooltip)
            break # Found and updated

@pyqtSlot(QListWidgetItem)
def on_task_double_clicked(self, item):
    """Show task details on double-click with enhanced lifecycle information."""
    self._show_task_details(item)

def _show_task_details(self, item):
    """Show detailed information about a task when double-clicked."""
    task_data = item.data(Qt.UserRole)
    if not task_data:
        return
        
    task_id = task_data.get("task_id", "Unknown")
        
    # Create a detailed message with formatting
    details = f"<h3>Task Details: {task_id}</h3>"
    details += f"<p><b>Prompt:</b> {task_data.get('prompt', 'Unknown')}</p>"
    details += f"<p><b>Status:</b> {task_data.get('status', 'Unknown')}</p>"
    
    # Add file path if available
    if 'file_path' in task_data:
        details += f"<p><b>File:</b> {task_data.get('file_path')}</p>"
        
    # Add mode information if available
    if 'mode' in task_data:
        details += f"<p><b>Mode:</b> {task_data.get('mode')}</p>"
        
    # Add test generation information if available
    if 'generated_test_path' in task_data:
        details += f"<p><b>Generated Test:</b> {task_data.get('generated_test_path')}</p>"
        
    # Add coverage analysis if available
    if 'coverage_analysis' in task_data:
        coverage = task_data.get('coverage_analysis', {})
        percentage = coverage.get('percentage', 0)
        
        # Determine color based on coverage percentage
        color = "green" if percentage >= 80 else "orange" if percentage >= 50 else "red"
        
        details += f"<div style='margin-top: 10px;'>"
        details += f"<h4>Test Coverage Analysis</h4>"
        details += f"<p><b>Coverage:</b> <span style='color: {color};'>{percentage}%</span></p>"
        
        # Add trend information
        if 'trend' in coverage:
            trend = coverage.get('trend')
            trend_icon = "▲" if trend == "increasing" else "▼" if trend == "decreasing" else "◆"
            details += f"<p><b>Trend:</b> {trend_icon} {trend}</p>"
            
        # Add uncovered functions count
        if 'uncovered_functions_count' in coverage:
            details += f"<p><b>Uncovered Functions:</b> {coverage.get('uncovered_functions_count')}</p>"
            
        # Add recommendation
        if coverage.get('needs_improvement', False):
            details += f"<p style='color: orange;'><b>Recommendation:</b> Test coverage should be improved</p>"
            
        details += "</div>"
        
    # Add lifecycle information if available
    lifecycle = task_data.get('lifecycle', {})
    if lifecycle:
        details += f"<div style='margin-top: 10px;'>"
        details += f"<h4>Lifecycle</h4>"
        stages = [
            ("queued_at", "Queued"),
            ("injected_at", "Context Injected"), 
            ("validated_at", "Validated"),
            ("approved_at", "Approved"),
            ("dispatched_at", "Dispatched"),
            ("completed_at", "Completed")
        ]
        for key, label in stages:
            if key in lifecycle:
                details += f"<p><b>{label}:</b> {lifecycle[key]}</p>"
        details += "</div>"
            
    # Display the details in a message box
    msg_box = QMessageBox()
    msg_box.setWindowTitle(f"Task Details - {task_id}")
    msg_box.setTextFormat(Qt.RichText)
    msg_box.setText(details)
    
    # Add buttons for actions
    if task_data.get('status') == 'failed':
        retry_button = msg_box.addButton("Retry Task", QMessageBox.ActionRole)
    
    if task_data.get('coverage_analysis', {}).get('needs_improvement', False):
        improve_button = msg_box.addButton("Improve Tests", QMessageBox.ActionRole)
        
    close_button = msg_box.addButton("Close", QMessageBox.RejectRole)
    
    # Show the dialog and process the result
    msg_box.exec_()
    
    # Handle button clicks
    clicked_button = msg_box.clickedButton()
    
    if clicked_button and clicked_button.text() == "Retry Task" and task_data.get('status') == 'failed':
        self._requeue_task(task_id)
    elif clicked_button and clicked_button.text() == "Improve Tests" and task_data.get('coverage_analysis', {}).get('needs_improvement', False):
        self._improve_test_coverage(task_id, task_data)

def show_task_context_menu(self, position):
    """Show context menu for tasks."""
    self._handle_context_menu(position)

def _handle_context_menu(self, position):
    """Handle right-click context menu on task list items."""
    item = self.task_queue_list.itemAt(position)
    if not item:
        return
        
    task_data = item.data(Qt.UserRole)
    if not task_data:
        return
        
    task_id = task_data.get("task_id", "Unknown")
        
    # Create context menu
    menu = QMenu()
    status = task_data.get('status', 'unknown')
    
    # Add actions based on task status
    if status == 'queued':
        cancel_action = menu.addAction("Cancel Task")
        boost_action = menu.addAction("Boost Priority")
    elif status == 'completed':
        view_action = menu.addAction("View Details")
        if task_data.get('coverage_analysis', {}).get('needs_improvement', False):
            improve_tests_action = menu.addAction("Improve Test Coverage")
    elif status == 'failed':
        retry_action = menu.addAction("Retry Task")
        view_action = menu.addAction("View Error Details")
        
    # Always add these options
    copy_action = menu.addAction("Copy Task ID")
    
    # Show the menu and get the selected action
    action = menu.exec_(self.task_queue_list.mapToGlobal(position))
    
    # Handle the selected action
    if not action:
        return
        
    if status == 'queued' and action.text() == "Cancel Task":
        self._cancel_task(task_id)
    elif status == 'queued' and action.text() == "Boost Priority":
        self._boost_task_priority(task_id)
    elif action.text() == "View Details" or action.text() == "View Error Details":
        self._show_task_details(item)
    elif status == 'failed' and action.text() == "Retry Task":
        self._requeue_task(task_id)
    elif action.text() == "Copy Task ID":
        QApplication.clipboard().setText(task_id)
    elif action.text() == "Improve Test Coverage":
        self._improve_test_coverage(task_id, task_data)

def _add_task_to_queue(self, task_data):
    """Add a task to the queue using cursor manager."""
    if self.cursor_manager and hasattr(self.cursor_manager, 'queue_task'):
        try:
            self.cursor_manager.queue_task(task_data)
            self.append_output(f"✅ Task queued: {task_data.get('prompt', '')[:50]}...")
            return True
        except Exception as e:
            error_msg = f"❌ Error queueing task: {e}"
            self.append_output(error_msg)
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            return False
    else:
        self.append_output("❌ Cursor manager not available or doesn't support queue_task.")
        return False

def _requeue_task(self, task_id):
    """Requeue a failed task."""
    task_data = self._get_task_data(task_id)
    if not task_data:
        self.append_output(f"❌ Cannot requeue task {task_id}: task data not found.")
        return
    
    # Create a new task with the same data
    new_task = {
        "prompt": task_data.get("task_prompt", ""),
        "priority": task_data.get("priority", "medium"),
        "source": task_data.get("source", "requeue"),
        "file_path": task_data.get("file_path"),
        "mode": task_data.get("mode"),
        "parent_task_id": task_id  # Link to the original task
    }
    
    # Add any additional data that might be useful
    if "context" in task_data:
        new_task["context"] = task_data["context"]
        
    success = self._add_task_to_queue(new_task)
    if success:
        QMessageBox.information(self.parent, "Task Requeued", f"Task {task_id} has been requeued.")
    else:
        QMessageBox.warning(self.parent, "Requeue Failed", f"Failed to requeue task {task_id}.")

def _cancel_task(self, task_id):
    """Cancel a queued task."""
    if self.cursor_manager and hasattr(self.cursor_manager, 'cancel_task'):
        try:
            self.cursor_manager.cancel_task(task_id)
            self.append_output(f"✅ Task {task_id} cancelled.")
            
            # Update our local task data
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = "cancelled"
                self._update_task_item_status(task_id, "cancelled")
                
            return True
        except Exception as e:
            error_msg = f"❌ Error cancelling task {task_id}: {e}"
            self.append_output(error_msg)
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            return False
    else:
        self.append_output("❌ Cursor manager not available or doesn't support cancel_task.")
        return False

def _boost_task_priority(self, task_id):
    """Boost the priority of a queued task."""
    if self.cursor_manager and hasattr(self.cursor_manager, 'update_task_priority'):
        try:
            self.cursor_manager.update_task_priority(task_id, "high")
            self.append_output(f"✅ Task {task_id} priority boosted to high.")
            
            # Update our local task data
            if task_id in self.tasks:
                self.tasks[task_id]["priority"] = "high"
                
            return True
        except Exception as e:
            error_msg = f"❌ Error boosting priority for task {task_id}: {e}"
            self.append_output(error_msg)
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            return False
    else:
        self.append_output("❌ Cursor manager not available or doesn't support update_task_priority.")
        return False

def _improve_test_coverage(self, task_id, task_data):
    """Create a new task to improve test coverage for the given task."""
    file_path = task_data.get('file_path')
    if not file_path:
        QMessageBox.warning(self.parent, "Error", "Cannot improve tests: No file path available")
        return
        
    # Get coverage information
    coverage = task_data.get('coverage_analysis', {})
    percentage = coverage.get('percentage', 0)
    uncovered_count = coverage.get('uncovered_functions_count', 0)
    
    # Create a new task with appropriate metadata
    new_task = {
        "prompt": f"Improve test coverage for {file_path}. Current coverage is {percentage}% with {uncovered_count} uncovered functions. Focus on generating tests for untested functionality.",
        "file_path": file_path,
        "mode": "coverage_driven",
        "analyze_coverage": True,
        "generate_tests": True,
        "priority": 10,  # High priority
        "parent_task_id": task_id  # Link to the original task
    }
    
    # Add the task to the queue
    self._add_task_to_queue(new_task)
    
    # Show confirmation
    QMessageBox.information(self.parent, "Task Added", f"Added task to improve test coverage for {file_path}")

def _get_task_data(self, task_id):
    """Get task data from stored tasks dictionary."""
    return self.tasks.get(task_id, None)

def append_output(self, message):
    """Pass the message to the parent for output handling."""
    if self.parent:
        self.parent.append_output(message) 