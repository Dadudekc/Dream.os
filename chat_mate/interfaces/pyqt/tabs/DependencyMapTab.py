import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtWebEngineWidgets import QWebEngineView

class DependencyMapTab(QWidget):
    def __init__(self, html_file, parent=None):
        super().__init__(parent)
        self.html_file = html_file
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Loading indicator
        self.loading_label = QLabel("Loading dependency map...")
        layout.addWidget(self.loading_label)

        # Web view for displaying the graph
        self.web_view = QWebEngineView()
        self.web_view.setUrl(f"file://{os.path.abspath(self.html_file)}")
        layout.addWidget(self.web_view)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Graph")
        self.refresh_button.clicked.connect(self.load_graph)
        layout.addWidget(self.refresh_button)

        # Set layout
        self.setLayout(layout)

        # Load the graph initially
        self.load_graph()

    def load_graph(self):
        self.loading_label.setText("Loading dependency map...")
        self.web_view.setUrl(f"file://{os.path.abspath(self.html_file)}")
        self.loading_label.setText("Dependency map loaded.")

        # Optionally, handle errors if the file does not exist
        if not os.path.exists(self.html_file):
            self.loading_label.setText("Error: Dependency map file not found.")
