import os
import json
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QTextEdit, QFileDialog, QMessageBox, QDialog, QHBoxLayout
)
from PyQt5.QtCore import Qt
from core.ReinforcementEngine import ReinforcementEngine

logger = logging.getLogger("reinforcement_tools")


class ReinforcementToolsDialog(QDialog):
    """
    Dialog UI for Reinforcement Engine analysis and feedback management.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reinforcement Tools")
        self.setMinimumWidth(600)
        self.engine = ReinforcementEngine()

        self.layout = QVBoxLayout()
        self.feedback_list = QListWidget()
        self.feedback_details = QTextEdit()
        self.feedback_details.setReadOnly(True)

        # Buttons
        self.refresh_button = QPushButton("🔄 Refresh Feedback")
        self.export_button = QPushButton("💾 Export Feedback")
        self.clear_button = QPushButton("🗑️ Clear Feedback")
        self.tune_button = QPushButton("🎛️ Auto-Tune Prompts")

        # Layout and events
        self.layout.addWidget(QLabel("Reinforcement Feedback History"))
        self.layout.addWidget(self.feedback_list)
        self.layout.addWidget(QLabel("Feedback Details"))
        self.layout.addWidget(self.feedback_details)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.refresh_button)
        btn_layout.addWidget(self.export_button)
        btn_layout.addWidget(self.clear_button)
        btn_layout.addWidget(self.tune_button)

        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)

        self.refresh_button.clicked.connect(self.load_feedback)
        self.feedback_list.itemClicked.connect(self.show_feedback_details)
        self.export_button.clicked.connect(self.export_feedback)
        self.clear_button.clicked.connect(self.clear_feedback)
        self.tune_button.clicked.connect(self.auto_tune_prompts)

        self.load_feedback()

    def load_feedback(self):
        """
        Populate the list with available prompt feedback records.
        """
        self.feedback_list.clear()
        feedback = self.engine.memory_data.get("reinforcement_feedback", {})

        if not feedback:
            self.feedback_list.addItem("No feedback records found.")
            return

        for prompt_name, records in feedback.items():
            if records:
                latest_record = records[-1]
                score = latest_record.get("scores", {}).get("final_score", "N/A")
                item_text = f"{prompt_name} | Last Score: {score}"
                self.feedback_list.addItem(item_text)

    def show_feedback_details(self, item):
        """
        Display full details of the selected prompt's latest feedback.
        """
        text = item.text()
        prompt_name = text.split('|')[0].strip()

        records = self.engine.memory_data.get("reinforcement_feedback", {}).get(prompt_name, [])

        if not records:
            self.feedback_details.setText("No feedback data available.")
            return

        latest = records[-1]
        details = json.dumps(latest, indent=4, ensure_ascii=False)
        self.feedback_details.setText(details)

    def export_feedback(self):
        """
        Export reinforcement feedback data to a JSON file.
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Feedback", "reinforcement_feedback.json", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.engine.memory_data.get("reinforcement_feedback", {}), f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "Success", f"Feedback exported successfully to:\n{file_path}")
            logger.info(f" Feedback exported to {file_path}")

        except Exception as e:
            logger.error(f" Failed to export feedback: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export feedback:\n{e}")

    def clear_feedback(self):
        """
        Clear reinforcement feedback after confirmation.
        """
        confirm = QMessageBox.question(self, "Confirm Clear", "Are you sure you want to clear ALL feedback data?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        self.engine.memory_data["reinforcement_feedback"] = {}
        self.engine.memory_data["prompt_scores"] = {}
        self.engine.save_memory()

        logger.info("️ Cleared all reinforcement feedback data.")
        QMessageBox.information(self, "Cleared", "All feedback records have been cleared.")
        self.load_feedback()
        self.feedback_details.clear()

    def auto_tune_prompts(self):
        """
        Auto-tune prompts based on feedback. Requires prompt_manager injection.
        """
        try:
            # PromptManager must be injected from parent
            prompt_manager = getattr(self.parent(), "prompt_manager", None)
            if not prompt_manager:
                raise ValueError("PromptManager not found on parent window.")

            self.engine.auto_tune_prompts(prompt_manager)
            QMessageBox.information(self, "Auto-Tune", "Prompts auto-tuned based on feedback.")
            logger.info("️ Auto-tuned prompts successfully.")

        except Exception as e:
            logger.error(f" Failed to auto-tune prompts: {e}")
            QMessageBox.critical(self, "Error", f"Auto-tuning failed:\n{e}")
