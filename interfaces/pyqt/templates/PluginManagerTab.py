import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer

class PluginManagerTab(QWidget):
    def __init__(self, plugin_registry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry  # Dict or object managing plugins/models
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Plugin Manager")
        self.layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel("🔌 Plugin / Model Manager")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout.addWidget(self.title_label)

        # Plugin Table
        self.plugin_table = QTableWidget(self)
        self.plugin_table.setColumnCount(5)
        self.plugin_table.setHorizontalHeaderLabels([
            "Model / Plugin Name", "Enabled", "Last Execution", "Success Rate", "Actions"
        ])
        self.layout.addWidget(self.plugin_table)

        # Manual Reload Button
        self.reload_all_btn = QPushButton("🔄 Reload All Plugins")
        self.reload_all_btn.clicked.connect(self.reload_all_plugins)
        self.layout.addWidget(self.reload_all_btn)

        # Auto-refresh table every X seconds (optional)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_table)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Initial population
        self.refresh_table()

    def refresh_table(self):
        """Update table with latest plugin info."""
        plugins = self.plugin_registry.get_all_plugins()  # Assumes method returns plugin info dict/list
        self.plugin_table.setRowCount(len(plugins))

        for row, plugin in enumerate(plugins):
            # Plugin Name
            name_item = QTableWidgetItem(plugin.get("name", "Unknown"))
            self.plugin_table.setItem(row, 0, name_item)

            # Enabled Checkbox
            enabled_chk = QCheckBox()
            enabled_chk.setChecked(plugin.get("enabled", False))
            enabled_chk.stateChanged.connect(lambda state, p=plugin: self.toggle_plugin(p, state))
            self.plugin_table.setCellWidget(row, 1, enabled_chk)

            # Last Execution
            last_exec_time = plugin.get("last_execution", None)
            last_exec_display = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_exec_time)) if last_exec_time else "Never"
            last_exec_item = QTableWidgetItem(last_exec_display)
            self.plugin_table.setItem(row, 2, last_exec_item)

            # Success Rate
            success_rate = plugin.get("success_rate", 0.0)
            success_item = QTableWidgetItem(f"{success_rate:.1f}%")
            self.plugin_table.setItem(row, 3, success_item)

            # Reload Button
            reload_btn = QPushButton("🔁 Reload")
            reload_btn.clicked.connect(lambda _, p=plugin: self.reload_plugin(p))
            self.plugin_table.setCellWidget(row, 4, reload_btn)

    def toggle_plugin(self, plugin, state):
        """Enable or disable a plugin."""
        plugin_name = plugin.get("name", "Unknown")
        try:
            if state == Qt.Checked:
                self.plugin_registry.enable_plugin(plugin_name)
                self.show_message("Plugin Enabled", f"{plugin_name} has been enabled.")
            else:
                self.plugin_registry.disable_plugin(plugin_name)
                self.show_message("Plugin Disabled", f"{plugin_name} has been disabled.")
        except Exception as e:
            self.show_message("Error", f"Failed to toggle plugin:\n{e}", error=True)

        self.refresh_table()

    def reload_plugin(self, plugin):
        """Reload a specific plugin."""
        plugin_name = plugin.get("name", "Unknown")
        try:
            self.plugin_registry.reload_plugin(plugin_name)
            self.show_message("Reloaded", f"{plugin_name} reloaded successfully.")
        except Exception as e:
            self.show_message("Error", f"Failed to reload plugin:\n{e}", error=True)

        self.refresh_table()

    def reload_all_plugins(self):
        """Reload all plugins."""
        try:
            self.plugin_registry.reload_all_plugins()
            self.show_message("Reload Complete", "All plugins reloaded successfully.")
        except Exception as e:
            self.show_message("Error", f"Failed to reload all plugins:\n{e}", error=True)

        self.refresh_table()

    def show_message(self, title, message, error=False):
        """Unified message box."""
        if error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

