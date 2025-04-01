from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QTextEdit, QListWidget,
    QListWidgetItem, QComboBox, QCheckBox, QStackedWidget,
    QInputDialog
)
from PyQt5.QtCore import pyqtSlot

class PromptExecutionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Exclusion List Group
        layout.addWidget(self._create_exclusion_group())

        # Prompt Controls Group
        layout.addWidget(self._create_prompt_controls_group())

        self.setLayout(layout)

    def _create_exclusion_group(self):
        group = QGroupBox("Prompts")
        layout = QVBoxLayout()

        self.exclusion_list = QListWidget()
        layout.addWidget(QLabel("Excluded Chats"))
        layout.addWidget(self.exclusion_list)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Exclusion")
        btn_add.clicked.connect(self.add_exclusion)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self.remove_exclusion)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        layout.addLayout(btn_layout)

        group.setLayout(layout)
        return group

    def _create_prompt_controls_group(self):
        group = QGroupBox("Prompt Execution Controls")
        layout = QVBoxLayout()

        # Prompt Type Selector
        layout.addWidget(QLabel("Select Prompt Type:"))
        self.prompt_selector = QComboBox()
        self.prompt_selector.addItems(["Default", "Custom", "Community"])
        layout.addWidget(self.prompt_selector)

        # Prompt Stack
        self.prompt_stack = QStackedWidget()
        self.prompt_editor = QTextEdit()
        self.prompt_cycle_list = QListWidget()
        self.prompt_stack.addWidget(self.prompt_editor)
        self.prompt_stack.addWidget(self.prompt_cycle_list)
        layout.addWidget(QLabel("Prompt Input:"))
        layout.addWidget(self.prompt_stack)

        # Mode Selection
        mode_layout = QHBoxLayout()
        self.execution_mode_combo = QComboBox()
        self.execution_mode_combo.addItems(["Direct Execution", "Prompt Cycle Mode"])
        self.execution_mode_combo.currentTextChanged.connect(self.update_execution_mode)
        mode_layout.addWidget(QLabel("Execution Mode:"))
        mode_layout.addWidget(self.execution_mode_combo)
        layout.addLayout(mode_layout)

        # Chat Mode Toggle
        self.mode_toggle_btn = QPushButton("Switch to New Chat Mode")
        self.chat_mode_label = QLabel("Current Mode: Chat History")
        layout.addWidget(self.mode_toggle_btn)
        layout.addWidget(self.chat_mode_label)

        # Checkboxes
        checkbox_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("Run Headless Browser")
        self.reverse_checkbox = QCheckBox("Process in Reverse Order")
        self.archive_checkbox = QCheckBox("Archive Chats")
        checkbox_layout.addWidget(self.headless_checkbox)
        checkbox_layout.addWidget(self.reverse_checkbox)
        checkbox_layout.addWidget(self.archive_checkbox)
        layout.addLayout(checkbox_layout)

        # Execute Button
        self.execute_prompt_btn = QPushButton("Execute Prompt")
        layout.addWidget(self.execute_prompt_btn)

        # Save/Reset Buttons
        btn_layout = QHBoxLayout()
        self.save_prompt_btn = QPushButton("Save Prompt")
        self.reset_prompts_btn = QPushButton("Reset Prompts")
        btn_layout.addWidget(self.save_prompt_btn)
        btn_layout.addWidget(self.reset_prompts_btn)
        layout.addLayout(btn_layout)

        # Generate Dreamscape Button
        btn_generate_dreamscape = QPushButton("Generate Dreamscape Episodes")
        layout.addWidget(btn_generate_dreamscape)

        group.setLayout(layout)
        return group

    def add_exclusion(self):
        chat_title, ok = QInputDialog.getText(self, "Add Exclusion", "Enter chat title to exclude:")
        if ok and chat_title.strip():
            self.exclusion_list.addItem(QListWidgetItem(chat_title.strip()))

    def remove_exclusion(self):
        selected_items = self.exclusion_list.selectedItems()
        for item in selected_items:
            self.exclusion_list.takeItem(self.exclusion_list.row(item))

    def get_excluded_chats(self):
        return [self.exclusion_list.item(i).text() for i in range(self.exclusion_list.count())]

    def update_execution_mode(self, mode_text: str):
        if mode_text == "Prompt Cycle Mode":
            self.prompt_stack.setCurrentIndex(1)
            self.execute_prompt_btn.setText("Start Prompt Cycle")
        else:
            self.prompt_stack.setCurrentIndex(0)
            self.execute_prompt_btn.setText("Execute Prompt")
            
    @pyqtSlot(dict)
    def load_prompt(self, prompt_data: dict):
        """Load a prompt from the prompt manager into the execution tab."""
        if not prompt_data:
            return
            
        # Set the prompt text
        prompt_text = prompt_data.get("text", "")
        self.prompt_editor.setPlainText(prompt_text)
        
        # Set prompt type if available
        prompt_type = prompt_data.get("type", "Default")
        index = self.prompt_selector.findText(prompt_type)
        if index >= 0:
            self.prompt_selector.setCurrentIndex(index)
            
        # Check if it's a cycle prompt
        if prompt_data.get("is_cycle", False):
            self.execution_mode_combo.setCurrentText("Prompt Cycle Mode")
            
            # Clear and populate cycle list
            self.prompt_cycle_list.clear()
            for item in prompt_data.get("cycle_items", []):
                self.prompt_cycle_list.addItem(QListWidgetItem(item))
        else:
            self.execution_mode_combo.setCurrentText("Direct Execution")
            
        # Update UI based on the loaded prompt
        self.update_execution_mode(self.execution_mode_combo.currentText()) 
