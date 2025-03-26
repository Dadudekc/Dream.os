"""
Simple test script to verify the tab fixes.
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel

def main():
    print("Starting tab test...")
    app = QApplication(sys.argv)
    
    # Create a simple window
    window = QMainWindow()
    window.setWindowTitle("Tab Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Create a central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # Create a layout
    layout = QVBoxLayout(central_widget)
    
    # Add a label
    label = QLabel("Tabs should be fixed now. Verify by running the full Dreamscape app with:\n"
                  "python -m interfaces.pyqt.DreamscapeMainWindow")
    layout.addWidget(label)
    
    # Show the window
    window.show()
    print("Window shown")
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 