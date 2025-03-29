from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt


class ExclusionsDialog(QDialog):
    """
    Dialog window for managing excluded items (chats, users, etc.)
    """
    def __init__(self, parent=None, exclusions_list=None):
        super().__init__(parent)
        self.setWindowTitle("Exclusions Manager")
        self.setModal(True)
        self.setMinimumSize(400, 300)

        self.exclusions_list = exclusions_list if exclusions_list is not None else []

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # --- List Widget for Exclusions ---
        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(QLabel("Current Exclusions:"))
        layout.addWidget(self.list_widget)

        # --- Input Field & Add Button ---
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter exclusion item...")
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_exclusion)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(add_button)
        layout.addLayout(input_layout)

        # --- Remove Button ---
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected)
        layout.addWidget(remove_button)

        # --- Close Button ---
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def refresh_list(self):
        """
        Refresh the list widget to show current exclusions.
        """
        self.list_widget.clear()
        for item in self.exclusions_list:
            self.list_widget.addItem(str(item))

    def add_exclusion(self):
        """
        Add an item to the exclusion list.
        """
        new_item = self.input_field.text().strip()
        if not new_item:
            QMessageBox.warning(self, "Warning", "You must enter a value.")
            return
        if new_item in self.exclusions_list:
            QMessageBox.information(self, "Info", "Item already excluded.")
            return

        self.exclusions_list.append(new_item)
        self.refresh_list()
        self.input_field.clear()

    def remove_selected(self):
        """
        Remove the selected item from the exclusion list.
        """
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Select an item to remove.")
            return

        for item in selected_items:
            item_text = item.text()
            if item_text in self.exclusions_list:
                self.exclusions_list.remove(item_text)

        self.refresh_list()

    def get_exclusions(self):
        """
        Return the updated exclusions list.
        """
        return self.exclusions_list

