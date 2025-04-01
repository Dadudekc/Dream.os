"""
Metrics Viewer Tab Module

This module provides a tab for visualizing task metrics, recovery performance,
and system health statistics.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox,
    QPushButton, QFrame, QSplitter, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtChart import (
    QChart, QChartView, QLineSeries, QValueAxis,
    QBarSeries, QBarSet, QBarCategoryAxis
)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

class MetricsChart(QWidget):
    """Widget for displaying metrics charts."""
    
    def __init__(self, title: str):
        super().__init__()
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Add title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        layout.addWidget(title_label)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
    
    def plot_line(self, x: List[Any], y: List[float], label: str):
        """Plot a line chart."""
        self.ax.clear()
        self.ax.plot(x, y, label=label)
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()
    
    def plot_bar(self, categories: List[str], values: List[float]):
        """Plot a bar chart."""
        self.ax.clear()
        self.ax.bar(categories, values)
        self.ax.tick_params(axis='x', rotation=45)
        self.canvas.draw()
    
    def plot_heatmap(self, data: List[List[float]], labels: List[str]):
        """Plot a heatmap."""
        self.ax.clear()
        im = self.ax.imshow(data)
        self.ax.set_xticks(range(len(labels)))
        self.ax.set_xticklabels(labels, rotation=45)
        self.figure.colorbar(im)
        self.canvas.draw()

class MetricsViewerTab(QWidget):
    """Tab for displaying and analyzing metrics."""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, services: Dict[str, Any]):
        """
        Initialize the metrics viewer tab.
        
        Args:
            services: Dictionary of application services
        """
        super().__init__()
        self.services = services
        self._init_ui()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        # Time range selector
        self.time_range = QComboBox()
        self.time_range.addItems([
            "Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days"
        ])
        self.time_range.currentTextChanged.connect(self.refresh_data)
        
        # Metric type selector
        self.metric_type = QComboBox()
        self.metric_type.addItems([
            "Recovery Performance", "Task Success Rate", "Execution Time",
            "Stall Distribution"
        ])
        self.metric_type.currentTextChanged.connect(self.refresh_data)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        
        header_layout.addWidget(QLabel("Time Range:"))
        header_layout.addWidget(self.time_range)
        header_layout.addWidget(QLabel("Metric Type:"))
        header_layout.addWidget(self.metric_type)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Create splitter for charts and tables
        splitter = QSplitter(Qt.Vertical)
        
        # Add charts
        charts_widget = QWidget()
        charts_layout = QHBoxLayout()
        
        self.performance_chart = MetricsChart("Recovery Performance")
        self.distribution_chart = MetricsChart("Task Distribution")
        
        charts_layout.addWidget(self.performance_chart)
        charts_layout.addWidget(self.distribution_chart)
        charts_widget.setLayout(charts_layout)
        
        splitter.addWidget(charts_widget)
        
        # Add metrics tables
        tables_widget = QWidget()
        tables_layout = QHBoxLayout()
        
        # Recovery actions table
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(5)
        self.actions_table.setHorizontalHeaderLabels([
            "Action", "Success Rate", "Avg Time", "Usage Count", "Last Used"
        ])
        header = self.actions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Task metrics table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels([
            "Task ID", "Type", "Status", "Recovery Count",
            "Duration", "Result"
        ])
        header = self.tasks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        tables_layout.addWidget(self.actions_table)
        tables_layout.addWidget(self.tasks_table)
        tables_widget.setLayout(tables_layout)
        
        splitter.addWidget(tables_widget)
        
        # Add insights panel
        insights_frame = QFrame()
        insights_frame.setFrameStyle(QFrame.StyledPanel)
        insights_layout = QVBoxLayout()
        
        insights_header = QLabel("Insights & Recommendations")
        insights_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.insights_label = QLabel()
        self.insights_label.setWordWrap(True)
        
        insights_layout.addWidget(insights_header)
        insights_layout.addWidget(self.insights_label)
        insights_frame.setLayout(insights_layout)
        
        splitter.addWidget(insights_frame)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def refresh_data(self):
        """Refresh all metrics data."""
        try:
            # Get metrics from recovery engine
            recovery_engine = self.services.get("recovery")
            if not recovery_engine:
                logger.error("Recovery engine not available")
                return
                
            stats = recovery_engine.get_recovery_stats()
            
            # Update performance chart
            self._update_performance_chart(stats)
            
            # Update distribution chart
            self._update_distribution_chart(stats)
            
            # Update tables
            self._update_actions_table(stats)
            self._update_tasks_table(stats)
            
            # Update insights
            self._update_insights(stats)
            
            self.refresh_requested.emit()
            
        except Exception as e:
            logger.error(f"Failed to refresh metrics: {e}")
    
    def _update_performance_chart(self, stats: Dict[str, Any]):
        """Update the performance chart."""
        try:
            strategy_performance = stats["strategy_performance"]
            
            # Extract data for plotting
            actions = list(strategy_performance.keys())
            success_rates = [data["success_rate"] for data in strategy_performance.values()]
            
            # Plot bar chart
            self.performance_chart.plot_bar(actions, success_rates)
            
        except Exception as e:
            logger.error(f"Failed to update performance chart: {e}")
    
    def _update_distribution_chart(self, stats: Dict[str, Any]):
        """Update the distribution chart."""
        try:
            metric_type = self.metric_type.currentText()
            
            if metric_type == "Stall Distribution":
                # Create stall distribution heatmap
                active_recoveries = stats["active_recoveries"]
                hours = list(range(24))
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                
                # Initialize heatmap data
                data = [[0] * len(hours) for _ in range(len(days))]
                
                # Populate data
                for recovery in active_recoveries:
                    timestamp = datetime.fromisoformat(
                        recovery["metrics"]["start_time"]
                    )
                    day_idx = timestamp.weekday()
                    hour_idx = timestamp.hour
                    data[day_idx][hour_idx] += 1
                
                self.distribution_chart.plot_heatmap(data, [f"{h:02d}:00" for h in hours])
                
            else:
                # Plot time series of selected metric
                timestamps = []
                values = []
                
                for task in stats.get("task_history", []):
                    timestamps.append(datetime.fromisoformat(task["timestamp"]))
                    if metric_type == "Task Success Rate":
                        values.append(100 if task["status"] == "completed" else 0)
                    elif metric_type == "Execution Time":
                        values.append(task.get("execution_time", 0))
                
                if timestamps and values:
                    self.distribution_chart.plot_line(timestamps, values, metric_type)
                
        except Exception as e:
            logger.error(f"Failed to update distribution chart: {e}")
    
    def _update_actions_table(self, stats: Dict[str, Any]):
        """Update the recovery actions table."""
        try:
            strategy_performance = stats["strategy_performance"]
            self.actions_table.setRowCount(len(strategy_performance))
            
            for row, (action, data) in enumerate(strategy_performance.items()):
                self.actions_table.setItem(row, 0, QTableWidgetItem(action))
                self.actions_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"{data['success_rate']:.1f}%")
                )
                self.actions_table.setItem(
                    row, 2,
                    QTableWidgetItem(f"{data['avg_time']:.1f}s")
                )
                self.actions_table.setItem(
                    row, 3,
                    QTableWidgetItem(str(data["attempts"]))
                )
                
                # Calculate time since last use
                if "last_used" in data:
                    last_used = datetime.fromisoformat(data["last_used"])
                    delta = datetime.now() - last_used
                    if delta < timedelta(minutes=1):
                        time_str = "Just now"
                    elif delta < timedelta(hours=1):
                        time_str = f"{delta.seconds // 60}m ago"
                    elif delta < timedelta(days=1):
                        time_str = f"{delta.seconds // 3600}h ago"
                    else:
                        time_str = f"{delta.days}d ago"
                else:
                    time_str = "Never"
                    
                self.actions_table.setItem(row, 4, QTableWidgetItem(time_str))
                
        except Exception as e:
            logger.error(f"Failed to update actions table: {e}")
    
    def _update_tasks_table(self, stats: Dict[str, Any]):
        """Update the task metrics table."""
        try:
            active_recoveries = stats["active_recoveries"]
            self.tasks_table.setRowCount(len(active_recoveries))
            
            for row, task in enumerate(active_recoveries):
                metrics = task["metrics"]
                last_status = task["last_status"]
                
                # Task ID (truncated)
                task_id = task["task_id"][:8] + "..." if len(task["task_id"]) > 8 else task["task_id"]
                self.tasks_table.setItem(row, 0, QTableWidgetItem(task_id))
                
                # Task type
                self.tasks_table.setItem(
                    row, 1,
                    QTableWidgetItem(metrics.get("task_type", "unknown"))
                )
                
                # Status
                self.tasks_table.setItem(
                    row, 2,
                    QTableWidgetItem(last_status["status"])
                )
                
                # Recovery count
                self.tasks_table.setItem(
                    row, 3,
                    QTableWidgetItem(str(metrics.get("retry_count", 0)))
                )
                
                # Duration
                start_time = datetime.fromisoformat(metrics["start_time"])
                duration = datetime.now() - start_time
                duration_str = str(duration).split(".")[0]  # Remove microseconds
                self.tasks_table.setItem(row, 4, QTableWidgetItem(duration_str))
                
                # Result
                result = metrics.get("result", "")
                if isinstance(result, str):
                    result = result[:50] + "..." if len(result) > 50 else result
                self.tasks_table.setItem(row, 5, QTableWidgetItem(str(result)))
                
        except Exception as e:
            logger.error(f"Failed to update tasks table: {e}")
    
    def _update_insights(self, stats: Dict[str, Any]):
        """Update the insights panel."""
        try:
            recommendations = stats.get("recommendations", [])
            if recommendations:
                insights_text = "Recommendations:\n\n"
                for i, rec in enumerate(recommendations, 1):
                    insights_text += f"{i}. {rec}\n"
            else:
                insights_text = "No recommendations available at this time."
                
            self.insights_label.setText(insights_text)
            
        except Exception as e:
            logger.error(f"Failed to update insights: {e}") 