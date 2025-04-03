import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt5.QtCore import pyqtSignal

# Custom imports
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic
from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow


class DreamscapeGUI(QWidget):
    append_output_signal = pyqtSignal(str)

    def __init__(self, ui_logic: DreamscapeUILogic):
        super().__init__()
        self.setWindowTitle("Digital Dreamscape Automation")
        self.setGeometry(100, 100, 800, 800)

        self.ui_logic = ui_logic

        self.main_window = DreamOsMainWindow(ui_logic=self.ui_logic)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.main_window)
        layout.addWidget(scroll)
        self.setLayout(layout)

        self.append_output_signal.connect(self.main_window.append_output)

    def closeEvent(self, event):
        self.ui_logic.shutdown()
        event.accept()
