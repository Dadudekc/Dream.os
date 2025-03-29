#!/usr/bin/env python3
"""
meredith_tab.py

A full-featured PyQt5 tab for Dream.OS that:
  - Spawns a separate thread to scrape profiles (ScraperThread).
  - Integrates seamlessly with the ScraperManager and ProfileFilter classes
    from meredith.profile_scraper.
  - Displays scrape progress, logs, and final results in a responsive UI.
  - Allows you to open each discovered profile in a browser via a "Message" button.
  - Exports filtered profiles to JSON.
  - Supports canceling an in-progress scrape.
  - Offers a "Clear" function for resetting the tab’s data and logs.
  - Displays a "Resonance Score" computed via ResonanceScorer.
  - Dynamically loads all resonance model JSONs from the "resonance_match_models" directory.
  - Can be toggled visible/invisible if running in "private mode."
"""

import os
import json
import logging
import webbrowser
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QProgressBar, QComboBox
)

# Adjust import paths to your project structure
from core.meredith.profile_scraper import ScraperManager, ProfileFilter
from core.meredith.resonance_scorer import ResonanceScorer
from core.PathManager import PathManager

# Directory where all resonance JSON models are stored
MODEL_DIR = PathManager().get_path("resonance_models")



###############################################################################
#                             SCRAPER THREAD                                  #
###############################################################################

class ScraperThread(QThread):
    """
    A separate QThread to perform the Meredith scraping process off the main UI thread.
    This prevents UI blocking while ScraperManager runs.
    
    Signals:
        scan_completed (list): Emitted when scraping+filtering completes or is canceled/errored.
        log_update (str): Emitted for logging messages to the UI.
        progress_update (int): Emitted for updating a progress bar (0-100).
    """
    scan_completed = pyqtSignal(list)
    log_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._cancel_requested = False

    def cancel(self):
        """
        Request that the scraping operation be halted at the next safe checkpoint.
        """
        self._cancel_requested = True

    def run(self):
        """
        The thread's entrypoint. Coordinates:
          1. Initialization of ScraperManager.
          2. Running default scrapers.
          3. Location/gender filtering.
          4. Emission of final results or error logs.
          5. Periodic progress updates.
        """
        try:
            self.log_update.emit("Initializing Meredith full sync scan...")
            self.progress_update.emit(10)

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

            if self._cancel_requested:
                scraper_manager.close()
                self.log_update.emit("Scan canceled during scraping.")
                self.scan_completed.emit([])
                return

            self.log_update.emit("Filtering by location...")
            local_profiles = ProfileFilter.filter_by_location(all_profiles, ["houston", "htx"], "77090")

            self.log_update.emit("Filtering by gender (female)...")
            final_profiles = ProfileFilter.filter_by_gender(local_profiles, "female")
            self.progress_update.emit(90)

            scraper_manager.close()
            self.log_update.emit(f"Found {len(final_profiles)} matching profiles.")
            self.progress_update.emit(100)

            if self._cancel_requested:
                self.log_update.emit("Scan canceled at final checkpoint.")
                self.scan_completed.emit([])
                return

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
    A private PyQt5 tab that orchestrates:
      - Running the Meredith scraping (in a background thread).
      - Displaying progress logs and a progress bar.
      - Showing the final filtered profiles in a QTableWidget.
      - Exporting or clearing results.
      - Providing a 'Message' button that opens each profile in your default browser.
      - Displaying a "Resonance Score" computed via the ResonanceScorer.
      - Dynamically loading available resonance models from a directory.
      - Can be toggled visible/invisible if running in "private mode."
    
    Args:
        parent (QWidget): Parent widget, if any.
        private_mode (bool): If True, the tab is hidden by default.
    """
    def __init__(self, parent=None, private_mode=True):
        super().__init__(parent)
        self.private_mode = private_mode
        self.filtered_profiles = []

        # Load default model (if exists, otherwise you may handle errors)
        default_model = os.path.join(MODEL_DIR, "romantic.json")
        self.scorer = ResonanceScorer(default_model)

        self.setWindowTitle("Meredith - Private Resonance Scanner")
        self.init_ui()

        if self.private_mode:
            self.hide()

    def init_ui(self):
        """
        Constructs the UI layout:
          1. Header label.
          2. Model selector dropdown (populated dynamically from MODEL_DIR).
          3. Button row: Run, Stop, Export, Clear.
          4. Progress bar.
          5. Log output.
          6. Results table with columns for Platform, Username, Bio, Location, URL, Message, and Resonance Score.
        """
        layout = QVBoxLayout()

        # --- HEADER ---
        header_label = QLabel("Meredith: Private Resonance Scanner")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size:16px;font-weight:bold;")
        layout.addWidget(header_label)

        # --- MODEL SELECTOR (Dynamic) ---
        self.model_selector = QComboBox()
        self.populate_model_selector()
        self.model_selector.currentTextChanged.connect(self.switch_model)
        layout.addWidget(self.model_selector)

        # --- BUTTON ROW ---
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

        # --- PROGRESS BAR ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- LOG OUTPUT ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(100)
        layout.addWidget(self.log_output)

        # --- RESULTS TABLE ---
        # 7 columns: Platform, Username, Bio, Location, URL, Message, Resonance Score
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Platform", "Username", "Bio", "Location", "URL", "Message", "Resonance Score"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def populate_model_selector(self):
        """
        Reads all JSON files in the MODEL_DIR and populates the dropdown with their base names.
        """
        self.model_selector.clear()
        if os.path.isdir(MODEL_DIR):
            files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".json")]
            # Sort alphabetically for consistency
            files.sort()
            for file in files:
                model_name = os.path.splitext(file)[0]
                self.model_selector.addItem(model_name)
        else:
            self.log("Model directory not found.")

    def switch_model(self, model_name):
        """
        Loads the resonance model corresponding to the selected name.
        """
        path = os.path.join(MODEL_DIR, f"{model_name}.json")
        if os.path.exists(path):
            self.scorer.load_model(path)
            self.log(f"Resonance model switched to '{model_name}'.")
        else:
            self.log(f"Model '{model_name}' not found.")

    ###############################################################################
    #                                LOGGING                                      #
    ###############################################################################

    def log(self, message: str):
        """
        Appends a log message to the log output and routes it to the Python logger.
        """
        self.log_output.append(message)
        logging.info(f"[MeredithTab] {message}")

    ###############################################################################
    #                                SCAN LOGIC                                   #
    ###############################################################################

    def run_full_scan(self):
        """
        Initiates the scraping process in a background thread,
        disabling UI controls until the scan completes or is canceled.
        """
        self.log("Launching Meredith scraper thread...")
        self._reset_ui_for_new_scan()

        self.scraper_thread = ScraperThread()
        self.scraper_thread.scan_completed.connect(self.on_scan_completed)
        self.scraper_thread.log_update.connect(self.log)
        self.scraper_thread.progress_update.connect(self.progress_bar.setValue)

        self.stop_button.setEnabled(True)
        self.scraper_thread.start()

    def stop_scan(self):
        """
        Cancels an ongoing scraping operation.
        """
        if hasattr(self, 'scraper_thread') and self.scraper_thread.isRunning():
            self.log("Stop requested. Attempting to cancel ongoing scan...")
            self.scraper_thread.cancel()
            self.stop_button.setEnabled(False)

    def on_scan_completed(self, profiles: list):
        """
        Called when the scraper thread completes. Re-enables UI controls and populates the results table.
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

    ###############################################################################
    #                             TABLE POPULATION                                #
    ###############################################################################

    def populate_results_table(self, profiles: list):
        """
        Renders each profile as a row in the results table, adding:
          - A 'Message' button to open the profile URL in a browser.
          - A "Resonance Score" computed via the ResonanceScorer.
        """
        self.results_table.setRowCount(len(profiles))

        for row, profile in enumerate(profiles):
            # Standard data columns
            self.results_table.setItem(row, 0, QTableWidgetItem(profile.get("platform", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(profile.get("username", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(profile.get("bio", "")))
            self.results_table.setItem(row, 3, QTableWidgetItem(profile.get("location", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(profile.get("url", "")))

            # 'Message' button column
            url_for_this_profile = profile.get("url", "")
            message_button = QPushButton("Message")
            message_button.clicked.connect(
                lambda _, url=url_for_this_profile: self.open_profile_in_browser(url)
            )
            self.results_table.setCellWidget(row, 5, message_button)

            # 'Resonance Score' column
            result = self.scorer.score_profile(profile)
            score_text = f"{result['score']:.2f}"
            self.results_table.setItem(row, 6, QTableWidgetItem(score_text))

    def open_profile_in_browser(self, url: str):
        """
        Opens the provided URL in the default web browser.
        """
        if not url:
            self.log("No URL available for this profile.")
            return
        webbrowser.open(url)
        self.log(f"Opened URL: {url}")

    ###############################################################################
    #                             DATA MANAGEMENT                                 #
    ###############################################################################

    def export_results(self):
        """
        Exports the current filtered profiles to a JSON file chosen by the user.
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
        Clears the results table, local profile data, and log output.
        """
        self.results_table.setRowCount(0)
        self.filtered_profiles.clear()
        self.log_output.clear()
        self.log("Cleared all results.")

        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)

    ###############################################################################
    #                                UI HELPERS                                   #
    ###############################################################################

    def _reset_ui_for_new_scan(self):
        """
        Resets UI elements to prepare for a new scrape.
        """
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.filtered_profiles.clear()

    def toggle_visibility(self):
        """
        Toggles the tab's visibility (useful for private mode hotkeys).
        """
        self.setVisible(not self.isVisible())