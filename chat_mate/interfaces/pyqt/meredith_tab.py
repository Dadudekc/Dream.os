from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
import json
import os
import logging

from meredith.profile_scraper import ScraperManager, ProfileFilter

###############################################################################
#                              SCRAPER THREAD                                 #
###############################################################################

class ScraperThread(QThread):
    """
    A separate thread to run the Meredith scraping process 
    without freezing the PyQt UI.
    """
    scan_completed = pyqtSignal(list)      # Emitted when scraping+filtering is done
    log_update = pyqtSignal(str)           # Emitted to display log messages on the UI
    progress_update = pyqtSignal(int)      # Emitted to update the progress bar

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._cancel_requested = False

    def cancel(self):
        """
        Signals the thread that the user wants to cancel the operation.
        """
        self._cancel_requested = True

    def run(self):
        """
        Main logic that executes in the worker thread:
         1. Initialize ScraperManager
         2. Run default scrapers
         3. Filter results
         4. Return final profiles
        """
        try:
            self.log_update.emit("Initializing Meredith full sync scan...")
            self.progress_update.emit(10)

            # Early cancellation check
            if self._cancel_requested:
                self.log_update.emit("Scan canceled before start.")
                self.scan_completed.emit([])
                return

            scraper_manager = ScraperManager(headless=True)
            scraper_manager.register_default_scrapers()

            self.log_update.emit("Scraping profiles across platforms...")
            all_profiles = scraper_manager.run_all()
            self.progress_update.emit(50)
            self.log_update.emit(f"Scraped {len(all_profiles)} profiles.")

            # Check again for cancellation
            if self._cancel_requested:
                scraper_manager.close()
                self.log_update.emit("Scan canceled during scraping.")
                self.scan_completed.emit([])
                return

            self.log_update.emit("Filtering by location...")
            local_profiles = ProfileFilter.filter_by_location(
                all_profiles, ["houston", "htx"], "77090"
            )

            self.log_update.emit("Filtering by gender (female)...")
            final_profiles = ProfileFilter.filter_by_gender(local_profiles, "female")
            self.progress_update.emit(90)

            scraper_manager.close()
            self.log_update.emit(f"Found {len(final_profiles)} matching profiles.")
            self.progress_update.emit(100)

            # Final check for cancellation
            if self._cancel_requested:
                self.log_update.emit("Scan canceled at the very end.")
                self.scan_completed.emit([])
                return

            # Emitting final results
            self.scan_completed.emit(final_profiles)

        except Exception as e:
            logging.exception("Exception in scraper thread:")
            self.log_update.emit(f"Error during scan: {str(e)}")
            self.scan_completed.emit([])

###############################################################################
#                               MEREDITH TAB                                  #
###############################################################################

class MeredithTab(QWidget):
    """
    A private tab within the Dream.OS PyQt interface that manages:
      - Running the Meredith scraping process in a separate thread.
      - Displaying logs, progress, and final profiles in a table.
      - Exporting results to a JSON file.
    """
    def __init__(self, parent=None, private_mode=True):
        super().__init__(parent)
        self.private_mode = private_mode
        self.filtered_profiles = []

        self.setWindowTitle("Meredith - Private Resonance Scanner")
        self.init_ui()

        # Hide this tab if it's in private mode
        if self.private_mode:
            self.hide()

    def init_ui(self):
        """
        Assembles the PyQt widgets: 
          - Header label
          - Buttons (Scan, Stop, Export, Clear)
          - Progress bar
          - Log output
          - Results table
        """
        layout = QVBoxLayout()

        # --- Header ---
        header_label = QLabel("Meredith: Private Resonance Scanner")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size:16px;font-weight:bold;")
        layout.addWidget(header_label)

        # --- Button Row ---
        button_layout = QHBoxLayout()

        self.run_button = QPushButton("Run Full Scan")
        self.run_button.clicked.connect(self.run_full_scan)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_scan)
        button_layout.addWidget(self.stop_button)

        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)

        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setEnabled(False)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- Log Output ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(100)
        layout.addWidget(self.log_output)

        # --- Results Table ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Platform", "Username", "Bio", "Location", "URL"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def log(self, message: str):
        """
        Appends a log message to the QTextEdit and also logs to the Python logger.
        """
        self.log_output.append(message)
        logging.info(f"[MeredithTab] {message}")

    def run_full_scan(self):
        """
        Triggers a new scrape in a separate thread, disabling relevant UI elements.
        """
        self.log("Launching Meredith scraper thread...")
        self._reset_ui_for_new_scan()

        self.scraper_thread = ScraperThread()
        self.scraper_thread.scan_completed.connect(self.on_scan_completed)
        self.scraper_thread.log_update.connect(self.log)
        self.scraper_thread.progress_update.connect(self.progress_bar.setValue)

        # Enable the Stop button
        self.stop_button.setEnabled(True)

        # Start the thread
        self.scraper_thread.start()

    def stop_scan(self):
        """
        Requests cancellation of the ongoing scraping thread.
        """
        if hasattr(self, 'scraper_thread') and self.scraper_thread.isRunning():
            self.log("Stop requested. Attempting to cancel ongoing scan...")
            self.scraper_thread.cancel()
            self.stop_button.setEnabled(False)

    def on_scan_completed(self, profiles: list):
        """
        Called when the ScraperThread finishes (successfully or not).
        Enables the UI again and displays the results if any.
        """
        self.filtered_profiles = profiles
        self.populate_results_table(profiles)

        self.export_button.setEnabled(bool(profiles))
        self.clear_button.setEnabled(bool(profiles))
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if profiles:
            self.log("Scan complete.")
        else:
            self.log("No profiles found or scan was canceled.")

    def populate_results_table(self, profiles: list):
        """
        Fills the QTableWidget with profile data.
        """
        self.results_table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            self.results_table.setItem(row, 0, QTableWidgetItem(profile.get("platform", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(profile.get("username", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(profile.get("bio", "")))
            self.results_table.setItem(row, 3, QTableWidgetItem(profile.get("location", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(profile.get("url", "")))

    def export_results(self):
        """
        Saves the current filtered profiles to a user-selected JSON file.
        """
        if not self.filtered_profiles:
            self.log("No results available to export.")
            return

        default_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(default_dir, exist_ok=True)
        default_file = os.path.join(default_dir, "meredith_profiles.json")

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Profiles", default_file, "JSON Files (*.json)"
        )

        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.filtered_profiles, f, indent=4)
            self.log(f"Exported {len(self.filtered_profiles)} profiles to {file_path}.")

    def clear_results(self):
        """
        Clears the table and local data, along with the log output.
        """
        self.results_table.setRowCount(0)
        self.filtered_profiles.clear()
        self.log_output.clear()
        self.log("Cleared all results.")
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)

    def toggle_visibility(self):
        """
        Toggles whether the tab is visible or hidden.
        Useful for a hotkey-based approach to open a private tab.
        """
        self.setVisible(not self.isVisible())

    def _reset_ui_for_new_scan(self):
        """
        Resets UI elements to a clean state before starting a new scan.
        """
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.filtered_profiles.clear()