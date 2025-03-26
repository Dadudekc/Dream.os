import sys
import random
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from .views.file_browser_widget import FileBrowserWidget
from .GUI.GuiHelpers import GuiHelpers
from .automation_engine import AutomationEngine

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)

class GUIMain(QtWidgets.QMainWindow):
    def __init__(self, splash_screen=None):
        super().__init__()
        self.setWindowTitle("ChatGPT Automation - Unified Interface")
        self.resize(1200, 800)
        
        self.helpers = GuiHelpers()
        # Use OpenAIClient (headless=True for background operation)
        self.engine = AutomationEngine(use_local_llm=False, model_name='mistral', splash_screen=splash_screen)
        
        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Horizontal splitter for left/right panels
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # LEFT PANEL: File Browser remains unchanged
        self.file_browser = FileBrowserWidget(helpers=self.helpers)
        main_splitter.addWidget(self.file_browser)
        main_splitter.setStretchFactor(0, 1)
        
        # RIGHT PANEL: QTabWidget with "Preview" and "Prompt" tabs
        right_tab = QtWidgets.QTabWidget()
        
        # --- Tab 1: Preview with Action Buttons ---
        preview_widget = QtWidgets.QWidget()
        preview_layout = QtWidgets.QVBoxLayout(preview_widget)
        
        self.file_preview = QtWidgets.QPlainTextEdit()
        self.file_preview.setPlaceholderText(
            "File preview will appear here.\nDouble-click a file in the browser to load it for editing."
        )
        preview_layout.addWidget(self.file_preview)
        
        button_layout = QtWidgets.QHBoxLayout()
        self.process_button = QtWidgets.QPushButton("Process File")
        self.process_button.clicked.connect(self.process_file)
        button_layout.addWidget(self.process_button)
        
        self.self_heal_button = QtWidgets.QPushButton("Self-Heal")
        self.self_heal_button.clicked.connect(self.self_heal)
        button_layout.addWidget(self.self_heal_button)
        
        self.run_tests_button = QtWidgets.QPushButton("Run Tests")
        self.run_tests_button.clicked.connect(self.run_tests)
        button_layout.addWidget(self.run_tests_button)
        preview_layout.addLayout(button_layout)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        preview_layout.addWidget(self.progress_bar)
        
        right_tab.addTab(preview_widget, "Preview")
        
        # --- Tab 2: Prompt Tab for OpenAIClient ---
        prompt_widget = QtWidgets.QWidget()
        prompt_layout = QtWidgets.QVBoxLayout(prompt_widget)
        
        self.prompt_input = QtWidgets.QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        prompt_layout.addWidget(self.prompt_input)
        
        send_button = QtWidgets.QPushButton("Send Prompt to ChatGPT")
        send_button.clicked.connect(self.send_prompt)
        prompt_layout.addWidget(send_button)
        
        batch_button = QtWidgets.QPushButton("Process Batch with Prompt")
        batch_button.clicked.connect(self.process_batch_files)
        prompt_layout.addWidget(batch_button)
        
        self.prompt_response = QtWidgets.QPlainTextEdit()
        self.prompt_response.setReadOnly(True)
        self.prompt_response.setPlaceholderText("Response will appear here...")
        prompt_layout.addWidget(self.prompt_response)
        
        right_tab.addTab(prompt_widget, "Prompt")
        
        main_splitter.addWidget(right_tab)
        main_splitter.setStretchFactor(1, 3)
        
        self.statusBar().showMessage("Ready")
        
        self.file_browser.fileDoubleClicked.connect(self.load_file_into_preview)

    def load_file_into_preview(self, file_path):
        content = self.helpers.read_file(file_path)
        if content:
            self.file_preview.setPlainText(content)
            self.current_file_path = file_path
            self.statusBar().showMessage(f"Loaded: {file_path}")
        else:
            self.helpers.show_error("Could not load file.", "Error")

    def process_file(self):
        if not hasattr(self, "current_file_path"):
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        prompt_text = "Update this file and show me the complete updated version."
        file_content = self.file_preview.toPlainText()
        combined_prompt = f"{prompt_text}\n\n---\n\n{file_content}"
        self.statusBar().showMessage("Processing file...")
        
        response = self.engine.get_chatgpt_response(combined_prompt)
        if response:
            # Save to the updated folder, preserving the original filename.
            updated_file = UPDATED_FOLDER / Path(self.current_file_path).name
            saved = self.helpers.save_file(str(updated_file), response)
            if saved:
                self.statusBar().showMessage(f"✅ Updated file saved: {updated_file}")
            else:
                self.statusBar().showMessage(f"❌ Failed to save: {updated_file}")
        else:
            self.statusBar().showMessage("❌ No response from ChatGPT.")

    def self_heal(self):
        if not hasattr(self, "current_file_path"):
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        self.statusBar().showMessage("Self-healing in progress...")
        response = self.engine.self_heal_file(self.current_file_path)
        if response:
            updated_file = UPDATED_FOLDER / Path(self.current_file_path).name
            saved = self.helpers.save_file(str(updated_file), response)
            if saved:
                self.statusBar().showMessage(f"✅ Self-healed file saved: {updated_file}")
            else:
                self.statusBar().showMessage(f"❌ Failed to save self-healed file: {updated_file}")
        else:
            self.statusBar().showMessage("❌ Self-Heal did not produce a response.")

    def run_tests(self):
        if not hasattr(self, "current_file_path"):
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        self.statusBar().showMessage("Running tests...")
        results = self.engine.run_tests(self.current_file_path)
        self.statusBar().showMessage("Test run complete.")

    def send_prompt(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.statusBar().showMessage("Please enter a prompt.")
            return
        
        self.statusBar().showMessage("Sending prompt to ChatGPT...")
        response = self.engine.openai_client.process_prompt(prompt)
        if response:
            self.prompt_response.setPlainText(response)
            self.statusBar().showMessage("✅ Response received.")
        else:
            self.prompt_response.setPlainText("❌ No response received.")
            self.statusBar().showMessage("❌ No response received.")

    def process_batch_files(self):
        file_list = self.engine.prioritize_files()
        if not file_list:
            self.statusBar().showMessage("No files found for batch processing.")
            return
        
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.statusBar().showMessage("Please enter a prompt for batch processing.")
            return
        
        total_files = len(file_list)
        self.statusBar().showMessage(f"Processing {total_files} files with the shared prompt...")
        
        batch_results = []
        for index, file_path in enumerate(file_list, start=1):
            progress_percent = int((index / total_files) * 100)
            self.progress_bar.setValue(progress_percent)
            
            file_content = self.helpers.read_file(file_path)
            if not file_content:
                batch_results.append(f"[WARNING] Failed to read {file_path}")
                continue
            
            composite_prompt = f"{prompt}\n\n---\n\n{file_content}"
            self.statusBar().showMessage(f"Processing {file_path}...")
            response = self.engine.get_chatgpt_response(composite_prompt)
            
            if response:
                updated_file = UPDATED_FOLDER / Path(file_path).name
                if self.helpers.save_file(str(updated_file), response):
                    batch_results.append(f"[SUCCESS] {updated_file} saved.")
                else:
                    batch_results.append(f"[ERROR] Failed to save {updated_file}.")
            else:
                batch_results.append(f"[ERROR] No response for {file_path}.")
        
        self.prompt_response.setPlainText("\n".join(batch_results))
        self.statusBar().showMessage("Batch processing complete.")

    def closeEvent(self, event):
        """Handle application shutdown."""
        try:
            # Update status
            self.statusBar().showMessage("Shutting down application...")
            
            # First, stop any ongoing operations
            if hasattr(self, 'engine') and self.engine:
                self.statusBar().showMessage("Shutting down automation engine...")
                self.engine.shutdown()
                
            # Clean up file browser
            if hasattr(self, 'file_browser'):
                self.file_browser.cleanup()
                
            # Accept the close event
            event.accept()
            
            # Finally, ensure the application quits
            QtWidgets.QApplication.quit()
            
        except Exception as e:
            self.statusBar().showMessage(f"Error during shutdown: {str(e)}")
            event.accept()  # Still accept the event to ensure we close
            QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Splash screen with loading bar and motivational quotes
    splash_pix = QtGui.QPixmap("logo.webp")
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

    # Initialize main window with splash screen
    window = GUIMain(splash_screen=splash)
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
