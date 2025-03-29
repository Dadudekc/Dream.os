import os
from PyQt5 import QtWidgets
from core.chatgpt_automation.setup_logging import setup_logging

class GuiHelpers:
    """
    Utility class for managing GUI-related helpers.
    Handles status bars, file operations, logging, and dialogs.
    """

    def __init__(self, log_name="gui_helpers", log_subdir="social"):
        # Initialize logger
        log_dir = os.path.join(os.getcwd(), "logs", log_subdir)
        self.logger = setup_logging(log_name, log_dir=log_dir)
        self.logger.info("✅ GuiHelpers initialized.")

    # -------------------------------
    # STATUS BAR HANDLING
    # -------------------------------
    def setup_status_bar(self, window):
        """
        Initialize and return a status bar for the given QMainWindow.
        """
        if not hasattr(window, 'status_bar'):
            window.status_bar = window.statusBar()
            window.status_bar.showMessage("Ready")
            self.logger.info("✅ Status bar initialized.")
        return window.status_bar

    def update_status_bar(self, window, message, timeout=5000):
        """
        Update the status bar message for a set duration.
        """
        if hasattr(window, 'status_bar'):
            window.status_bar.showMessage(message, timeout)
            self.logger.info(f"✅ Status bar updated: {message}")

    # -------------------------------
    # LOGGING UTILITIES
    # -------------------------------
    def log_to_output(self, log_widget, message, logger_func=None):
        """
        Append log message to a QTextEdit/QPlainTextEdit widget and optionally log to file/console.
        """
        if log_widget:
            log_widget.appendPlainText(message)

        if logger_func:
            logger_func(message)
        else:
            self.logger.info(message)

    # -------------------------------
    # FILE HELPERS
    # -------------------------------
    def read_file(self, file_path):
        """
        Read a file and return its contents.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.logger.info(f"✅ Read file: {file_path}")
            return content
        except Exception as e:
            self.logger.error(f"❌ Failed to read file {file_path}: {e}")
            return None

    def save_file(self, file_path, content):
        """
        Save content to a file.
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"✅ File saved: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to save file {file_path}: {e}")
            return False

    # -------------------------------
    # CONFIRMATION & ALERTS
    # -------------------------------
    def show_info(self, message, title="Info"):
        """
        Show an informational dialog box.
        """
        QtWidgets.QMessageBox.information(None, title, message)

    def show_warning(self, message, title="Warning"):
        """
        Show a warning dialog box.
        """
        QtWidgets.QMessageBox.warning(None, title, message)

    def show_error(self, message, title="Error"):
        """
        Show an error dialog box.
        """
        QtWidgets.QMessageBox.critical(None, title, message)

    def confirm_action(self, message, title="Confirm"):
        """
        Show a Yes/No confirmation dialog and return True/False.
        """
        reply = QtWidgets.QMessageBox.question(
            None, title, message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        return reply == QtWidgets.QMessageBox.Yes
