import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from .preview_panel import PreviewPanel
from ..widgets.file_browser_widget import FileBrowserWidget  # Make sure FileBrowserWidget emits a signal on double-click.
from core.chatgpt_automation.controllers.automation_controller import AutomationController
from interfaces.pyqt.GuiHelpers import GuiHelpers

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatGPT Automation - Unified Interface")
        self.resize(1200, 800)
        self.helpers = GuiHelpers()
        self.controller = AutomationController(self.helpers)
        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        # Left Sidebar Layout (File Browser + Assistant Toggle)
        sidebar_layout = QtWidgets.QVBoxLayout()
        self.file_browser = FileBrowserWidget(helpers=self.helpers)
        self.file_browser.fileDoubleClicked.connect(self.load_file_into_preview)
        sidebar_layout.addWidget(self.file_browser)

        self.assistant_toggle = AssistantModeToggleWidget()
        sidebar_layout.addWidget(self.assistant_toggle)

        sidebar_container = QtWidgets.QWidget()
        sidebar_container.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar_container, 1)

        # Right: Preview Panel
        self.preview_panel = PreviewPanel(self.helpers, self.controller)
        main_layout.addWidget(self.preview_panel, 3)

        self.statusBar().showMessage("Ready")


    def load_file_into_preview(self, file_path):
        self.preview_panel.load_file(file_path)
        self.statusBar().showMessage(f"Loaded: {file_path}")

    def closeEvent(self, event):
        self.statusBar().showMessage("Shutting down...")
        self.controller.shutdown()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    splash_pix = QtGui.QPixmap("chatgpt_automation/logo.webp")
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()
    QtCore.QThread.sleep(2)
    window = MainWindow()
    window.show()
    splash.finish(window)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
