"""Mock implementation of GuiHelpers."""

class GuiHelpers:
    """Mock GuiHelpers class."""
    
    @staticmethod
    def create_button(*args, **kwargs):
        """Mock create_button method."""
        from PyQt5.QtWidgets import QPushButton
        return QPushButton(*args)
    
    @staticmethod
    def create_label(*args, **kwargs):
        """Mock create_label method."""
        from PyQt5.QtWidgets import QLabel
        return QLabel(*args)
    
    @staticmethod
    def create_text_edit(*args, **kwargs):
        """Mock create_text_edit method."""
        from PyQt5.QtWidgets import QTextEdit
        return QTextEdit(*args)
    
    @staticmethod
    def create_line_edit(*args, **kwargs):
        """Mock create_line_edit method."""
        from PyQt5.QtWidgets import QLineEdit
        return QLineEdit(*args)
    
    @staticmethod
    def create_combo_box(*args, **kwargs):
        """Mock create_combo_box method."""
        from PyQt5.QtWidgets import QComboBox
        return QComboBox(*args)
    
    @staticmethod
    def create_checkbox(*args, **kwargs):
        """Mock create_checkbox method."""
        from PyQt5.QtWidgets import QCheckBox
        return QCheckBox(*args)
    
    @staticmethod
    def create_list_widget(*args, **kwargs):
        """Mock create_list_widget method."""
        from PyQt5.QtWidgets import QListWidget
        return QListWidget(*args) 