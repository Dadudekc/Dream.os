import os
import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QTextEdit,
    QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt

# Set up logger for reinforcement tools
logger = logging.getLogger("reinforcement_engine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))
    logger.addHandler(ch)


# -------------------------------------------
# ReinforcementEngine Class
# -------------------------------------------
class ReinforcementEngine:
    def __init__(self, memory_file=None):
        # If not provided, use default path relative to this file
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if memory_file is None:
            memory_file = os.path.join(base_dir, "persistent_memory.json")
        self.memory_file = memory_file
        self.memory_data = self.load_memory()

    # ---------------------------
    # MEMORY HANDLING
    # ---------------------------
    def load_memory(self):
        """Load persistent memory JSON. Initialize if missing."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"✅ Loaded memory from {self.memory_file}")
                    return data
            except Exception as e:
                logger.error(f"❌ Failed to load memory: {e}")
        # Initialize default structure
        logger.info("Initializing new memory structure.")
        return {
            "reinforcement_feedback": {},
            "prompt_scores": {},
            "execution_logs": [],
            "last_updated": datetime.now().isoformat()
        }

    def save_memory(self):
        """Persist updated memory to disk."""
        self.memory_data["last_updated"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_data, f, indent=4, ensure_ascii=False)
            logger.info(f"💾 Memory saved to {self.memory_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save memory: {e}")

    # ---------------------------
    # FEEDBACK COLLECTION & ANALYSIS
    # ---------------------------
    def detect_hallucination(self, response: str) -> bool:
        """Detect if response contains likely hallucinations."""
        signals = [
            "AI hallucination", "as an AI language model", 
            "I do not have access", "I'm unable to browse"
        ]
        return any(signal.lower() in response.lower() for signal in signals)

    def calculate_length_score(self, response: str) -> float:
        """Score based on word count (up to 1.0)."""
        words = len(response.split())
        return min(words / 100, 1.0)

    def detect_clarity_issues(self, response: str) -> float:
        """Return 0 if common clarity issues are found, else 1."""
        issues = ["error", "unclear", "not enough information"]
        return 0 if any(issue in response.lower() for issue in issues) else 1

    def calculate_coherence_score(self, response: str) -> float:
        """
        Calculate a rough coherence score based on word repetition.
        Lower repetition implies higher coherence.
        """
        words = response.split()
        if not words:
            return 0.0
        unique_words = set(words)
        repetition_ratio = 1 - (len(unique_words) / len(words))
        # A lower repetition ratio is better; we subtract from 1.
        coherence = max(1 - repetition_ratio, 0)
        return round(coherence, 2)

    def analyze_response(self, prompt_name: str, prompt_text: str, response: str) -> float:
        """
        Evaluate the AI response and compute a final score using multiple metrics.
        Detailed metrics include:
          - Length score
          - Clarity score
          - Coherence score
        A penalty is applied if hallucinations are detected.
        Feedback is logged and stored.
        """
        hallucination = self.detect_hallucination(response)
        length_score = self.calculate_length_score(response)
        clarity_score = self.detect_clarity_issues(response)
        coherence_score = self.calculate_coherence_score(response)
        # Average the scores (all range 0-1)
        base_score = (length_score + clarity_score + coherence_score) / 3
        # Apply hallucination penalty if needed
        final_score = max(base_score - 0.5 if hallucination else base_score, 0)
        final_score = round(final_score, 2)

        feedback = {
            "prompt": prompt_text,
            "response_snapshot": response if len(response) <= 250 else response[:250] + "...",
            "hallucination": hallucination,
            "scores": {
                "length_score": length_score,
                "clarity_score": clarity_score,
                "coherence_score": coherence_score,
                "final_score": final_score
            },
            "timestamp": datetime.now().isoformat()
        }
        self.memory_data.setdefault("reinforcement_feedback", {}).setdefault(prompt_name, []).append(feedback)
        self.memory_data["prompt_scores"][prompt_name] = final_score
        self.append_execution_log(prompt_name, final_score, hallucination)
        self.save_memory()
        return final_score

    def append_execution_log(self, prompt_name: str, score: float, hallucination: bool):
        """Append an execution log entry for traceability."""
        log_entry = {
            "prompt_name": prompt_name,
            "score": score,
            "hallucination": hallucination,
            "timestamp": datetime.now().isoformat()
        }
        self.memory_data.setdefault("execution_logs", []).append(log_entry)

    # ---------------------------
    # FEEDBACK-DRIVEN TUNING
    # ---------------------------
    def auto_tune_prompts(self, prompt_manager):
        """
        Adjust prompts dynamically based on stored feedback.
        If the final score is low, suggestions are appended to improve clarity and brevity.
        """
        tuned_count = 0
        feedback_data = self.memory_data.get("reinforcement_feedback", {})
        for prompt_name, records in feedback_data.items():
            if not records:
                continue
            latest = records[-1]
            score = latest.get("scores", {}).get("final_score", 1)
            try:
                current_prompt = prompt_manager.get_prompt(prompt_name)
            except Exception:
                continue  # Skip if prompt doesn't exist
            tuned_prompt = None
            if score < 0.3:
                tuned_prompt = current_prompt + " Clarify the core message and reduce unnecessary context."
            elif score < 0.5:
                tuned_prompt = current_prompt + " Be concise and avoid overexplaining."
            if tuned_prompt:
                prompt_manager.add_prompt(prompt_name, tuned_prompt, prompt_manager.get_model(prompt_name))
                tuned_count += 1
        prompt_manager.save_prompts()
        self.append_tuning_log(tuned_count)

    def append_tuning_log(self, tuned_count: int):
        logger.info(f"✅ Auto-tuned {tuned_count} prompts based on reinforcement feedback.")


# -------------------------------------------
# ReinforcementToolsDialog Class (GUI)
# -------------------------------------------
class ReinforcementToolsDialog(QDialog):
    """
    A dialog for managing reinforcement feedback, exporting logs,
    clearing feedback data, and auto-tuning prompts.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reinforcement Tools")
        self.setMinimumWidth(600)
        self.engine = ReinforcementEngine()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Feedback list and details view
        layout.addWidget(QLabel("Reinforcement Feedback History"))
        self.feedback_list = QListWidget()
        layout.addWidget(self.feedback_list)

        layout.addWidget(QLabel("Feedback Details"))
        self.feedback_details = QTextEdit()
        self.feedback_details.setReadOnly(True)
        layout.addWidget(self.feedback_details)

        # Buttons
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Feedback")
        self.export_btn = QPushButton("Export Feedback")
        self.clear_btn = QPushButton("Clear Feedback")
        self.tune_btn = QPushButton("Auto-Tune Prompts")

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.tune_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect signals
        self.refresh_btn.clicked.connect(self.load_feedback)
        self.export_btn.clicked.connect(self.export_feedback)
        self.clear_btn.clicked.connect(self.clear_feedback)
        self.tune_btn.clicked.connect(self.auto_tune_prompts)
        self.feedback_list.itemClicked.connect(self.display_feedback_details)

        self.load_feedback()

    def load_feedback(self):
        """Load feedback records into the list widget."""
        self.feedback_list.clear()
        feedback = self.engine.memory_data.get("reinforcement_feedback", {})
        if not feedback:
            self.feedback_list.addItem("No feedback records found.")
            return
        for prompt_name, records in feedback.items():
            if records:
                latest = records[-1]
                score = latest.get("scores", {}).get("final_score", "N/A")
                self.feedback_list.addItem(f"{prompt_name} | Last Score: {score}")

    def display_feedback_details(self, item):
        """Display full details for the selected feedback record."""
        text = item.text()
        prompt_name = text.split("|")[0].strip()
        records = self.engine.memory_data.get("reinforcement_feedback", {}).get(prompt_name, [])
        if not records:
            self.feedback_details.setText("No details available.")
            return
        latest = records[-1]
        details = json.dumps(latest, indent=4, ensure_ascii=False)
        self.feedback_details.setText(details)

    def export_feedback(self):
        """Export the reinforcement feedback to a JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Feedback", "reinforcement_feedback.json", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.engine.memory_data.get("reinforcement_feedback", {}), f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Success", f"Feedback exported to:\n{file_path}")
            logger.info(f"✅ Feedback exported to {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to export feedback: {e}")
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")

    def clear_feedback(self):
        """Clear all stored reinforcement feedback."""
        confirm = QMessageBox.question(self, "Confirm Clear", "Clear all feedback data?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self.engine.memory_data["reinforcement_feedback"] = {}
        self.engine.memory_data["prompt_scores"] = {}
        self.engine.save_memory()
        QMessageBox.information(self, "Cleared", "All feedback has been cleared.")
        self.load_feedback()
        self.feedback_details.clear()

    def auto_tune_prompts(self):
        """
        Auto-tune prompts based on feedback.
        Requires that the parent window has a 'prompt_manager' attribute.
        """
        try:
            prompt_manager = getattr(self.parent(), "prompt_manager", None)
            if not prompt_manager:
                raise ValueError("Prompt manager not found on parent.")
            self.engine.auto_tune_prompts(prompt_manager)
            QMessageBox.information(self, "Auto-Tune", "Prompts auto-tuned based on feedback.")
        except Exception as e:
            logger.error(f"❌ Auto-tuning failed: {e}")
            QMessageBox.critical(self, "Error", f"Auto-tuning failed:\n{e}")
