from PyQt5.QtWidgets import QApplication
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from gui.DreamscapeMainWindow import DreamscapeGUI
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DreamscapeGUI()
    window.show()
    sys.exit(app.exec_())
