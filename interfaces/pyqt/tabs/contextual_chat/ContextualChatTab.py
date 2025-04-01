"""
Contextual Chat Tab Module (Refactored)

This tab provides a streamlined interface for:
1) Selecting a conversation (episode)
2) Pulling context from both local history and a project scanner
3) Sending a dynamic prompt to ChatGPT.com via the CursorSessionManager
4) Updating the conversation history with the newly returned response

Result: A continuous loop where local context + project analysis => prompt => Cursor => chatgpt.com => new response => local updates.
"""

import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QTextEdit, QComboBox, QPushButton,
    QLabel, QGroupBox, QCheckBox, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QTime
from qasync import asyncSlot

logger = logging.getLogger(__name__)

class ContextualChatTab(QWidget):
    """
    Main widget for the Contextual Chat Tab.
    Orchestrates conversation selection, history display, action execution,
    and optional automation—now using CursorSessionManager for UI automation,
    and optionally ProjectScanner for project context.
    """

    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """
        Initialize the Contextual Chat Tab.

        Args:
            services: Dictionary containing necessary services such as:
              - 'cursor_session_manager' (CursorSessionManager instance)
              - 'episode_generator' (manages conversation history)
              - 'template_manager'  (optional, for advanced prompt templating)
              - 'project_scanner'   (optional, to fetch project analysis JSON)
              - etc.
        """
        super().__init__()
        self.services = services or {}
        self.logger = logger

        # State
        self.selected_conversation_id = None
        self.is_auto_mode = False
        self.auto_timer = QTimer(self)  # Timer for automated steps

        # Grab references to key services
        self.cursor_session_manager = self.services.get("cursor_session_manager")
        self.episode_generator = self._get_nested_service("component_managers", "episode_generator")
        self.template_manager = self._get_nested_service("component_managers", "template_manager")
        self.project_scanner = self.services.get("project_scanner")  # could return analysis JSON

        # Setup the UI
        self._setup_ui()
        self._connect_signals()
        self._load_initial_data()

        # If the CursorSessionManager is available, let's hook into its callback
        if self.cursor_session_manager:
            self.cursor_session_manager.set_on_update_callback(self._on_cursor_task_update)
        else:
            self.logger.warning("CursorSessionManager not provided. UI automation won't work.")

    def _get_nested_service(self, parent_key: str, child_key: str):
        """Helper to safely navigate the services dict, e.g. services['component_managers']['episode_generator']."""
        parent = self.services.get(parent_key, {})
        return parent.get(child_key)

    def _setup_ui(self):
        """Set up the UI components based on our ASCII mockups."""
        main_layout = QVBoxLayout(self)

        # Top Splitter (Conversation List | History)
        top_splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Conversation List
        conversation_list_group = QGroupBox("Conversations")
        conversation_list_layout = QVBoxLayout()
        self.conversation_list_widget = QListWidget()
        conversation_list_layout.addWidget(self.conversation_list_widget)
        conversation_list_group.setLayout(conversation_list_layout)
        top_splitter.addWidget(conversation_list_group)

        # Right Panel: Conversation History
        history_group = QGroupBox("Conversation History")
        history_layout = QVBoxLayout()
        self.conversation_history_text = QTextEdit()
        self.conversation_history_text.setReadOnly(True)
        history_layout.addWidget(self.conversation_history_text)
        history_group.setLayout(history_layout)
        top_splitter.addWidget(history_group)

        top_splitter.setSizes([200, 500])  # Initial sizes for list and history
        main_layout.addWidget(top_splitter)

        # Bottom Control Area
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout()

        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        # Example built-in actions. You can expand with more advanced logic.
        self.action_combo.addItems(["Summarize Last", "Continue Thought", "Elaborate"])
        action_layout.addWidget(self.action_combo)
        action_layout.addStretch()

        self.auto_mode_checkbox = QCheckBox("Auto Mode")
        action_layout.addWidget(self.auto_mode_checkbox)
        control_layout.addLayout(action_layout)

        self.send_button = QPushButton("Send & Auto-Update Response")
        control_layout.addWidget(self.send_button)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # Automation Log/Status Area
        status_group = QGroupBox("Automation Status")
        status_layout = QVBoxLayout()
        self.status_log_text = QTextEdit()
        self.status_log_text.setReadOnly(True)
        self.status_log_text.setMaximumHeight(100)  # Limit height
        status_layout.addWidget(self.status_log_text)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connect UI signals to methods."""
        self.conversation_list_widget.currentItemChanged.connect(self._on_conversation_selected)
        self.send_button.clicked.connect(self._on_send_clicked)
        self.auto_mode_checkbox.stateChanged.connect(self._on_auto_mode_toggled)
        self.auto_timer.timeout.connect(self._run_automated_step)

    def _load_initial_data(self):
        """Load existing conversations into the list."""
        self.logger.info("Loading initial conversation list...")
        self.conversation_list_widget.clear()

        if not self.episode_generator:
            self._update_status_log("Error: Episode generator not available.")
            return

        try:
            episodes = self.episode_generator.get_episodes()
            if episodes:
                for ep in episodes:
                    title = ep.get("title", ep.get("id", "Unknown Episode"))
                    item = QListWidgetItem(title)
                    item.setData(Qt.UserRole, ep.get("id"))
                    self.conversation_list_widget.addItem(item)
                self._update_status_log(f"Loaded {len(episodes)} conversations.")
            else:
                self._update_status_log("No conversations found.")
        except Exception as e:
            self.logger.error(f"Error loading conversations: {e}", exc_info=True)
            self._update_status_log(f"Error loading conversations: {e}")

    def _on_conversation_selected(self, current_item, previous_item):
        """Handle selection of a conversation from the list."""
        self.conversation_history_text.clear()

        if not current_item:
            self.selected_conversation_id = None
            self._update_status_log("Conversation selection cleared.")
            return

        self.selected_conversation_id = current_item.data(Qt.UserRole)
        self.logger.info(f"Conversation selected: ID={self.selected_conversation_id}")
        self._load_conversation_history()

    def _load_conversation_history(self):
        """Load and display the conversation history for the selected conversation."""
        if not self.selected_conversation_id or not self.episode_generator:
            return

        try:
            history = self.episode_generator.get_episode_history(self.selected_conversation_id)
            # Convert to display text
            if isinstance(history, list):
                display_text = "\n---\n".join(history)
            elif isinstance(history, str):
                display_text = history
            else:
                display_text = "Unable to load history (invalid format)."

            self.conversation_history_text.setPlainText(display_text)
            self._update_status_log(f"Loaded history for conversation ID {self.selected_conversation_id}.")
        except Exception as e:
            self.logger.error(f"Error loading history for {self.selected_conversation_id}: {e}", exc_info=True)
            self._update_status_log(f"Error loading history: {e}")

    def _on_send_clicked(self):
        """Handle the manual 'Send' button click."""
        if not self.selected_conversation_id:
            self._update_status_log("Error: No conversation selected.")
            return

        selected_action = self.action_combo.currentText()
        self.logger.info(f"Manual send triggered for '{self.selected_conversation_id}' with action: {selected_action}")
        self._execute_conversation_step(selected_action)

    def _on_auto_mode_toggled(self, state):
        """Handle the 'Auto Mode' checkbox toggle."""
        self.is_auto_mode = (state == Qt.Checked)

        if self.is_auto_mode:
            self.logger.info("Auto Mode Enabled")
            self._update_status_log("Auto Mode Enabled. Waiting for next trigger...")

            # Start the timer for automated steps (e.g. every 10 seconds)
            interval_ms = 10000
            self.auto_timer.start(interval_ms)
            self._update_status_log(f"Automation timer started ({interval_ms / 1000}s interval).")
            self.send_button.setText("Stop Automation")
        else:
            self.logger.info("Auto Mode Disabled")
            self._update_status_log("Auto Mode Disabled.")
            self.auto_timer.stop()
            self.send_button.setText("Send & Auto-Update Response")

    def _run_automated_step(self):
        """Perform one step of the automated conversation update."""
        if not self.is_auto_mode or not self.selected_conversation_id:
            self.auto_timer.stop()  # Safety stop
            self._update_status_log("Auto Mode ended or no conversation selected.")
            return

        selected_action = self.action_combo.currentText()
        self.logger.info(f"Auto-step for '{self.selected_conversation_id}' with action: {selected_action}")
        self._execute_conversation_step(selected_action)

    @asyncSlot(str)
    async def _execute_conversation_step(self, action: str):
        """Core logic: gather context, build prompt, queue a Cursor task."""
        if not self.selected_conversation_id:
            self._update_status_log("Cannot execute: No conversation selected.")
            return

        # Make sure we have the essential service
        if not self.cursor_session_manager:
            self._update_status_log("Error: CursorSessionManager not available. Cannot automate UI.")
            return

        self._update_status_log(f"Executing action '{action}' for conversation {self.selected_conversation_id}...")

        try:
            # Gather local conversation context
            conversation_context = self._gather_local_context()

            # Optionally gather project analysis from ProjectScanner
            project_context = {}
            if self.project_scanner:
                project_context = self.project_scanner.load_cache()  # or .scan_project(), depends on your usage

            # Combine into a single prompt text
            prompt_text = self._build_prompt(action, conversation_context, project_context)
            if not prompt_text:
                self._update_status_log(f"Error: Could not build prompt for action '{action}'.")
                return

            self._update_status_log(f"Queueing task with Cursor for '{action}'...")

            # Enqueue a new task in the CursorSessionManager
            # We can include some context in case we want that later
            task_context = {
                "conversation_id": self.selected_conversation_id,
                "action": action
            }
            self.cursor_session_manager.queue_task(prompt_text, context=task_context)

        except Exception as e:
            self.logger.error(f"Error during conversation step execution: {e}", exc_info=True)
            self._update_status_log(f"Error executing step: {e}")

    def _gather_local_context(self) -> str:
        """
        Gather relevant local conversation context for the prompt.
        For example, the last message or full conversation from the current episode.
        """
        if not self.episode_generator or not self.selected_conversation_id:
            return ""

        # Example: gather the last message from the conversation
        history = self.episode_generator.get_episode_history(self.selected_conversation_id)
        if isinstance(history, list) and history:
            return history[-1]  # last entry
        elif isinstance(history, str):
            return history
        return ""

    def _build_prompt(self, action: str, conversation_context: str, project_context: dict) -> str:
        """
        Build a final prompt text from the selected action, local conversation context, and project analysis.
        If you have a template manager, you can use it here instead.
        """
        # If there's a template manager, you could do something like:
        # return self.template_manager.render_template_by_action(action, {"conv": conversation_context, "analysis": project_context})

        # Otherwise, here's a simple example:
        prompt = (
            f"Action: {action}\n"
            f"Most recent conversation message:\n{conversation_context}\n\n"
            f"Project Analysis:\n{project_context}\n\n"
            f"Please respond accordingly, referencing both conversation and code context."
        )
        return prompt

    def _on_cursor_task_update(self, outcome: Dict[str, Any]):
        """
        Callback for when CursorSessionManager completes a task or an error occurs.
        outcome might contain:
          - "task": The original prompt text
          - "context": Additional data passed in queue_task
          - "response": The simulated/real code or text from ChatGPT
          - "success": bool
          - "error": str, if any
        """
        if "error" in outcome:
            error_msg = outcome["error"]
            self._update_status_log(f"Cursor Error: {error_msg}")
            return

        if outcome.get("success"):
            conversation_id = outcome["context"].get("conversation_id")
            response_text = outcome["response"]
            action = outcome["context"].get("action", "NoAction")
            self._update_status_log(f"Cursor task success for {conversation_id}, action={action}.")

            # Append the response to local conversation history
            self._append_llm_response(conversation_id, response_text)
        else:
            self._update_status_log("Cursor task completed but success=False. Check logs.")

    def _append_llm_response(self, conversation_id: str, response_text: str):
        """Append LLM response to the local conversation and update UI."""
        if not self.episode_generator:
            return

        # Append to the local store
        self.episode_generator.append_to_episode(conversation_id, "llm", response_text)

        # Update the UI's conversation history text
        old_text = self.conversation_history_text.toPlainText()
        self.conversation_history_text.setPlainText(f"{old_text}\n\n---\nLLM: {response_text}")

        self._update_status_log(f"Conversation {conversation_id} updated with new LLM response.")

    def _update_status_log(self, message: str):
        """Append a message to the status log QTextEdit."""
        timestamp = QTime.currentTime().toString("hh:mm:ss")
        self.status_log_text.append(f"[{timestamp}] {message}")
        self.logger.info(message)

    # Optional teardown or final steps
    def closeEvent(self, event):
        """Ensure the auto_timer is stopped on close."""
        if self.auto_timer.isActive():
            self.auto_timer.stop()
        super().closeEvent(event) 