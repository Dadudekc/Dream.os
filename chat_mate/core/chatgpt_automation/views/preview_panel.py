from PyQt5 import QtWidgets, QtCore

class PreviewPanel(QtWidgets.QWidget):
    # Define custom signals if you need to notify the MainWindow of events.
    fileProcessed = QtCore.pyqtSignal(str)
    fileSelfHealed = QtCore.pyqtSignal(str)
    testsRun = QtCore.pyqtSignal(str)
    
    def __init__(self, helpers, controller, parent=None):
        super().__init__(parent)
        self.helpers = helpers
        self.controller = controller
        self.current_file_path = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Editable file preview area
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setPlaceholderText("File preview will appear here...")
        layout.addWidget(self.preview)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.process_button = QtWidgets.QPushButton("Process File")
        self.process_button.clicked.connect(self.process_file)
        button_layout.addWidget(self.process_button)

        self.self_heal_button = QtWidgets.QPushButton("Self-Heal")
        self.self_heal_button.clicked.connect(self.self_heal_file)
        button_layout.addWidget(self.self_heal_button)

        self.run_tests_button = QtWidgets.QPushButton("Run Tests")
        self.run_tests_button.clicked.connect(self.run_tests)
        button_layout.addWidget(self.run_tests_button)

        layout.addLayout(button_layout)

        # Log output area
        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Log output will appear here...")
        layout.addWidget(self.log_output)

    def load_file(self, file_path):
        content = self.helpers.read_file(file_path)
        if content:
            self.preview.setPlainText(content)
            self.current_file_path = file_path
            self.log_output.append(f"Loaded: {file_path}")
        else:
            self.log_output.append(f"❌ Could not load file: {file_path}")

    def process_file(self):
        if not self.current_file_path:
            self.log_output.append("No file loaded.")
            return

        file_content = self.preview.toPlainText()
        result = self.controller.process_file(self.current_file_path, file_content)
        self.log_output.append(result)
        self.fileProcessed.emit(result)

    def self_heal_file(self):
        if not self.current_file_path:
            self.log_output.append("No file loaded.")
            return

        file_content = self.preview.toPlainText()
        result = self.controller.self_heal_file(self.current_file_path, file_content)
        self.log_output.append(result)
        self.fileSelfHealed.emit(result)

    def run_tests(self):
        if not self.current_file_path:
            self.log_output.append("No file loaded.")
            return

        result = self.controller.run_tests_on_file(self.current_file_path)
        self.log_output.append(result)
        self.testsRun.emit(result)
