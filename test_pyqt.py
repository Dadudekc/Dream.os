"""Test PyQt5 imports."""
import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

try:
    import PyQt5
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 imported successfully")
    print(f"PyQt5 version: {PyQt5.QtCore.QT_VERSION_STR}")
except ImportError as e:
    print(f"Failed to import PyQt5: {e}")
    sys.exit(1)

app = QApplication(sys.argv)
print("QApplication created successfully") 