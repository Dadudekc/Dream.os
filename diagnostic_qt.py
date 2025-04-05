from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
import sys
import os

# Make sure we're in the right working directory
print(f"Current working directory: {os.getcwd()}")

# Enable debug output
os.environ['QT_DEBUG_PLUGINS'] = '1'

# Set attribute before QApplication creation (addresses webengine issue)
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

class SimpleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Diagnostic Window")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Add a label
        label = QLabel("If you can see this, PyQt GUI display is working correctly", self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Add a button that will close the app when clicked
        button = QPushButton("Click to close", self)
        button.clicked.connect(self.close)
        layout.addWidget(button)
        
        # Set the central widget
        self.setCentralWidget(central_widget)
        
        # Print confirmation that window was created
        print("Window created successfully")

if __name__ == "__main__":
    print("Starting PyQt diagnostic app")
    app = QApplication(sys.argv)
    print("QApplication created")
    
    window = SimpleWindow()
    print("Window instance created")
    
    # Make sure the window is visible
    window.show()
    print("Window.show() called")
    
    # This ensures the window stays visible until closed
    print("Entering application main loop (app.exec_())")
    sys.exit(app.exec_()) 