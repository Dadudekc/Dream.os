from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, 
    QApplication, QMainWindow
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

class SplashScreen(QMainWindow):
    mode_selected = pyqtSignal(str)  # Signal to emit when a mode is selected

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatMate - Mode Selection")
        self.setFixedSize(600, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #2c3e50;
                font-size: 24px;
                font-weight: bold;
                margin: 20px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 5px;
                margin: 10px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2472a4;
            }
        """)
        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        # Title
        title = QLabel("Welcome to ChatMate")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Choose your preferred interface")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        layout.addWidget(subtitle)

        # Add some spacing
        layout.addSpacing(40)

        # GUI Mode Button
        gui_btn = QPushButton("Desktop Interface")
        gui_btn.clicked.connect(lambda: self.mode_selected.emit("gui"))
        layout.addWidget(gui_btn, alignment=Qt.AlignCenter)

        # Web Mode Button
        web_btn = QPushButton("Web Dashboard")
        web_btn.clicked.connect(lambda: self.mode_selected.emit("web"))
        layout.addWidget(web_btn, alignment=Qt.AlignCenter)

        # Add some spacing
        layout.addSpacing(40)

        # Version info
        version = QLabel("v1.0.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #95a5a6; font-size: 12px;")
        layout.addWidget(version)

def show_splash_screen():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    splash = SplashScreen()
    splash.show()
    return splash 