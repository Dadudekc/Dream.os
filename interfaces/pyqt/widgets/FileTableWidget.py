import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QTableWidgetItem, QComboBox, QPushButton, QMessageBox

class FileTableWidget(QtWidgets.QTableWidget):
    def __init__(self, helpers=None):
        super().__init__()
        self.helpers = helpers

        # Setup columns
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["File Path", "Line Count", "Model Selection", "Preview"])

        # Enable drag & drop for external files
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)

        # Stretch last column for UI balance
        self.horizontalHeader().setStretchLastSection(True)

        # Log output widget for external access
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)

    # ------------------------------
    # Drag & Drop Handlers
    # ------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isdir(file_path):
                    self.add_folder_files(file_path)
                elif file_path.endswith(".py"):
                    self.add_file(file_path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ------------------------------
    # Adding Files / Folders
    # ------------------------------
    def add_folder_files(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    self.add_file(full_path)

    def add_file(self, file_path):
        # Read file and calculate line count
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            line_count = len([line for line in lines if line.strip()])
        except Exception as e:
            self.log(f"❌ Failed to read file {file_path}: {e}")
            return

        # Insert new row
        row_position = self.rowCount()
        self.insertRow(row_position)

        # File Path Item
        self.setItem(row_position, 0, QTableWidgetItem(file_path))

        # Line Count Item
        self.setItem(row_position, 1, QTableWidgetItem(str(line_count)))

        # Model Selection ComboBox (customize list as needed)
        model_combo = QComboBox()
        model_combo.addItems(["o3mini", "o4", "o5"])  # Placeholder list
        self.setCellWidget(row_position, 2, model_combo)

        # Preview Button
        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(lambda _, r=row_position: self.preview_prompt(r))
        self.setCellWidget(row_position, 3, preview_button)

        self.log(f"✅ File added: {file_path} ({line_count} lines)")

    # ------------------------------
    # Preview Prompt
    # ------------------------------
    def preview_prompt(self, row):
        file_path_item = self.item(row, 0)
        if not file_path_item:
            return

        file_path = file_path_item.text()
        model_combo: QComboBox = self.cellWidget(row, 2)
        manual_model = model_combo.currentText() if model_combo else "Unknown"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            preview = (
                f"Preview for file: {file_path}\n"
                f"Selected Model: {manual_model}\n"
                f"---\n"
                f"{content[:300]}{'...' if len(content) > 300 else ''}"
            )

            QMessageBox.information(self, "Prompt Preview", preview)
            self.log(f"🔍 Preview generated for {file_path}")
        except Exception as e:
            self.log(f"❌ Error generating preview for {file_path}: {e}")

    # ------------------------------
    # File Selection
    # ------------------------------
    def get_selected_files(self):
        selected_rows = self.selectionModel().selectedRows()
        return [self.item(row.row(), 0).text() for row in selected_rows if self.item(row.row(), 0)]

    # ------------------------------
    # Get All Files from the Table
    # ------------------------------
    def get_all_files(self):
        files = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item is not None:
                files.append(item.text())
        return files

    # ------------------------------
    # File Processing (Placeholder)
    # ------------------------------
    def start_processing(self):
        if self.rowCount() == 0:
            QMessageBox.warning(self, "No Files", "Please add .py files to process.")
            return

        self.log("🚀 Starting file processing...")

        for row in range(self.rowCount()):
            file_path = self.item(row, 0).text()
            model_combo: QComboBox = self.cellWidget(row, 2)
            manual_model = model_combo.currentText() if model_combo else "Unknown"

            # Placeholder for processing logic
            self.log(f"⚙️ Processing: {file_path} with model {manual_model}")

        self.log("✅ All files processed.")

    # ------------------------------
    # Logging Helper
    # ------------------------------
    def log(self, message):
        self.log_output.appendPlainText(message)
        if self.helpers:
            self.helpers.update_status_bar(self.window(), message)
            self.helpers.logger.info(message)
