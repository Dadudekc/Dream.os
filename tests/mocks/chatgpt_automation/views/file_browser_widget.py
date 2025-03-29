"""Mock implementation of FileBrowserWidget."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton

class FileBrowserWidget(QWidget):
    """Mock FileBrowserWidget class."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the mock widget."""
        super().__init__()
        self.layout = QVBoxLayout()
        self.path_input = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.layout.addWidget(self.path_input)
        self.layout.addWidget(self.browse_button)
        self.setLayout(self.layout)
        
    def get_path(self):
        """Get the current path."""
        return self.path_input.text()
    
    def set_path(self, path):
        """Set the current path."""
        self.path_input.setText(path) 