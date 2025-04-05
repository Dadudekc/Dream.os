import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

def main():
    """Run a simple PyQt5 test application."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("PyQt5 Test Window")
    window.setGeometry(100, 100, 400, 200)
    
    # Create central widget and layout
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Add a label
    label = QLabel("PyQt5 is working properly!")
    layout.addWidget(label)
    
    # Show the window
    window.show()
    
    # Run the application
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 