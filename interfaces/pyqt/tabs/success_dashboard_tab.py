#!/usr/bin/env python3
"""
Success Dashboard Tab

This module provides a PyQt5 UI tab for visualizing task execution metrics,
including success rates, execution times, and error trends.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QTabWidget, 
    QHeaderView, QComboBox, QDateEdit, QFormLayout,
    QGroupBox, QScrollArea, QGridLayout, QFrame, QSplitter
)
from PyQt5.QtGui import QColor, QFont, QPalette, QBrush
from PyQt5.QtCore import Qt, QDate

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

logger = logging.getLogger(__name__)

# Import optional plotting library if available
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    logger.warning("Matplotlib not available; charts will not be rendered")
    HAS_MATPLOTLIB = False


class SuccessDashboardTab(QWidget):
    """Tab for visualizing task execution metrics and success rates."""
    
    def __init__(self, parent=None, orchestrator_bridge=None, memory_path="memory/task_history.json"):
        """
        Initialize the SuccessDashboardTab.
        
        Args:
            parent: Parent widget
            orchestrator_bridge: Optional orchestrator bridge for real-time updates
            memory_path: Path to task execution memory file
        """
        super().__init__(parent)
        self.orchestrator_bridge = orchestrator_bridge
        self.memory_path = memory_path
        self.tasks = []
        self.setup_ui()
        self.load_task_data()
        
        # Connect to bridge if available
        if self.orchestrator_bridge:
            self.orchestrator_bridge.task_execution_completed.connect(self.on_task_execution_completed)
            self.orchestrator_bridge.tasks_requeued.connect(lambda _: self.refresh_dashboard())
    
    def setup_ui(self):
        """Set up the tab UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("Task Execution Dashboard")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Time period selector
        time_selector_label = QLabel("Period:")
        header_layout.addWidget(time_selector_label)
        
        self.time_period_combo = QComboBox()
        self.time_period_combo.addItems([
            "Last 24 Hours",
            "Last 7 Days",
            "Last 30 Days",
            "All Time"
        ])
        self.time_period_combo.currentTextChanged.connect(self.refresh_dashboard)
        header_layout.addWidget(self.time_period_combo)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_dashboard)
        header_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(header_layout)
        
        # Create tab widget for different dashboard views
        self.dashboard_tabs = QTabWidget()
        
        # Summary view
        self.summary_tab = QWidget()
        summary_layout = QVBoxLayout(self.summary_tab)
        
        # Summary cards in grid layout
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        
        summary_content = QWidget()
        self.summary_grid = QGridLayout(summary_content)
        
        # Create summary cards (will be populated in refresh_dashboard)
        self.create_summary_cards()
        
        summary_scroll.setWidget(summary_content)
        summary_layout.addWidget(summary_scroll)
        
        self.dashboard_tabs.addTab(self.summary_tab, "Summary")
        
        # Charts view
        if HAS_MATPLOTLIB:
            self.charts_tab = QWidget()
            charts_layout = QVBoxLayout(self.charts_tab)
            
            # Create chart containers
            charts_scroll = QScrollArea()
            charts_scroll.setWidgetResizable(True)
            
            charts_content = QWidget()
            self.charts_grid = QGridLayout(charts_content)
            
            # Create charts (will be populated in refresh_dashboard)
            self.create_chart_widgets()
            
            charts_scroll.setWidget(charts_content)
            charts_layout.addWidget(charts_scroll)
            
            self.dashboard_tabs.addTab(self.charts_tab, "Charts")
        
        # Details view
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        
        # Create table for detailed metrics
        self.details_table = QTableWidget(0, 6)  # Template, Attempts, Success, Failure, Avg Time, Error Types
        self.details_table.setHorizontalHeaderLabels([
            "Template", "Attempts", "Success Rate", "Failures", "Avg Time (s)", "Common Errors"
        ])
        self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        details_layout.addWidget(self.details_table)
        
        self.dashboard_tabs.addTab(self.details_tab, "Details")
        
        main_layout.addWidget(self.dashboard_tabs)
        
        # Status bar
        self.status_bar = QLabel("")
        self.status_bar.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_bar)
    
    def create_summary_cards(self):
        """Create summary metric cards."""
        # Clear existing widgets from grid
        while self.summary_grid.count():
            item = self.summary_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Card 1: Total Tasks
        self.total_tasks_card = self.create_metric_card("Total Tasks", "0")
        self.summary_grid.addWidget(self.total_tasks_card, 0, 0)
        
        # Card 2: Success Rate
        self.success_rate_card = self.create_metric_card("Success Rate", "0%")
        self.summary_grid.addWidget(self.success_rate_card, 0, 1)
        
        # Card 3: Average Execution Time
        self.avg_time_card = self.create_metric_card("Avg Execution Time", "0s")
        self.summary_grid.addWidget(self.avg_time_card, 0, 2)
        
        # Card 4: Failed Tasks
        self.failed_tasks_card = self.create_metric_card("Failed Tasks", "0")
        self.summary_grid.addWidget(self.failed_tasks_card, 1, 0)
        
        # Card 5: Requeued Tasks
        self.requeued_tasks_card = self.create_metric_card("Requeued Tasks", "0")
        self.summary_grid.addWidget(self.requeued_tasks_card, 1, 1)
        
        # Card 6: Most Used Template
        self.most_used_template_card = self.create_metric_card("Most Used Template", "None")
        self.summary_grid.addWidget(self.most_used_template_card, 1, 2)
    
    def create_metric_card(self, title, value):
        """
        Create a card widget for displaying a metric.
        
        Args:
            title: Card title
            value: Metric value
            
        Returns:
            QGroupBox containing the metric card
        """
        card = QGroupBox(title)
        card.setStyleSheet("""
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                background-color: #f8f8f8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(card)
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(value_label)
        
        # Store the value label for later updates
        card.value_label = value_label
        
        return card
    
    def create_chart_widgets(self):
        """Create chart widgets using matplotlib."""
        if not HAS_MATPLOTLIB:
            return
            
        # Clear existing widgets from grid
        while self.charts_grid.count():
            item = self.charts_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Chart 1: Success Rate Over Time
        self.success_rate_chart = self.create_chart_container("Success Rate Over Time")
        self.charts_grid.addWidget(self.success_rate_chart, 0, 0)
        
        # Chart 2: Execution Times by Template
        self.exec_time_chart = self.create_chart_container("Execution Times by Template")
        self.charts_grid.addWidget(self.exec_time_chart, 0, 1)
        
        # Chart 3: Error Types Distribution
        self.error_types_chart = self.create_chart_container("Error Types Distribution")
        self.charts_grid.addWidget(self.error_types_chart, 1, 0)
        
        # Chart 4: Task Volume by Template
        self.task_volume_chart = self.create_chart_container("Task Volume by Template")
        self.charts_grid.addWidget(self.task_volume_chart, 1, 1)
    
    def create_chart_container(self, title):
        """
        Create a container for a chart.
        
        Args:
            title: Chart title
            
        Returns:
            QGroupBox containing the chart
        """
        container = QGroupBox(title)
        layout = QVBoxLayout(container)
        
        figure = Figure(figsize=(5, 4), tight_layout=True)
        canvas = FigureCanvas(figure)
        layout.addWidget(canvas)
        
        # Store figure and canvas for later updates
        container.figure = figure
        container.canvas = canvas
        
        return container
    
    def load_task_data(self):
        """Load task execution data from memory file."""
        try:
            if not os.path.exists(self.memory_path):
                self.status_bar.setText(f"Memory file not found: {self.memory_path}")
                return
                
            with open(self.memory_path, 'r') as f:
                memory_data = json.load(f)
                
            # Get tasks from memory
            self.tasks = memory_data.get("tasks", [])
            
            # Refresh dashboard with loaded data
            self.refresh_dashboard()
            
            self.status_bar.setText(f"Loaded {len(self.tasks)} tasks from memory")
            
        except Exception as e:
            self.status_bar.setText(f"Error loading task data: {e}")
            logger.error(f"Error loading task data: {e}")
    
    def on_task_execution_completed(self, data):
        """
        Handle task execution completed event.
        
        Args:
            data: Event data
        """
        # Refresh dashboard to include the new task
        self.refresh_dashboard()
    
    def refresh_dashboard(self):
        """Refresh dashboard metrics and charts."""
        # Get time period filter
        period = self.time_period_combo.currentText()
        filtered_tasks = self.filter_tasks_by_period(period)
        
        # Update summary metrics
        self.update_summary_metrics(filtered_tasks)
        
        # Update charts if available
        if HAS_MATPLOTLIB:
            self.update_charts(filtered_tasks)
        
        # Update details table
        self.update_details_table(filtered_tasks)
        
        self.status_bar.setText(f"Dashboard refreshed with {len(filtered_tasks)} tasks")
    
    def filter_tasks_by_period(self, period):
        """
        Filter tasks by time period.
        
        Args:
            period: Time period string
            
        Returns:
            List of filtered tasks
        """
        now = datetime.now()
        
        if period == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
        elif period == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        elif period == "Last 30 Days":
            cutoff = now - timedelta(days=30)
        else:  # All Time
            return self.tasks
            
        # Filter tasks by end_time or start_time
        filtered = []
        for task in self.tasks:
            # Try end_time first, then fall back to start_time
            time_str = task.get("end_time") or task.get("start_time")
            if not time_str:
                continue
                
            try:
                task_time = datetime.fromisoformat(time_str)
                if task_time >= cutoff:
                    filtered.append(task)
            except ValueError:
                # Skip tasks with invalid timestamps
                continue
                
        return filtered
    
    def update_summary_metrics(self, tasks):
        """
        Update summary metric cards.
        
        Args:
            tasks: List of tasks to analyze
        """
        # Calculate metrics
        total_tasks = len(tasks)
        
        # Success rate
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        success_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        # Average execution time
        times = []
        for task in tasks:
            duration = task.get("duration_seconds")
            if duration is not None:
                times.append(duration)
        avg_time = sum(times) / len(times) if times else 0
        
        # Failed tasks
        failed = sum(1 for t in tasks if t.get("status") in ["failed", "error"])
        
        # Requeued tasks
        requeued = sum(1 for t in tasks if t.get("requeued", False))
        
        # Most used template
        template_counts = defaultdict(int)
        for task in tasks:
            template = task.get("template_name", "unknown")
            template_counts[template] += 1
            
        most_used = max(template_counts.items(), key=lambda x: x[1])[0] if template_counts else "None"
        
        # Update cards
        self.total_tasks_card.value_label.setText(str(total_tasks))
        self.success_rate_card.value_label.setText(f"{success_rate:.1f}%")
        self.avg_time_card.value_label.setText(f"{avg_time:.2f}s")
        self.failed_tasks_card.value_label.setText(str(failed))
        self.requeued_tasks_card.value_label.setText(str(requeued))
        self.most_used_template_card.value_label.setText(most_used)
    
    def update_charts(self, tasks):
        """
        Update dashboard charts.
        
        Args:
            tasks: List of tasks to visualize
        """
        if not HAS_MATPLOTLIB or not tasks:
            return
            
        # Chart 1: Success Rate Over Time
        self._update_success_rate_chart(tasks)
        
        # Chart 2: Execution Times by Template
        self._update_exec_time_chart(tasks)
        
        # Chart 3: Error Types Distribution
        self._update_error_types_chart(tasks)
        
        # Chart 4: Task Volume by Template
        self._update_task_volume_chart(tasks)
    
    def _update_success_rate_chart(self, tasks):
        """Update success rate over time chart."""
        figure = self.success_rate_chart.figure
        figure.clear()
        
        # Group tasks by day
        dates = defaultdict(lambda: {"total": 0, "success": 0})
        
        for task in tasks:
            # Get date from end_time or start_time
            time_str = task.get("end_time") or task.get("start_time")
            if not time_str:
                continue
                
            try:
                task_date = datetime.fromisoformat(time_str).date()
                date_key = task_date.isoformat()
                
                dates[date_key]["total"] += 1
                if task.get("status") == "completed":
                    dates[date_key]["success"] += 1
            except ValueError:
                continue
        
        # Calculate success rates
        date_keys = sorted(dates.keys())
        success_rates = []
        
        for date in date_keys:
            day_data = dates[date]
            rate = (day_data["success"] / day_data["total"] * 100) if day_data["total"] > 0 else 0
            success_rates.append(rate)
        
        # Create chart
        ax = figure.add_subplot(111)
        ax.plot(date_keys, success_rates, marker='o', linestyle='-', color='green')
        ax.set_ylim(0, 100)
        ax.set_ylabel('Success Rate (%)')
        ax.set_xlabel('Date')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Format x-axis for better readability
        if len(date_keys) > 10:
            ax.set_xticks(date_keys[::len(date_keys)//10])
        
        figure.tight_layout()
        self.success_rate_chart.canvas.draw()
    
    def _update_exec_time_chart(self, tasks):
        """Update execution times by template chart."""
        figure = self.exec_time_chart.figure
        figure.clear()
        
        # Group execution times by template
        template_times = defaultdict(list)
        
        for task in tasks:
            template = task.get("template_name", "unknown")
            duration = task.get("duration_seconds")
            if duration is not None:
                template_times[template].append(duration)
        
        # Calculate average execution time per template
        templates = []
        avg_times = []
        
        for template, times in template_times.items():
            if times:
                templates.append(template)
                avg_times.append(sum(times) / len(times))
        
        # Create chart (bar chart)
        ax = figure.add_subplot(111)
        bars = ax.bar(templates, avg_times, color='skyblue')
        ax.set_ylabel('Average Execution Time (s)')
        ax.set_xlabel('Template')
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Rotate template names for better readability
        ax.set_xticklabels(templates, rotation=45, ha='right')
        
        figure.tight_layout()
        self.exec_time_chart.canvas.draw()
    
    def _update_error_types_chart(self, tasks):
        """Update error types distribution chart."""
        figure = self.error_types_chart.figure
        figure.clear()
        
        # Count error types
        error_counts = defaultdict(int)
        
        for task in tasks:
            if task.get("status") in ["failed", "error"]:
                # Try to get error type from validation result or error message
                error_type = "Unknown"
                
                # Check validation result
                validation = task.get("validation", {})
                if validation:
                    checks = validation.get("checks", [])
                    failed_checks = [c.get("type", "unknown") for c in checks if not c.get("passed", False)]
                    if failed_checks:
                        error_type = ", ".join(failed_checks)
                
                # Fallback to error message
                if error_type == "Unknown" and "error" in task:
                    error_msg = task["error"]
                    if "timeout" in error_msg.lower():
                        error_type = "Timeout"
                    elif "connection" in error_msg.lower():
                        error_type = "Connection Error"
                    elif "validation" in error_msg.lower():
                        error_type = "Validation Error"
                
                error_counts[error_type] += 1
        
        # Create chart (pie chart)
        if error_counts:
            ax = figure.add_subplot(111)
            ax.pie(error_counts.values(), labels=error_counts.keys(), autopct='%1.1f%%', 
                   startangle=90, shadow=True)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No errors recorded", ha='center', va='center')
            ax.axis('off')
        
        figure.tight_layout()
        self.error_types_chart.canvas.draw()
    
    def _update_task_volume_chart(self, tasks):
        """Update task volume by template chart."""
        figure = self.task_volume_chart.figure
        figure.clear()
        
        # Count tasks by template
        template_counts = defaultdict(int)
        
        for task in tasks:
            template = task.get("template_name", "unknown")
            template_counts[template] += 1
        
        # Sort by count
        sorted_templates = sorted(template_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Limit to top 10 templates for readability
        if len(sorted_templates) > 10:
            sorted_templates = sorted_templates[:10]
            
        templates = [t[0] for t in sorted_templates]
        counts = [t[1] for t in sorted_templates]
        
        # Create chart (horizontal bar chart)
        ax = figure.add_subplot(111)
        bars = ax.barh(templates, counts, color='lightgreen')
        ax.set_xlabel('Number of Tasks')
        ax.set_ylabel('Template')
        ax.grid(True, axis='x', linestyle='--', alpha=0.7)
        
        # Add counts at the end of each bar
        for i, v in enumerate(counts):
            ax.text(v + 0.1, i, str(v), va='center')
        
        figure.tight_layout()
        self.task_volume_chart.canvas.draw()
    
    def update_details_table(self, tasks):
        """
        Update details table with template metrics.
        
        Args:
            tasks: List of tasks to analyze
        """
        # Group tasks by template
        template_data = defaultdict(lambda: {
            "attempts": 0,
            "success": 0,
            "failure": 0,
            "times": [],
            "errors": defaultdict(int)
        })
        
        for task in tasks:
            template = task.get("template_name", "unknown")
            
            # Update counts
            template_data[template]["attempts"] += 1
            
            if task.get("status") == "completed":
                template_data[template]["success"] += 1
            elif task.get("status") in ["failed", "error"]:
                template_data[template]["failure"] += 1
                
                # Track error type
                error_type = "Unknown"
                validation = task.get("validation", {})
                if validation:
                    checks = validation.get("checks", [])
                    failed_checks = [c.get("type", "unknown") for c in checks if not c.get("passed", False)]
                    if failed_checks:
                        error_type = ", ".join(failed_checks)
                
                if error_type == "Unknown" and "error" in task:
                    error_msg = task["error"]
                    if "timeout" in error_msg.lower():
                        error_type = "Timeout"
                    elif "connection" in error_msg.lower():
                        error_type = "Connection Error"
                    elif "validation" in error_msg.lower():
                        error_type = "Validation Error"
                
                template_data[template]["errors"][error_type] += 1
            
            # Track execution time
            duration = task.get("duration_seconds")
            if duration is not None:
                template_data[template]["times"].append(duration)
        
        # Populate table
        self.details_table.setRowCount(len(template_data))
        
        for i, (template, data) in enumerate(sorted(template_data.items())):
            # Template
            self.details_table.setItem(i, 0, QTableWidgetItem(template))
            
            # Attempts
            self.details_table.setItem(i, 1, QTableWidgetItem(str(data["attempts"])))
            
            # Success Rate
            success_rate = (data["success"] / data["attempts"] * 100) if data["attempts"] > 0 else 0
            rate_item = QTableWidgetItem(f"{success_rate:.1f}%")
            # Color based on rate
            if success_rate >= 90:
                rate_item.setForeground(QColor(0, 128, 0))  # Green
            elif success_rate >= 50:
                rate_item.setForeground(QColor(255, 140, 0))  # Orange
            else:
                rate_item.setForeground(QColor(255, 0, 0))  # Red
            self.details_table.setItem(i, 2, rate_item)
            
            # Failures
            self.details_table.setItem(i, 3, QTableWidgetItem(str(data["failure"])))
            
            # Avg Time
            avg_time = sum(data["times"]) / len(data["times"]) if data["times"] else 0
            self.details_table.setItem(i, 4, QTableWidgetItem(f"{avg_time:.2f}"))
            
            # Common Errors
            if data["errors"]:
                # Sort errors by frequency
                sorted_errors = sorted(data["errors"].items(), key=lambda x: x[1], reverse=True)
                error_str = ", ".join(f"{error} ({count})" for error, count in sorted_errors[:3])
                if len(sorted_errors) > 3:
                    error_str += f" +{len(sorted_errors) - 3} more"
            else:
                error_str = "None"
            self.details_table.setItem(i, 5, QTableWidgetItem(error_str))


class SuccessDashboardTabFactory:
    """Factory for creating SuccessDashboardTab instances."""
    
    @staticmethod
    def create(orchestrator_bridge=None, memory_path="memory/task_history.json", parent=None) -> SuccessDashboardTab:
        """
        Create a SuccessDashboardTab instance.
        
        Args:
            orchestrator_bridge: Optional orchestrator bridge to connect to
            memory_path: Path to task execution memory file
            parent: Parent widget
            
        Returns:
            SuccessDashboardTab instance
        """
        tab = SuccessDashboardTab(
            parent=parent, 
            orchestrator_bridge=orchestrator_bridge,
            memory_path=memory_path
        )
        return tab


if __name__ == "__main__":
    # For testing as standalone
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = SuccessDashboardTabFactory.create()
    window.show()
    sys.exit(app.exec_()) 