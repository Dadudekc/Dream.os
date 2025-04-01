"""
Settings Tab Module

This module provides the settings interface for Dream.OS, allowing users to
configure application-wide settings, themes, and preferences.
"""

import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QScrollArea, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QSpinBox, QColorDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor

class SettingsTab(QWidget):
    """
    Settings tab for configuring application-wide preferences.
    Manages themes, performance settings, and general configurations.
    """
    # Signals
    settings_updated = pyqtSignal(str, dict)  # section, updated_settings
    theme_changed = pyqtSignal(dict)  # theme_settings
    log_message = pyqtSignal(str)
    
    def __init__(
        self,
        config_manager=None,
        theme_manager=None,
        logger=None,
        parent=None
    ):
        super().__init__(parent)
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.logger = logger or logging.getLogger(__name__)
        self.parent = parent
        
        # Initialize settings
        self._current_settings = {}
        self._load_settings()
        
        self.initUI()
        
    def _load_settings(self) -> None:
        """Load current settings from config manager."""
        try:
            if self.config_manager:
                self._current_settings = self.config_manager.get_settings()
            else:
                self._current_settings = {}
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            self._current_settings = {}
            
    def initUI(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Add header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add settings sections
        appearance_group = self._create_appearance_section()
        scroll_layout.addWidget(appearance_group)
        scroll_layout.addSpacing(20)
        
        performance_group = self._create_performance_section()
        scroll_layout.addWidget(performance_group)
        scroll_layout.addSpacing(20)
        
        advanced_group = self._create_advanced_section()
        scroll_layout.addWidget(advanced_group)
        
        # Add save/reset buttons
        buttons_layout = QVBoxLayout()
        
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        save_button.setMinimumHeight(40)
        buttons_layout.addWidget(save_button)
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(reset_button)
        
        scroll_layout.addSpacing(20)
        scroll_layout.addLayout(buttons_layout)
        
        # Add stretch at the bottom
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def _create_appearance_section(self) -> QGroupBox:
        """Create the appearance settings section."""
        group = QGroupBox("Appearance")
        layout = QFormLayout()
        
        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        self.theme_combo.setCurrentText(
            self._current_settings.get("theme", "System")
        )
        layout.addRow("Theme:", self.theme_combo)
        
        # Accent color
        self.accent_button = QPushButton()
        self.accent_button.clicked.connect(self._choose_accent_color)
        self._update_accent_button_color(
            self._current_settings.get("accent_color", "#007AFF")
        )
        layout.addRow("Accent Color:", self.accent_button)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(
            self._current_settings.get("font_size", 12)
        )
        layout.addRow("Font Size:", self.font_size)
        
        group.setLayout(layout)
        return group
        
    def _create_performance_section(self) -> QGroupBox:
        """Create the performance settings section."""
        group = QGroupBox("Performance")
        layout = QFormLayout()
        
        # Hardware acceleration
        self.hw_accel = QCheckBox()
        self.hw_accel.setChecked(
            self._current_settings.get("hardware_acceleration", True)
        )
        layout.addRow("Hardware Acceleration:", self.hw_accel)
        
        # Cache size
        self.cache_size = QSpinBox()
        self.cache_size.setRange(100, 10000)
        self.cache_size.setSuffix(" MB")
        self.cache_size.setValue(
            self._current_settings.get("cache_size_mb", 1000)
        )
        layout.addRow("Cache Size:", self.cache_size)
        
        group.setLayout(layout)
        return group
        
    def _create_advanced_section(self) -> QGroupBox:
        """Create the advanced settings section."""
        group = QGroupBox("Advanced")
        layout = QFormLayout()
        
        # Debug mode
        self.debug_mode = QCheckBox()
        self.debug_mode.setChecked(
            self._current_settings.get("debug_mode", False)
        )
        layout.addRow("Debug Mode:", self.debug_mode)
        
        # API endpoint
        self.api_endpoint = QLineEdit()
        self.api_endpoint.setText(
            self._current_settings.get("api_endpoint", "")
        )
        layout.addRow("API Endpoint:", self.api_endpoint)
        
        group.setLayout(layout)
        return group
        
    @pyqtSlot()
    def _choose_accent_color(self) -> None:
        """Open color picker for accent color selection."""
        current = QColor(self._current_settings.get("accent_color", "#007AFF"))
        color = QColorDialog.getColor(current, self, "Choose Accent Color")
        
        if color.isValid():
            self._update_accent_button_color(color.name())
            
    def _update_accent_button_color(self, color: str) -> None:
        """Update the accent color button appearance."""
        self.accent_button.setStyleSheet(
            f"background-color: {color}; min-width: 60px; min-height: 30px;"
        )
        self.accent_button.setText(color)
        
    @pyqtSlot()
    def save_settings(self) -> None:
        """Save current settings to config manager."""
        try:
            settings = {
                "theme": self.theme_combo.currentText(),
                "accent_color": self.accent_button.text(),
                "font_size": self.font_size.value(),
                "hardware_acceleration": self.hw_accel.isChecked(),
                "cache_size_mb": self.cache_size.value(),
                "debug_mode": self.debug_mode.isChecked(),
                "api_endpoint": self.api_endpoint.text().strip()
            }
            
            if self.config_manager:
                self.config_manager.update_settings(settings)
                
            self._current_settings = settings
            self.settings_updated.emit("all", settings)
            self.theme_changed.emit({
                "theme": settings["theme"],
                "accent_color": settings["accent_color"]
            })
            
            self.log_action("Settings saved successfully")
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            self._show_error("Save Failed", f"Failed to save settings: {e}")
            
    @pyqtSlot()
    def reset_settings(self) -> None:
        """Reset settings to default values."""
        try:
            if QMessageBox.question(
                self,
                "Reset Settings",
                "Are you sure you want to reset all settings to default values?"
            ) == QMessageBox.StandardButton.Yes:
                if self.config_manager:
                    self.config_manager.reset_to_defaults()
                self._load_settings()
                self.initUI()
                self.log_action("Settings reset to defaults")
                
        except Exception as e:
            self.logger.error(f"Failed to reset settings: {e}")
            self._show_error("Reset Failed", f"Failed to reset settings: {e}")
            
    def log_action(self, message: str) -> None:
        """Log an action to both logger and UI."""
        self.logger.info(message)
        self.log_message.emit(f"[SETTINGS TAB]: {message}")
        
        # Try to use parent's signal if available
        try:
            if hasattr(self.parent, 'append_output_signal'):
                self.parent.append_output_signal.emit(f"[SETTINGS TAB]: {message}")
        except Exception:
            pass
            
    def _show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)