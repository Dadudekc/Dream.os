from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json
import os
import logging

from meredith.profile_scraper import ScraperManager, ProfileFilter

class ScraperThread(QThread):
    scan_completed = pyqtSignal(list)
    log_update = pyqtSignal(str)

    def run(self):
        self.log_update.emit("Starting Meredith full sync scan...")
        scraper_manager = ScraperManager(headless=True)
        scraper_manager.register_default_scrapers()

        self.log_update.emit("Scraping profiles...")
        all_profiles = scraper_manager.run_all()
        self.log_update.emit(f"Scraped {len(all_profiles)} profiles.")

        self.log_update.emit("Applying location filters...")
        local_profiles = ProfileFilter.filter_by_location(all_profiles, ["houston", "htx"], "77090")

        self.log_update.emit("Filtering by gender (female)...")
        final_profiles = ProfileFilter.filter_by_gender(local_profiles, gender="female")
        self.log_update.emit(f"{len(final_profiles)} profiles after filtering.")

        scraper_manager.close()
        self.scan_completed.emit(final_profiles)

class MeredithTab(QWidget):
    def __init__(self, parent=None, private_mode=True):
        super().__init__(parent)
        self.private_mode = private_mode
        self.filtered_profiles = []

        self.init_ui()
        self.setWindowTitle("Meredith - Private Resonance Scanner")

        if self.private_mode:
            self.hide()

    def init_ui(self):
        layout = QVBoxLayout()

        header_label = QLabel("Meredith: Private Resonance Scanner")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)

        button_layout = QHBoxLayout()

        self.run_button = QPushButton("Run Full Scan")
        self.run_button.clicked.connect(self.run_full_scan)
        button_layout.addWidget(self.run_button)

        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)

        layout.addLayout(button_layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(100)
        layout.addWidget(self.log_output)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Platform", "Username", "Bio", "Location", "URL"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def log(self, message):
        self.log_output.append(message)
        logging.info(f"[MeredithTab] {message}")

    def run_full_scan(self):
        self.run_button.setEnabled(False)
        self.results_table.setRowCount(0)
        self.log("Launching Meredith scan thread...")
        self.scraper_thread = ScraperThread()
        self.scraper_thread.scan_completed.connect(self.on_scan_completed)
        self.scraper_thread.log_update.connect(self.log)
        self.scraper_thread.start()

    def on_scan_completed(self, profiles):
        self.filtered_profiles = profiles
        self.populate_results_table(profiles)
        self.export_button.setEnabled(True)
        self.run_button.setEnabled(True)
        self.log("Scan completed successfully.")

    def populate_results_table(self, profiles):
        self.results_table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            self.results_table.setItem(row, 0, QTableWidgetItem(profile.get("platform", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(profile.get("username", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(profile.get("bio", "")))
            self.results_table.setItem(row, 3, QTableWidgetItem(profile.get("location", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(profile.get("url", "")))

    def export_results(self):
        if not self.filtered_profiles:
            self.log("No results to export.")
            return

        default_path = os.path.join(os.getcwd(), "outputs", "meredith_profiles.json")
        os.makedirs(os.path.dirname(default_path), exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Profiles", default_path, "JSON Files (*.json)")
        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.filtered_profiles, f, indent=4)
            self.log(f"Exported {len(self.filtered_profiles)} profiles to {file_path}.")