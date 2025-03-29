import os
import subprocess
import time
from PyQt5 import QtWidgets, QtCore
from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.services.OpenAIClient import OpenAIClient  # Use the new client class

class SelfHealController:
    """
    Controller class encapsulating the self-healing logic.
    Contains methods for running and validating a file, reading/saving files,
    and executing auto-retry logic.
    """
    def __init__(self, client: OpenAIClient, helpers: GuiHelpers, max_retries=5):
        self.client = client
        self.helpers = helpers
        self.max_retries = max_retries

    def run_and_validate(self, file_path, cancelled_flag_callback):
        """
        Synchronously runs and validates a file self-heal.
        :param file_path: Path to the file to process.
        :param cancelled_flag_callback: Function that returns True if cancellation is requested.
        :return: Boolean indicating success.
        """
        retries = 0
        while retries < self.max_retries and not cancelled_flag_callback():
            self.helpers.logger.info(f"▶️ Attempt {retries + 1} running {file_path}...")
            result = subprocess.run(["python", file_path], capture_output=True, text=True)
            if result.returncode == 0:
                self.helpers.logger.info(f"✅ {file_path} ran successfully!")
                return True
            else:
                error_msg = result.stderr
                self.helpers.logger.warning(f"❌ Execution failed for {file_path}: {error_msg}")
                file_content = self.read_file(file_path)
                if not file_content:
                    self.helpers.logger.error(f"🚫 Unable to read {file_path}")
                    return False

                prompt = (
                    "This file failed to run. Here's the code and the error. "
                    "Please fix it and show me the complete updated version.\n\n"
                    "--- CODE ---\n"
                    f"{file_content}\n\n"
                    "--- ERROR ---\n"
                    f"{error_msg}"
                )
                self.helpers.logger.info("📤 Sending prompt to ChatGPT...")
                response = self.client.get_chatgpt_response(prompt)
                if response:
                    self.helpers.logger.info("📥 Received response, saving updated code...")
                    saved = self.save_file(file_path, response)
                    if not saved:
                        self.helpers.logger.error("🚫 Failed to save the updated code.")
                        return False
                else:
                    self.helpers.logger.error("🚫 No valid response from ChatGPT.")
                    return False

                retries += 1
                time.sleep(1)

        if cancelled_flag_callback():
            self.helpers.logger.info(f"⏹️ {file_path} cancelled by user.")
            return False

        self.helpers.logger.warning(f"🚫 Max retries reached for {file_path}.")
        return False

    def read_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.helpers.logger.error(f"❌ Failed to read {file_path}: {e}")
            return None

    def save_file(self, file_path, content):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            self.helpers.logger.error(f"❌ Failed to save {file_path}: {e}")
            return False

class SelfHealRunner(QtWidgets.QWidget):
    log_signal = QtCore.pyqtSignal(str)      # For log messages
    progress_signal = QtCore.pyqtSignal(int)   # For updating progress bar

    def __init__(self, helpers: GuiHelpers, client: OpenAIClient, max_retries=5):
        """
        Initialize SelfHealRunner widget.

        Args:
            helpers (GuiHelpers): Utility helper instance for status updates.
            client (OpenAIClient): An instance of OpenAIClient for ChatGPT interactions.
            max_retries (int): Maximum number of self-heal attempts per file.
        """
        super().__init__()
        self.helpers = helpers
        self.client = client
        self.max_retries = max_retries

        # Instantiate the controller to handle business logic.
        self.controller = SelfHealController(client, helpers, max_retries)

        self.threadpool = QtCore.QThreadPool()
        self.cancelled = False   # Cancellation flag
        self.total_tasks = 0     # Total files to process
        self.completed_tasks = 0 # Count of files processed

        self.init_ui()
        self.log_signal.connect(self.log)
        self.progress_signal.connect(self.update_progress_bar)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # File Selection (Multi-file)
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        layout.addWidget(self.file_list)

        # Add Files Button
        add_files_btn = QtWidgets.QPushButton("Add Files")
        add_files_btn.clicked.connect(self.add_files)
        layout.addWidget(add_files_btn)

        # Button Controls for Self-Heal
        btn_layout = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start Self-Healing")
        self.start_btn.clicked.connect(self.start_self_heal)
        btn_layout.addWidget(self.start_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_self_heal)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Global Progress Bar for self-heal tasks
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("No tasks started.")
        layout.addWidget(self.progress_bar)

        # Log Output
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Removed setup_status_bar() call since SelfHealRunner is a QWidget, not a QMainWindow.
        self.helpers.update_status_bar(self, "Self-Heal Ready")

    def add_files(self):
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select Python Files", "", "Python Files (*.py)"
        )
        for path in file_paths:
            self.file_list.addItem(path)
        self.log_signal.emit(f"✅ Added files: {len(file_paths)}")

    def start_self_heal(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(
                self, "No Selection", "Please select one or more files to self-heal."
            )
            return

        # Reset cancellation flag and progress counters
        self.cancelled = False
        self.completed_tasks = 0
        self.total_tasks = len(selected_items)
        self.progress_bar.setMaximum(self.total_tasks)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0 / {} files processed".format(self.total_tasks))
        self.cancel_btn.setEnabled(True)
        self.start_btn.setEnabled(False)

        self.log_signal.emit("🚀 Starting Self-Heal on selected files...")
        for item in selected_items:
            file_path = item.text()
            worker = SelfHealWorker(file_path, self.controller, self)
            self.threadpool.start(worker)

    def cancel_self_heal(self):
        self.cancelled = True
        self.log_signal.emit("⏹️ Cancellation requested. Aborting remaining tasks...")
        self.cancel_btn.setEnabled(False)

    def log(self, message):
        self.log_output.appendPlainText(message)
        self.helpers.update_status_bar(self, message)
        self.helpers.logger.info(message)

    def update_progress_bar(self, value):
        # 'value' here is an integer representing the new progress value.
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value} / {self.total_tasks} files processed")
        if value >= self.total_tasks:
            self.cancel_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.helpers.update_status_bar(self, "Self-Heal Complete")

class SelfHealWorker(QtCore.QRunnable):
    """
    QRunnable to process self-healing of a single file in the background.
    Checks for cancellation requests before and during processing.
    """
    def __init__(self, file_path, controller: SelfHealController, runner_widget: SelfHealRunner):
        super().__init__()
        self.file_path = file_path
        self.controller = controller
        self.runner_widget = runner_widget

    def run(self):
        # Check cancellation before starting.
        if self.runner_widget.cancelled:
            self.runner_widget.log_signal.emit(f"⏹️ Skipping {self.file_path} due to cancellation.")
            self._update_progress()
            return

        self.runner_widget.log_signal.emit(f"⚙️ Processing: {self.file_path}")
        success = self.controller.run_and_validate(self.file_path, lambda: self.runner_widget.cancelled)
        if success:
            self.runner_widget.log_signal.emit(f"✅ Self-Heal succeeded for {self.file_path}")
        else:
            self.runner_widget.log_signal.emit(f"🚫 Self-Heal failed for {self.file_path}")
        self._update_progress()

    def _update_progress(self):
        # Update the global progress.
        self.runner_widget.completed_tasks += 1
        # Emit the new progress value via the progress signal.
        self.runner_widget.progress_signal.emit(self.runner_widget.completed_tasks)

# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Create an OpenAIClient instance with your desired profile_dir.
    client = OpenAIClient(profile_dir="your_profile_dir", headless=False)
    window = SelfHealRunner(helpers=GuiHelpers(), client=client)
    window.show()
    sys.exit(app.exec_())
