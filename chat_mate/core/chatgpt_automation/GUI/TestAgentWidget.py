import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHBoxLayout, QListWidgetItem

class TestAgentWidget(QtWidgets.QWidget):
    """
    Widget to select one or more Python files (or folders), generate tests using ChatGPT (or LLM),
    and run those tests.

    NOW WITH MULTI-FILE & FOLDER DRAG-AND-DROP SUPPORT!
    """
    def __init__(self, helpers, engine):
        super().__init__()
        self.helpers = helpers
        self.engine = engine
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # File selection layout with drag-and-drop enabled
        file_select_layout = QHBoxLayout()

        self.file_list = FileDropListWidget(self)
        self.file_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.file_list.files_dropped.connect(self.on_files_dropped)

        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_files)

        file_select_layout.addWidget(self.file_list)
        file_select_layout.addWidget(browse_btn)
        layout.addLayout(file_select_layout)

        # Generate and Run Tests button
        self.run_tests_btn = QtWidgets.QPushButton("Generate and Run Tests")
        self.run_tests_btn.clicked.connect(self.run_tests)
        layout.addWidget(self.run_tests_btn)

        # Log output area
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

    def browse_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select Python Files", "", "Python Files (*.py)"
        )
        if files:
            self.add_files(files)

    def on_files_dropped(self, file_paths):
        """Triggered when files/folders are dropped into the file_list widget."""
        self.log(f"📥 Dropped: {file_paths}")
        self.add_files(file_paths)

    def add_files(self, files):
        """Add files to the list, avoiding duplicates."""
        existing_files = {self.file_list.item(i).text() for i in range(self.file_list.count())}
        for file_path in files:
            if file_path not in existing_files and file_path.endswith('.py'):
                item = QListWidgetItem(file_path)
                self.file_list.addItem(item)
            elif os.path.isdir(file_path):
                # Recursively add all Python files from folders
                for root, _, filenames in os.walk(file_path):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            full_path = os.path.join(root, filename)
                            if full_path not in existing_files:
                                item = QListWidgetItem(full_path)
                                self.file_list.addItem(item)

    def run_tests(self):
        count = self.file_list.count()

        if count == 0:
            self.helpers.show_warning("Please select at least one file.", "No Files Selected")
            return

        file_paths = [self.file_list.item(i).text() for i in range(count)]

        self.run_tests_btn.setEnabled(False)
        self.log(f"🚀 Starting test generation and execution for {count} files...")

        for file_path in file_paths:
            if not os.path.exists(file_path):
                self.log(f"❌ File not found: {file_path}")
                continue

            try:
                from GUI.TestAgent import TestAgent
                test_agent = TestAgent(driver=self.engine.driver, helpers=self.helpers)

                self.helpers.update_status_bar(self.window(), f"Running tests for {file_path}...")

                success, output = test_agent.run_full_test_cycle(file_path)

                status = "✅ Success!" if success else "❌ Failure!"
                self.log(f"{status}: {file_path}\n{output}\n\n")

            except Exception as e:
                self.log(f"❌ Error during test cycle for {file_path}:\n{e}")

        self.run_tests_btn.setEnabled(True)
        self.helpers.update_status_bar(self.window(), "Ready")

    def log(self, message):
        self.log_output.appendPlainText(message)
        self.helpers.logger.info(message)


class FileDropListWidget(QtWidgets.QListWidget):
    """
    QListWidget subclass that accepts drag-and-drop file/folder paths.
    Emits files_dropped signal with a list of the dropped paths.
    """
    files_dropped = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if self._has_valid_files(mime):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        files = []

        # Handle external files (URLs)
        if mime.hasUrls():
            files.extend([
                url.toLocalFile()
                for url in mime.urls()
                if url.isLocalFile() and (url.toLocalFile().endswith('.py') or os.path.isdir(url.toLocalFile()))
            ])

        # Handle internal drags (MIME text)
        if mime.hasText():
            # Split multiple file paths by newline or semicolon if needed
            text_paths = mime.text().splitlines()
            files.extend([
                path for path in text_paths
                if (path.endswith('.py') and os.path.exists(path)) or os.path.isdir(path)
            ])

        if files:
            self.files_dropped.emit(files)

        event.acceptProposedAction()

    def _has_valid_files(self, mime):
        # Check for URLs
        if mime.hasUrls():
            for url in mime.urls():
                local_path = url.toLocalFile()
                if (local_path.endswith('.py') and os.path.isfile(local_path)) or os.path.isdir(local_path):
                    return True
        # Check for text (internal drags)
        if mime.hasText():
            paths = mime.text().splitlines()
            for path in paths:
                if (path.endswith('.py') and os.path.exists(path)) or os.path.isdir(path):
                    return True
        return False
