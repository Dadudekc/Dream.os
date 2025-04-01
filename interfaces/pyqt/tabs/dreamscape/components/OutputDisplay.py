from typing import Optional, Callable
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QGroupBox,
    QFileDialog, QMessageBox
)

class OutputDisplay(QWidget):
    """Widget for displaying and managing generated episode output."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the output display widget."""
        super().__init__(parent)
        self._initialize_ui_elements()
        self._build_ui()

    def _initialize_ui_elements(self) -> None:
        """Initialize all UI element references."""
        # Output display
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)

        # Save buttons
        self.save_txt_btn = QPushButton("Save as TXT")
        self.save_md_btn = QPushButton("Save as MD")

    def _build_ui(self) -> None:
        """Build the UI layout."""
        layout = QVBoxLayout()
        
        # Output display
        layout.addWidget(self.output_text)
        
        # Save buttons
        save_layout = QHBoxLayout()
        save_layout.addWidget(self.save_txt_btn)
        save_layout.addWidget(self.save_md_btn)
        layout.addLayout(save_layout)
        
        self.setLayout(layout)

    def bind_events(self, 
                   on_save_txt: Callable[[], None],
                   on_save_md: Callable[[], None]) -> None:
        """
        Bind event handlers to the controls.
        
        Args:
            on_save_txt: Callback for save as TXT button click
            on_save_md: Callback for save as MD button click
        """
        self.save_txt_btn.clicked.connect(on_save_txt)
        self.save_md_btn.clicked.connect(on_save_md)

    def append_log(self, message: str) -> None:
        """
        Append a log message to the output display.
        
        Args:
            message: Message to append
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.output_text.append(formatted_message)

    def set_content(self, content: str) -> None:
        """
        Set the content of the output display.
        
        Args:
            content: Content to display
        """
        self.output_text.setPlainText(content)

    def get_content(self) -> str:
        """
        Get the current content of the output display.
        
        Returns:
            str: Current content
        """
        return self.output_text.toPlainText()

    def clear(self) -> None:
        """Clear the output display."""
        self.output_text.clear()

    def save_content(self, file_format: str = 'txt') -> bool:
        """
        Save the current content to a file.
        
        Args:
            file_format: Format to save as ('txt' or 'md')
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            content = self.get_content()
            if not content:
                QMessageBox.warning(self, "Save Error", "No content to save")
                return False

            file_filter = "Text files (*.txt)" if file_format == 'txt' else "Markdown files (*.md)"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Output",
                "",
                file_filter
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
                
            return False
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file: {str(e)}")
            return False 
