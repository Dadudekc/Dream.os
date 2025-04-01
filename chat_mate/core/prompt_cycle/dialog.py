from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget,
    QPushButton, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt

class PromptCycleDialog(QDialog):
    """
    Dialog for selecting prompts to include in the cycle.
    """
    def __init__(self, prompt_manager, start_cycle_callback):
        """
        :param prompt_manager: Manager that lists or retrieves available prompts.
        :param start_cycle_callback: Callback function that takes selected prompt names and begins the cycle.
        """
        super().__init__()
        self.prompt_manager = prompt_manager
        self.start_cycle_callback = start_cycle_callback

        self.setWindowTitle("Prompt Cycle Mode")
        self.setGeometry(200, 200, 400, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select prompts to include in the cycle:"))

        self.prompt_list_widget = QListWidget()
        self.prompt_list_widget.setSelectionMode(QListWidget.MultiSelection)

        # Load prompt types from the manager
        for prompt_type in self.prompt_manager.list_available_prompts():
            item = QListWidgetItem(prompt_type)
            self.prompt_list_widget.addItem(item)

        layout.addWidget(self.prompt_list_widget)

        start_button = QPushButton("Start Cycle")
        start_button.clicked.connect(self.start_cycle)
        layout.addWidget(start_button)

        self.setLayout(layout)

    def start_cycle(self):
        selected_prompts = [item.text() for item in self.prompt_list_widget.selectedItems()]
        if not selected_prompts:
            QMessageBox.warning(self, "No Prompts Selected", "Please select at least one prompt.")
            return

        self.start_cycle_callback(selected_prompts)
        self.accept() 
