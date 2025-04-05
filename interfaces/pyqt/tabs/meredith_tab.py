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
  - Offers a "Clear" function for resetting the tab's data and logs.
  - Displays a "Resonance Score" computed via ResonanceScorer.
  - Dynamically loads all resonance model JSONs from the "resonance_match_models" directory.
  - Can be toggled visible/invisible if running in "private mode."
  - Integrates the MeredithDispatcher for analyzing profiles and logging resonance matches.
  - Displays visual indicators for profiles saved to MeritChain.
  - Provides a view of previously saved MeritChain entries.
"""

import os
import json
import logging
import webbrowser
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QProgressBar, QComboBox, QMessageBox,
    QDialog, QTabWidget, QListWidget, QListWidgetItem, QSplitter,
    QFrame, QGridLayout
)
from PyQt5.QtGui import QIcon, QColor, QBrush, QFont
from pathlib import Path
from typing import Dict, Any

# Adjust import paths to your project structure
from core.meredith.profile_scraper import ScraperManager, ProfileFilter
from core.meredith.resonance_scorer import ResonanceScorer
from core.PathManager import PathManager
from core.meredith.meredith_dispatcher import MeredithDispatcher

# Define the MeritChain file path (could be managed by PathManager too)
MERITCHAIN_FILE = "memory/meritchain.json"


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
#                            MERITCHAIN DIALOG                                #
###############################################################################

class MeritChainViewDialog(QDialog):
    """
    Dialog for viewing MeritChain entries.
    Provides a list of saved matches and a detailed view of the selected match.
    """
    def __init__(self, dispatcher, parent=None):
        super().__init__(parent)
        self.dispatcher = dispatcher
        self.setWindowTitle("MeritChain Entries")
        self.resize(800, 600)
        self.init_ui()
        self.load_entries()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Create a splitter for the list and details view
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - List of entries
        self.entries_list = QListWidget()
        self.entries_list.setMinimumWidth(200)
        self.entries_list.currentItemChanged.connect(self.on_entry_selected)
        splitter.addWidget(self.entries_list)
        
        # Right side - Entry details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Details header
        self.details_header = QLabel("Select an entry to view details")
        details_layout.addWidget(self.details_header)
        
        # Details grid (for key-value pairs)
        self.details_grid = QGridLayout()
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.StyledPanel)
        details_frame.setLayout(self.details_grid)
        details_layout.addWidget(details_frame)
        
        # First message preview
        message_label = QLabel("First Message:")
        details_layout.addWidget(message_label)
        
        self.message_text = QTextEdit()
        self.message_text.setReadOnly(True)
        details_layout.addWidget(self.message_text)
        
        splitter.addWidget(details_widget)
        
        # Add the splitter to the main layout
        layout.addWidget(splitter)
        
        # Button layout
        button_layout = QHBoxLayout()

        # Delete button
        delete_button = QPushButton("Delete Entry")
        delete_button.setIcon(QIcon.fromTheme("edit-delete")) # Optional icon
        delete_button.clicked.connect(self.delete_selected_entry)
        button_layout.addWidget(delete_button)

        button_layout.addStretch() # Add space between buttons

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_entries(self):
        """Load entries from the MeritChain."""
        # Store entries locally for easier access
        self.current_entries = self.dispatcher.get_previous_matches(100) # Increased limit
        self.entries_list.clear()
        
        for entry in self.current_entries:
            username = entry.get("username", "Unknown")
            platform = entry.get("platform", "Unknown")
            score = entry.get("resonance_score", 0)
            
            item = QListWidgetItem(f"{username} ({platform}) - {score}")
            
            # Set tooltip with more details
            tooltip = f"Username: {username}\nPlatform: {platform}\nScore: {score}"
            if "timestamp" in entry:
                dt = datetime.fromisoformat(entry["timestamp"])
                tooltip += f"\nAdded: {dt.strftime('%Y-%m-%d %H:%M')}"
            item.setToolTip(tooltip)
            
            # Set data for the item
            item.setData(Qt.UserRole, entry)
            
            # Set color based on score
            if score >= 90:
                item.setForeground(QBrush(QColor("green")))
                item.setFont(QFont("Arial", 10, QFont.Bold))
            elif score >= 75:
                item.setForeground(QBrush(QColor("blue")))
            
            self.entries_list.addItem(item)

    def on_entry_selected(self, current, previous):
        """Handle selection of an entry."""
        if not current:
            return
            
        entry = current.data(Qt.UserRole)
        if not entry:
            return
            
        # Update the header
        username = entry.get("username", "Unknown")
        platform = entry.get("platform", "Unknown")
        score = entry.get("resonance_score", 0)
        self.details_header.setText(f"{username} from {platform} - Resonance Score: {score}")
        
        # Clear the grid
        for i in reversed(range(self.details_grid.count())):
            self.details_grid.itemAt(i).widget().setParent(None)
        
        # Add details to the grid
        row = 0
        for key, value in entry.items():
            if key in ["username", "platform", "resonance_score", "first_message"]:
                continue  # Skip these as they're shown elsewhere
                
            if key == "timestamp":
                try:
                    dt = datetime.fromisoformat(value)
                    value = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
                    
            if isinstance(value, list):
                value = ", ".join(value)
                
            label = QLabel(f"{key.replace('_', ' ').title()}:")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setFont(QFont("Arial", 9, QFont.Bold))
            
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            
            self.details_grid.addWidget(label, row, 0)
            self.details_grid.addWidget(value_label, row, 1)
            row += 1
            
        # Set the first message
        first_message = entry.get("first_message", "")
        self.message_text.setText(first_message)

    def delete_selected_entry(self):
        """Deletes the currently selected entry from the MeritChain."""
        current_item = self.entries_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an entry to delete.")
            return

        entry = current_item.data(Qt.UserRole)
        if not entry:
            QMessageBox.critical(self, "Error", "Could not retrieve entry data.")
            return

        username = entry.get("username", "Unknown")
        platform = entry.get("platform", "Unknown")

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the MeritChain entry for '{username}' ({platform})?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Assuming dispatcher has the memory manager instance
                # REVIEW: Ensure self.dispatcher.memory correctly points to MeritChainManager
                if hasattr(self.dispatcher, 'memory') and hasattr(self.dispatcher.memory, 'delete_by_username'):
                    deleted = self.dispatcher.memory.delete_by_username(username)
                    if deleted:
                        QMessageBox.information(self, "Success", f"Entry for '{username}' deleted successfully.")
                        # Refresh the list
                        self.load_entries()
                        # Clear details view
                        self.details_header.setText("Select an entry to view details")
                        for i in reversed(range(self.details_grid.count())):
                            widget = self.details_grid.itemAt(i).widget()
                            if widget:
                                widget.setParent(None)
                        self.message_text.clear()
                    else:
                        QMessageBox.warning(self, "Deletion Failed", f"Could not find or delete entry for '{username}'.")
                else:
                     QMessageBox.critical(self, "Error", "Delete functionality is not available.")
                     # TODO: Add proper logging here
                     print("[MeritChainViewDialog] Error: dispatcher.memory or delete_by_username not found.")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred during deletion: {e}")
                # TODO: Add proper logging here
                print(f"[MeritChainViewDialog] Error deleting entry: {e}")


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
      - Integrates the MeredithDispatcher to analyze profiles.
      - Can be toggled visible/invisible if running in "private mode."
      - Provides access to view MeritChain entries.
    
    Args:
        services (Dict[str, Any]): Dictionary of shared services.
        parent (QWidget): Parent widget, if any.
        private_mode (bool): If True, the tab is hidden by default.
    """
    def __init__(self, services: Dict[str, Any], parent=None, private_mode=True):
        super().__init__(parent)
        self.services = services
        self.private_mode = private_mode
        self.filtered_profiles = []
        self.analyzed_profiles = set()
        
        self.logger = services.get('logger', logging.getLogger(__name__))
        self.dispatcher = services.get('meredith_dispatcher')
        path_manager = services.get('path_manager') # Get path_manager
        
        if not self.dispatcher:
            self.logger.error("MeredithDispatcher service not found. Creating a local instance.")
            self.dispatcher = MeredithDispatcher() 
        else:
             self.logger.info("MeredithDispatcher service retrieved successfully.")

        # Initialize ResonanceScorer using path from PathManager
        self.scorer = None
        if path_manager:
            try:
                model_dir_path = path_manager.get_path("resonance_models")
                default_model_path = model_dir_path / "romantic.json"
                if default_model_path.exists():
                    self.scorer = ResonanceScorer(str(default_model_path))
                    self.logger.info(f"Initialized ResonanceScorer with default model: {default_model_path}")
                else:
                     self.logger.error(f"Default resonance model not found at {default_model_path}. Scorer not functional.")
            except KeyError:
                 self.logger.error("PathManager missing 'resonance_models' key. Cannot initialize ResonanceScorer.")
            except Exception as e:
                self.logger.error(f"Error initializing ResonanceScorer: {e}")
        else:
            self.logger.error("PathManager service not found. Cannot determine model path for ResonanceScorer.")

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
          6. Results table with columns for Platform, Username, Bio, Location, URL, Message, Analyze, and Resonance Score.
          7. View MeritChain button to access previously saved matches.
        """
        layout = QVBoxLayout()

        # --- HEADER ---
        header_label = QLabel("Meredith: Private Resonance Scanner")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size:16px;font-weight:bold;")
        layout.addWidget(header_label)

        # --- MODEL SELECTOR (Dynamic) ---
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Resonance Model:"))
        
        self.model_selector = QComboBox()
        self.populate_model_selector()
        self.model_selector.currentTextChanged.connect(self.switch_model)
        model_layout.addWidget(self.model_selector, stretch=2)
        
        # View MeritChain button
        self.view_meritchain_button = QPushButton("View MeritChain")
        self.view_meritchain_button.clicked.connect(self.view_meritchain)
        model_layout.addWidget(self.view_meritchain_button, stretch=1)
        
        layout.addLayout(model_layout)

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
        # 9 columns: Status, Platform, Username, Bio, Location, URL, Message, Analyze, Resonance Score
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Status", "Platform", "Username", "Bio", "Location", "URL", "Message", "Analyze", "Resonance Score"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Set the Status column to be narrower
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.results_table.setColumnWidth(0, 40)
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def populate_model_selector(self):
        """
        Reads all JSON files in the model directory (obtained via PathManager) 
        and populates the dropdown with their base names.
        """
        self.model_selector.clear()
        path_manager = self.services.get('path_manager')
        if path_manager:
            try:
                model_dir = path_manager.get_path("resonance_models")
                if model_dir.is_dir():
                    files = [f for f in model_dir.glob("*.json")]
                    files.sort()
                    for file_path in files:
                        model_name = file_path.stem
                        self.model_selector.addItem(model_name)
                else:
                    self.log(f"Resonance model path is not a directory: {model_dir}")
            except KeyError:
                 self.log("PathManager missing 'resonance_models' key. Cannot populate models.")
            except Exception as e:
                self.log(f"Error populating model selector: {e}")
        else:
            self.log("PathManager service not found. Cannot populate models.")

    def switch_model(self, model_name):
        """
        Loads the resonance model corresponding to the selected name.
        """
        path_manager = self.services.get('path_manager')
        if path_manager and self.scorer is not None: # Check if scorer was initialized
            try:
                model_dir = path_manager.get_path("resonance_models")
                path = model_dir / f"{model_name}.json"
                if path.exists():
                    self.scorer.load_model(str(path))
                    self.log(f"Resonance model switched to '{model_name}'.")
                else:
                    self.log(f"Model file '{path}' not found.")
            except KeyError:
                 self.log("PathManager missing 'resonance_models' key. Cannot switch model.")
            except Exception as e:
                 self.log(f"Error switching model: {e}")
        elif self.scorer is None:
            self.log("ResonanceScorer not initialized. Cannot switch model.")
        else:
             self.log("PathManager service not found. Cannot switch model.")

    def view_meritchain(self):
        """
        Open dialog to view MeritChain entries.
        """
        dialog = MeritChainViewDialog(self.dispatcher, self)
        dialog.exec_()

    ###############################################################################
    #                                LOGGING                                      #
    ###############################################################################

    def log(self, message: str):
        """
        Appends a log message to the log output and routes it to the Python logger.
        """
        self.log_output.append(message)
        # Use the logger obtained from services
        if self.logger:
            self.logger.info(f"[MeredithTab] {message}")
        else: # Fallback if logger wasn't retrieved
             print(f"[MeredithTab LOG - NO LOGGER]: {message}") 

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
          - A status indicator showing if profile is saved to MeritChain.
          - A 'Message' button to open the profile URL in a browser.
          - An 'Analyze' button to run the MeredithDispatcher for resonance analysis.
          - A "Resonance Score" computed via the ResonanceScorer.
        """
        self.results_table.setRowCount(len(profiles))

        for row, profile in enumerate(profiles):
            # Status indicator (column 0)
            username = profile.get("username", "")
            
            # Check if this profile exists in MeritChain
            meritchain_entry = self.dispatcher.find_match_by_username(username)
            status_item = QTableWidgetItem()
            
            if meritchain_entry:
                # Profile is in MeritChain, show saved icon
                status_item.setText("✓")
                status_item.setForeground(QBrush(QColor("green")))
                status_item.setToolTip("Saved to MeritChain")
                # Also add this to analyzed profiles set
                self.analyzed_profiles.add(username)
            elif username in self.analyzed_profiles:
                # Profile was analyzed but not saved
                status_item.setText("✗")
                status_item.setForeground(QBrush(QColor("red")))
                status_item.setToolTip("Analyzed but not saved")
            else:
                # Profile not analyzed
                status_item.setText("")
                status_item.setToolTip("Not analyzed")
                
            status_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 0, status_item)

            # Standard data columns (1-5)
            self.results_table.setItem(row, 1, QTableWidgetItem(profile.get("platform", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(username))
            self.results_table.setItem(row, 3, QTableWidgetItem(profile.get("bio", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(profile.get("location", "")))
            self.results_table.setItem(row, 5, QTableWidgetItem(profile.get("url", "")))

            # 'Message' button column (6)
            url_for_this_profile = profile.get("url", "")
            message_button = QPushButton("Message")
            message_button.clicked.connect(
                lambda _, url=url_for_this_profile: self.open_profile_in_browser(url)
            )
            self.results_table.setCellWidget(row, 6, message_button)

            # 'Analyze' button column (7): triggers MeredithDispatcher to process profile
            analyze_button = QPushButton("Analyze")
            
            # If already analyzed, change button text and style
            if username in self.analyzed_profiles:
                analyze_button.setText("Re-Analyze")
                
            analyze_button.clicked.connect(
                lambda _, p=profile: self.analyze_profile(p)
            )
            self.results_table.setCellWidget(row, 7, analyze_button)

            # 'Resonance Score' column (8)
            if meritchain_entry and "resonance_score" in meritchain_entry:
                # Use score from MeritChain if available
                score_text = f"{meritchain_entry['resonance_score']}"
                score_item = QTableWidgetItem(score_text)
                score_item.setForeground(QBrush(QColor("green")))
            else:
                # Otherwise use the scorer to compute a preliminary score
                result = self.scorer.score_profile(profile)
                score_text = f"{result['score']:.2f}"
                score_item = QTableWidgetItem(score_text)
                
            self.results_table.setItem(row, 8, score_item)

    def open_profile_in_browser(self, url: str):
        """
        Opens the provided URL in the default web browser.
        """
        if not url:
            self.log("No URL available for this profile.")
            return
        webbrowser.open(url)
        self.log(f"Opened URL: {url}")

    def analyze_profile(self, profile: dict):
        """
        Uses MeredithDispatcher to process a profile and update the UI with the analysis result.
        """
        username = profile.get("username", "unknown")
        self.log(f"Analyzing profile: {username}")
        
        result = self.dispatcher.process_profile(
            profile_data=profile,
            source_platform=profile.get("platform", "Unknown"),
            target_role="love"
        )
        
        if result:
            # Add to analyzed profiles set
            self.analyzed_profiles.add(username)
            
            # Log the result
            resonance_score = result.get("resonance_score", 0)
            saved_to_meritchain = result.get("should_save_to_meritchain", False)
            
            if saved_to_meritchain:
                self.log(f"✅ Analysis complete - {username} saved to MeritChain with score {resonance_score}")
            else:
                self.log(f"Analysis complete - {username} not saved to MeritChain (score {resonance_score})")
                
            # Update the table display
            self.populate_results_table(self.filtered_profiles)
            
            # Show details dialog if saved to MeritChain
            if saved_to_meritchain:
                self.show_analysis_details(result)
        else:
            self.log("Analysis failed or returned no result.")
            
    def show_analysis_details(self, result):
        """
        Shows a dialog with the details of the analysis result.
        """
        username = result.get("username", "Unknown")
        platform = result.get("platform", "Unknown")
        score = result.get("resonance_score", 0)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Analysis Result")
        
        # Create a colorful header based on score
        if score >= 90:
            header_color = "green"
            header_prefix = "🌟 HIGH MATCH"
        elif score >= 75:
            header_color = "blue"
            header_prefix = "✨ GOOD MATCH"
        else:
            header_color = "black"
            header_prefix = "ANALYZED"
            
        header = f"<h3 style='color:{header_color};'>{header_prefix}: {username} from {platform}</h3>"
        
        # Create content
        content = f"<p><b>Resonance Score:</b> {score}</p>"
        
        if "matching_traits" in result and result["matching_traits"]:
            traits = ", ".join(result["matching_traits"])
            content += f"<p><b>Matching Traits:</b> {traits}</p>"
            
        if "summary" in result and result["summary"]:
            content += f"<p><b>Summary:</b> {result['summary']}</p>"
            
        if "suggested_follow_up" in result and result["suggested_follow_up"]:
            content += f"<p><b>Suggested Follow-up:</b> {result['suggested_follow_up']}</p>"
            
        if "first_message" in result and result["first_message"]:
            content += f"<p><b>First Message Template:</b><br>{result['first_message']}</p>"
            
        # Set text
        msg_box.setText(header)
        msg_box.setInformativeText(content)
        
        # Make it wide enough to be readable
        msg_box.setMinimumWidth(500)
        
        # Show the dialog
        msg_box.exec_()

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
        self.analyzed_profiles.clear()
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
        # Do not clear analyzed_profiles as we want to keep track of which
        # profiles have been analyzed across multiple scans

    def toggle_visibility(self):
        """
        Toggles the tab's visibility (useful for private mode hotkeys).
        """
        self.setVisible(not self.isVisible())
