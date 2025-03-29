import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QCheckBox, QTextEdit
from PyQt5.QtCore import QCoreApplication

class GUIEventHandler(QMainWindow):
    """
    GUI Event Handler for ChatMate Agent Control Panel
    - Control Config Flags (Headless, Reverse Order, Archive)
    - Start/Stop the Agent Dispatcher
    - Display logs or status updates
    """

    def __init__(self, config, dispatcher):
        super(GUIEventHandler, self).__init__()

        self.config = config
        self.dispatcher = dispatcher
        self.dispatcher_thread = None

        self.setWindowTitle("ChatMate Agent Control Panel")
        self.setGeometry(100, 100, 500, 400)

        self.init_ui()

    def init_ui(self):
        # Status label
        self.status_label = QLabel(self)
        self.status_label.setText("⚙️ System Status: Stopped")
        self.status_label.setGeometry(20, 20, 300, 30)

        # Headless toggle
        self.headless_checkbox = QCheckBox("Headless Mode", self)
        self.headless_checkbox.setGeometry(20, 70, 200, 30)
        self.headless_checkbox.setChecked(self.config.get("headless", True))
        self.headless_checkbox.stateChanged.connect(self.toggle_headless)

        # Reverse order toggle
        self.reverse_checkbox = QCheckBox("Reverse Chat Order", self)
        self.reverse_checkbox.setGeometry(20, 110, 200, 30)
        self.reverse_checkbox.setChecked(self.config.get("reverse_order", False))
        self.reverse_checkbox.stateChanged.connect(self.toggle_reverse)

        # Archive chats toggle
        self.archive_checkbox = QCheckBox("Archive Chats After Cycle", self)
        self.archive_checkbox.setGeometry(20, 150, 250, 30)
        self.archive_checkbox.setChecked(self.config.get("archive_enabled", True))
        self.archive_checkbox.stateChanged.connect(self.toggle_archive)

        # Start button
        self.start_button = QPushButton("🚀 Start Agent Dispatcher", self)
        self.start_button.setGeometry(20, 200, 250, 40)
        self.start_button.clicked.connect(self.start_dispatcher)

        # Stop button
        self.stop_button = QPushButton("🛑 Stop Agent Dispatcher", self)
        self.stop_button.setGeometry(20, 250, 250, 40)
        self.stop_button.clicked.connect(self.stop_dispatcher)

        # Log display
        self.log_display = QTextEdit(self)
        self.log_display.setGeometry(280, 20, 200, 350)
        self.log_display.setReadOnly(True)
        self.log("✅ GUI Initialized.")

    # -----------------------------
    # CONFIG TOGGLE HANDLERS
    # -----------------------------

    def toggle_headless(self):
        self.config.set("headless", self.headless_checkbox.isChecked())
        self.log(f"🟢 Headless mode {'enabled' if self.config.get('headless', True) else 'disabled'}.")

    def toggle_reverse(self):
        self.config.set("reverse_order", self.reverse_checkbox.isChecked())
        self.log(f"🔄 Reverse chat order {'enabled' if self.config.get('reverse_order', False) else 'disabled'}.")

    def toggle_archive(self):
        self.config.set("archive_enabled", self.archive_checkbox.isChecked())
        self.log(f"📦 Archive after chat cycle {'enabled' if self.config.get('archive_enabled', True) else 'disabled'}.")

    # -----------------------------
    # DISPATCHER CONTROL
    # -----------------------------

    def start_dispatcher(self):
        if self.dispatcher.running:
            self.log("⚠️ Agent Dispatcher already running.")
            return

        self.log("🚀 Starting Agent Dispatcher...")
        self.status_label.setText("⚙️ System Status: Running")
        self.dispatcher_thread = QtCore.QThread()
        self.dispatcher.moveToThread(self.dispatcher_thread)
        self.dispatcher_thread.started.connect(self.dispatcher.start)
        self.dispatcher_thread.start()

    def stop_dispatcher(self):
        if not self.dispatcher.running:
            self.log("⚠️ Agent Dispatcher not running.")
            return

        self.log("🛑 Stopping Agent Dispatcher...")
        self.dispatcher.stop()

        if self.dispatcher_thread:
            self.dispatcher_thread.quit()
            self.dispatcher_thread.wait()

        self.status_label.setText("⚙️ System Status: Stopped")

    # -----------------------------
    # LOGGING HELPER
    # -----------------------------

    def log(self, message):
        self.log_display.append(message)
        print(message)

    def closeEvent(self, event):
        """
        Handle the window close event to ensure proper shutdown
        """
        self.log("🛑 Shutting down application...")
        
        # Stop the dispatcher if running
        if self.dispatcher and hasattr(self.dispatcher, 'running') and self.dispatcher.running:
            self.stop_dispatcher()
        
        # Additional cleanup for any resources
        if hasattr(self.dispatcher, 'shutdown'):
            self.dispatcher.shutdown()
        
        # Wait for any remaining threads to terminate
        if self.dispatcher_thread and self.dispatcher_thread.isRunning():
            try:
                self.dispatcher_thread.quit()
                # Give the thread time to terminate gracefully
                success = self.dispatcher_thread.wait(3000)  # 3 seconds timeout
                if not success:
                    self.log("⚠️ Thread did not terminate gracefully, forcing termination...")
                    self.dispatcher_thread.terminate()
            except Exception as e:
                self.log(f"⚠️ Error during thread shutdown: {e}")
        
        # Accept the close event
        event.accept()
        
        # Exit the application
        QCoreApplication.exit(0)


# -----------------------------
# ENTRY POINT FOR GUI TESTING
# -----------------------------

def run_gui(config, dispatcher):
    app = QApplication(sys.argv)
    gui = GUIEventHandler(config, dispatcher)
    gui.show()
    sys.exit(app.exec_())
