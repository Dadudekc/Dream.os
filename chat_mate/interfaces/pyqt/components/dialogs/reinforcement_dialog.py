from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QTextEdit, QMessageBox
)


class ReinforcementToolsDialog(QDialog):
    """
    Dialog window for reinforcement learning tools.
    Provides prompt feedback review, tuning, and export functionality.
    """
    def __init__(self, ui_logic, parent=None):
        super().__init__(parent)
        self.ui_logic = ui_logic
        self.reinforcement_engine = self.ui_logic.reinforcement_engine

        self.setWindowTitle("Reinforcement Tools")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # --- Feedback List Section ---
        feedback_layout = QVBoxLayout()
        feedback_label = QLabel("Feedback Entries:")
        self.feedback_list = QListWidget()
        self.feedback_list.itemClicked.connect(self.display_feedback_details)

        feedback_layout.addWidget(feedback_label)
        feedback_layout.addWidget(self.feedback_list)

        # --- Feedback Details Section ---
        details_layout = QVBoxLayout()
        details_label = QLabel("Feedback Details:")
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)

        details_layout.addWidget(details_label)
        details_layout.addWidget(self.details_text)

        # --- Actions Section ---
        actions_layout = QHBoxLayout()

        load_button = QPushButton("Load Feedback")
        load_button.clicked.connect(self.load_feedback)

        export_button = QPushButton("Export Feedback Report")
        export_button.clicked.connect(self.export_feedback)

        clear_button = QPushButton("Clear Feedback")
        clear_button.clicked.connect(self.clear_feedback)

        tune_button = QPushButton("Auto Tune Prompts")
        tune_button.clicked.connect(self.auto_tune_prompts)

        actions_layout.addWidget(load_button)
        actions_layout.addWidget(export_button)
        actions_layout.addWidget(clear_button)
        actions_layout.addWidget(tune_button)

        # Assemble the layouts
        layout.addLayout(feedback_layout)
        layout.addLayout(details_layout)
        layout.addLayout(actions_layout)

        # Close Button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def load_feedback(self):
        """
        Load feedback entries from the reinforcement engine and populate the list.
        """
        feedback_entries = self.reinforcement_engine.load_feedback()

        self.feedback_list.clear()

        if not feedback_entries:
            QMessageBox.information(self, "No Feedback", "No feedback entries available.")
            return

        for entry in feedback_entries:
            item_text = f"{entry['prompt_type']} - {entry['score']}"
            self.feedback_list.addItem(item_text)

    def display_feedback_details(self):
        """
        Display details for the selected feedback item.
        """
        selected_item = self.feedback_list.currentItem()
        if not selected_item:
            return

        selected_index = self.feedback_list.currentRow()
        feedback_entries = self.reinforcement_engine.load_feedback()

        if selected_index >= len(feedback_entries):
            return

        entry = feedback_entries[selected_index]
        details = (
            f"Prompt Type: {entry.get('prompt_type', 'N/A')}\n"
            f"Score: {entry.get('score', 'N/A')}\n"
            f"Comments: {entry.get('comments', '')}\n"
            f"Timestamp: {entry.get('timestamp', '')}\n"
            f"\n--- Prompt ---\n{entry.get('prompt', '')}\n"
            f"\n--- Response ---\n{entry.get('response', '')}"
        )
        self.details_text.setPlainText(details)

    def export_feedback(self):
        """
        Export the feedback report to a markdown or HTML file.
        """
        success = self.reinforcement_engine.export_feedback()

        if success:
            QMessageBox.information(self, "Export Successful", "Feedback report exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export feedback report.")

    def clear_feedback(self):
        """
        Clear all feedback entries from memory and storage.
        """
        confirmation = QMessageBox.question(
            self, "Confirm Clear", "Are you sure you want to clear all feedback?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            self.reinforcement_engine.clear_feedback()
            self.feedback_list.clear()
            self.details_text.clear()
            QMessageBox.information(self, "Feedback Cleared", "All feedback has been cleared.")

    def auto_tune_prompts(self):
        """
        Automatically adjust prompt templates based on feedback.
        """
        success = self.reinforcement_engine.auto_tune_prompts()

        if success:
            QMessageBox.information(self, "Auto Tune Complete", "Prompts have been auto-tuned successfully.")
        else:
            QMessageBox.warning(self, "Auto Tune Failed", "Prompt tuning process failed.")
