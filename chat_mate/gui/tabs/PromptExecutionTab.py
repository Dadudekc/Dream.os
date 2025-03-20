from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox
from core.PromptCycleManager import PromptCycleManager
from core.AletheiaPromptManager import AletheiaPromptManager

class PromptExecutionTab(QWidget):
    def __init__(self, parent=None):  # ✅ Add parent param
        super().__init__(parent)       # ✅ Pass parent to QWidget constructor
        
        self.prompt_manager = AletheiaPromptManager()
        self.cycle_manager = PromptCycleManager(prompt_manager=self.prompt_manager)

        # Layout setup
        layout = QVBoxLayout()

        # Select Prompt label and combo box
        layout.addWidget(QLabel("Select Prompt:"))
        self.prompt_selector = QComboBox()
        self.prompt_selector.addItems(self.prompt_manager.list_prompts())
        self.prompt_selector.currentTextChanged.connect(self.load_prompt)
        layout.addWidget(self.prompt_selector)

        # Prompt editor area
        self.prompt_editor = QTextEdit()
        layout.addWidget(self.prompt_editor)

        # Execute button
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_prompt)
        layout.addWidget(execute_btn)

        # Apply layout to widget
        self.setLayout(layout)
    
    def load_prompt(self, prompt_name):
        prompt_text = self.prompt_manager.get_prompt(prompt_name)
        self.prompt_editor.setPlainText(prompt_text)  # ✅ Fixed variable name from `prompt` to `prompt_text`

    def execute_prompt(self):
        selected_prompt = self.prompt_editor.toPlainText()
        # ⚡ TODO: Implement actual execution logic here
        print(f"Executing Prompt:\n{selected_prompt}")  # Placeholder for logic feedback
