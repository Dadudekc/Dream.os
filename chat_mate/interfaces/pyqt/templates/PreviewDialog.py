import os
import shutil
import difflib
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPlainTextEdit, QHBoxLayout,
    QPushButton, QMessageBox, QLabel, QCheckBox, QFileDialog, QTextEdit
)

class PythonSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(Qt.darkBlue)
        keyword_format.setFontWeight(QtGui.QFont.Bold)
        keywords = [
            'def', 'class', 'if', 'else', 'elif', 'try', 'except', 'while', 'for',
            'return', 'import', 'from', 'as', 'pass', 'break', 'continue', 'with', 'lambda'
        ]
        for word in keywords:
            pattern = QtCore.QRegExp(f"\\b{word}\\b")
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Strings
        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(Qt.darkGreen)
        self.highlighting_rules.append((QtCore.QRegExp(r'".*"'), string_format))
        self.highlighting_rules.append((QtCore.QRegExp(r"'.*'"), string_format))
        
        # Comments
        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(Qt.gray)
        self.highlighting_rules.append((QtCore.QRegExp(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

class PreviewDialog(QDialog):
    def __init__(self, file_path, updated_content, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.updated_content = updated_content
        self.backup_dir = "backups"
        
        self.setWindowTitle(f"Preview / Override - {os.path.basename(file_path)}")
        self.resize(1200, 800)

        # Layouts
        self.layout = QVBoxLayout(self)
        self.btn_layout = QHBoxLayout()
        self.diff_layout = QHBoxLayout()

        # File Name Display
        self.label = QLabel(f"Editing: {self.file_path}")
        self.layout.addWidget(self.label)

        # Before Editor (Read-only)
        self.before_editor = QPlainTextEdit(self)
        self.before_editor.setPlainText(self.read_file(self.file_path))
        self.before_editor.setReadOnly(True)
        PythonSyntaxHighlighter(self.before_editor.document())
        self.diff_layout.addWidget(self.before_editor)

        # After Editor (Editable)
        self.after_editor = QPlainTextEdit(self)
        self.after_editor.setPlainText(self.updated_content)
        PythonSyntaxHighlighter(self.after_editor.document())
        self.diff_layout.addWidget(self.after_editor)

        self.layout.addLayout(self.diff_layout)

        # Buttons
        self.save_btn = QPushButton("💾 Save Override", self)
        self.save_as_btn = QPushButton("📂 Save As", self)
        self.copy_btn = QPushButton("📋 Copy to Clipboard", self)
        self.diff_btn = QPushButton("🧮 Show Diff", self)
        self.word_wrap_chk = QCheckBox("Word Wrap")
        self.word_wrap_chk.setChecked(True)
        self.cancel_btn = QPushButton("❌ Cancel", self)

        # Add buttons to layout
        self.btn_layout.addWidget(self.save_btn)
        self.btn_layout.addWidget(self.save_as_btn)
        self.btn_layout.addWidget(self.copy_btn)
        self.btn_layout.addWidget(self.diff_btn)
        self.btn_layout.addWidget(self.word_wrap_chk)
        self.btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.btn_layout)

        # Connections
        self.save_btn.clicked.connect(self.save_override)
        self.save_as_btn.clicked.connect(self.save_as)
        self.cancel_btn.clicked.connect(self.reject)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.word_wrap_chk.toggled.connect(self.toggle_word_wrap)
        self.diff_btn.clicked.connect(self.show_diff)

        # Initial Settings
        self.after_editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.before_editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.after_editor.setFocus()

        # Tab Order
        self.setTabOrder(self.save_btn, self.save_as_btn)
        self.setTabOrder(self.save_as_btn, self.copy_btn)
        self.setTabOrder(self.copy_btn, self.diff_btn)
        self.setTabOrder(self.diff_btn, self.cancel_btn)

    def save_override(self):
        new_content = self.after_editor.toPlainText()

        label, ok = QtWidgets.QInputDialog.getText(self, "File Label", "Enter label for file (optional):")
        if ok and label:
            output_file = self.file_path.replace(".py", f"_{label}.py")
        else:
            output_file = self.file_path.replace(".py", "_refactored.py")

        try:
            self.backup_file(self.file_path)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            self.show_message("Saved", f"Override saved successfully as:\n{output_file}")
            self.accept()

        except Exception as e:
            self.show_message("Error", f"Failed to save override:\n{e}", error=True)

    def save_as(self):
        new_content = self.after_editor.toPlainText()
        output_file, _ = QFileDialog.getSaveFileName(self, "Save As", self.file_path, "Python Files (*.py)")
        if not output_file:
            return
        try:
            self.backup_file(self.file_path)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            self.show_message("Saved", f"Override saved successfully as:\n{output_file}")
            self.accept()

        except Exception as e:
            self.show_message("Error", f"Failed to save override:\n{e}", error=True)

    def backup_file(self, original_file):
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        base_name = os.path.basename(original_file)
        backup_file_path = os.path.join(self.backup_dir, base_name)

        version = 1
        while os.path.exists(backup_file_path):
            backup_file_path = os.path.join(self.backup_dir, f"{base_name}_v{version}")
            version += 1

        shutil.copy2(original_file, backup_file_path)
        self.show_message("Backup Created", f"Backup saved at:\n{backup_file_path}")

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.after_editor.toPlainText())
        self.show_message("Copied", "Content copied to clipboard.")

    def toggle_word_wrap(self, checked):
        mode = QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap
        self.after_editor.setLineWrapMode(mode)
        self.before_editor.setLineWrapMode(mode)

    def show_message(self, title, message, error=False):
        if error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def read_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.show_message("Error", f"Failed to read original file:\n{e}", error=True)
            return ""

    def show_diff(self):
        before = self.before_editor.toPlainText().splitlines()
        after = self.after_editor.toPlainText().splitlines()
        diff = difflib.unified_diff(before, after, fromfile='Original', tofile='Updated', lineterm='')
        diff_output = "\n".join(diff)

        diff_dialog = QDialog(self)
        diff_dialog.setWindowTitle("File Differences")
        diff_dialog.resize(800, 600)
        layout = QVBoxLayout(diff_dialog)

        diff_text = QTextEdit(diff_dialog)
        diff_text.setPlainText(diff_output)
        diff_text.setReadOnly(True)

        layout.addWidget(diff_text)

        close_btn = QPushButton("Close", diff_dialog)
        close_btn.clicked.connect(diff_dialog.accept)
        layout.addWidget(close_btn)

        diff_dialog.exec_()

