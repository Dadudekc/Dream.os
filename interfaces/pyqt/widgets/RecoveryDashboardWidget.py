"""
Recovery Dashboard Widget Module

This module provides a real-time visualization widget for task recovery metrics and stall patterns.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QProgressBar,
    QFrame, QPushButton, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor

logger = logging.getLogger(__name__)

class SparklineWidget(QWidget):
    """Widget for displaying mini trend graphs."""
    
    def __init__(self, data: List[float], color: str = "#2196F3"):
        super().__init__()
        self.data = data
        self.color = QColor(color)
        self.setMinimumWidth(60)
        self.setMinimumHeight(20)
    
    def paintEvent(self, event):
        if not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        width = self.width()
        height = self.height()
        padding = 2
        
        # Calculate points
        points = []
        max_val = max(self.data) if self.data else 1
        min_val = min(self.data) if self.data else 0
        value_range = max(max_val - min_val, 1)
        
        x_step = (width - 2 * padding) / (len(self.data) - 1) if len(self.data) > 1 else 0
        
        for i, value in enumerate(self.data):
            x = padding + (i * x_step)
            y = height - padding - ((value - min_val) / value_range * (height - 2 * padding))
            points.append((x, y))
        
        # Draw line
        pen = QPen(self.color, 1.5)
        painter.setPen(pen)
        
        for i in range(len(points) - 1):
            painter.drawLine(
                int(points[i][0]), int(points[i][1]),
                int(points[i + 1][0]), int(points[i + 1][1])
            )

class RecoveryDashboardWidget(QWidget):
    """Widget for displaying real-time recovery metrics and stall patterns."""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, metrics_service):
        super().__init__()
        self.metrics_service = metrics_service
        self._init_ui()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def _init_ui(self):
        """Initialize the dashboard UI."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Recovery Dashboard")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Stats Grid
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QHBoxLayout()
        
        # Create stat boxes
        self.stat_boxes = {
            "active_recoveries": self._create_stat_box("Active Recoveries", "0"),
            "total_stalls": self._create_stat_box("Total Stalls", "0"),
            "recovery_success_rate": self._create_stat_box("Recovery Success Rate", "0%"),
            "avg_recovery_time": self._create_stat_box("Avg Recovery Time", "0s")
        }
        
        for box in self.stat_boxes.values():
            stats_layout.addWidget(box)
        
        stats_frame.setLayout(stats_layout)
        layout.addWidget(stats_frame)
        
        # Recovery Actions Table
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(5)
        self.actions_table.setHorizontalHeaderLabels([
            "Recovery Action", "Success Rate", "Trend", "Avg Time", "Last Used"
        ])
        header = self.actions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.actions_table)
        
        # Stalled Tasks Table
        self.stalled_table = QTableWidget()
        self.stalled_table.setColumnCount(6)
        self.stalled_table.setHorizontalHeaderLabels([
            "Task ID", "Status", "Retries", "Last Action", "Duration", "Progress"
        ])
        header = self.stalled_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.stalled_table)
        
        self.setLayout(layout)
    
    def _create_stat_box(self, title: str, value: str) -> QFrame:
        """Create a styled stat box."""
        box = QFrame()
        box.setFrameStyle(QFrame.StyledPanel)
        box.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 4px; }")
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #666;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3;")
        value_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        box.setLayout(layout)
        box.value_label = value_label  # Store reference for updates
        return box
    
    def refresh_data(self):
        """Refresh all dashboard data."""
        try:
            metrics = self.metrics_service.get_global_metrics()
            active_tasks = self._get_active_recovery_tasks()
            
            # Update stat boxes
            self.stat_boxes["active_recoveries"].value_label.setText(
                str(len(active_tasks))
            )
            self.stat_boxes["total_stalls"].value_label.setText(
                str(metrics["total_stalls"])
            )
            self.stat_boxes["recovery_success_rate"].value_label.setText(
                f"{metrics['recovery_success_rate']:.1f}%"
            )
            
            # Update recovery actions table
            self._update_recovery_actions_table(metrics["recovery_action_stats"])
            
            # Update stalled tasks table
            self._update_stalled_tasks_table(active_tasks)
            
            self.refresh_requested.emit()
            
        except Exception as e:
            logger.error(f"Failed to refresh recovery dashboard: {e}")
    
    def _get_active_recovery_tasks(self) -> List[Dict[str, Any]]:
        """Get list of tasks currently in recovery state."""
        active_tasks = []
        
        for task_id, metrics in self.metrics_service.metrics_cache.items():
            if metrics["status_history"]:
                last_status = metrics["status_history"][-1]
                if last_status["status"] in ["recovering", "stalled"]:
                    active_tasks.append({
                        "task_id": task_id,
                        "metrics": metrics,
                        "last_status": last_status
                    })
        
        return active_tasks
    
    def _update_recovery_actions_table(self, action_stats: Dict[str, Dict[str, int]]):
        """Update the recovery actions table with current stats."""
        self.actions_table.setRowCount(len(action_stats))
        
        for row, (action, stats) in enumerate(action_stats.items()):
            # Action name
            self.actions_table.setItem(row, 0, QTableWidgetItem(action))
            
            # Success rate
            success_rate = (stats["successes"] / stats["attempts"] * 100) if stats["attempts"] > 0 else 0
            self.actions_table.setItem(row, 1, QTableWidgetItem(f"{success_rate:.1f}%"))
            
            # Trend sparkline (last 10 attempts)
            trend_data = self._get_action_trend_data(action)
            sparkline = SparklineWidget(trend_data)
            self.actions_table.setCellWidget(row, 2, sparkline)
            
            # Average time
            avg_time = self._calculate_action_avg_time(action)
            self.actions_table.setItem(row, 3, QTableWidgetItem(f"{avg_time:.1f}s"))
            
            # Last used
            last_used = self._get_action_last_used(action)
            self.actions_table.setItem(row, 4, QTableWidgetItem(last_used))
    
    def _update_stalled_tasks_table(self, active_tasks: List[Dict[str, Any]]):
        """Update the stalled tasks table."""
        self.stalled_table.setRowCount(len(active_tasks))
        
        for row, task in enumerate(active_tasks):
            metrics = task["metrics"]
            last_status = task["last_status"]
            
            # Task ID (truncated)
            task_id = task["task_id"][:8] + "..." if len(task["task_id"]) > 8 else task["task_id"]
            self.stalled_table.setItem(row, 0, QTableWidgetItem(task_id))
            
            # Status
            self.stalled_table.setItem(row, 1, QTableWidgetItem(last_status["status"]))
            
            # Retry count
            self.stalled_table.setItem(row, 2, QTableWidgetItem(str(metrics["retry_count"])))
            
            # Last action
            last_action = last_status.get("recovery_action", "N/A")
            self.stalled_table.setItem(row, 3, QTableWidgetItem(last_action))
            
            # Duration
            start_time = datetime.fromisoformat(metrics["created_at"])
            duration = datetime.now() - start_time
            duration_str = str(duration).split(".")[0]  # Remove microseconds
            self.stalled_table.setItem(row, 4, QTableWidgetItem(duration_str))
            
            # Progress bar
            progress = QProgressBar()
            progress.setRange(0, task["metrics"]["max_retries"])
            progress.setValue(task["metrics"]["retry_count"])
            self.stalled_table.setCellWidget(row, 5, progress)
    
    def _get_action_trend_data(self, action: str) -> List[float]:
        """Get trend data for a recovery action (last 10 attempts)."""
        trend_data = []
        
        for task in self.metrics_service.metrics_cache.values():
            for status in task["status_history"]:
                if status.get("recovery_action") == action:
                    success = status["status"] == "completed"
                    trend_data.append(1.0 if success else 0.0)
        
        return trend_data[-10:]  # Last 10 attempts
    
    def _calculate_action_avg_time(self, action: str) -> float:
        """Calculate average execution time for a recovery action."""
        times = []
        
        for task in self.metrics_service.metrics_cache.values():
            action_starts = {}
            
            for status in task["status_history"]:
                if status.get("recovery_action") == action:
                    timestamp = datetime.fromisoformat(status["timestamp"])
                    
                    if status["status"] == "recovering":
                        action_starts[action] = timestamp
                    elif status["status"] in ["completed", "failed"]:
                        if action in action_starts:
                            duration = (timestamp - action_starts[action]).total_seconds()
                            times.append(duration)
                            del action_starts[action]
        
        return sum(times) / len(times) if times else 0.0
    
    def _get_action_last_used(self, action: str) -> str:
        """Get when the recovery action was last used."""
        latest_time = None
        
        for task in self.metrics_service.metrics_cache.values():
            for status in task["status_history"]:
                if status.get("recovery_action") == action:
                    timestamp = datetime.fromisoformat(status["timestamp"])
                    if latest_time is None or timestamp > latest_time:
                        latest_time = timestamp
        
        if latest_time is None:
            return "Never"
            
        delta = datetime.now() - latest_time
        if delta < timedelta(minutes=1):
            return "Just now"
        elif delta < timedelta(hours=1):
            return f"{delta.seconds // 60}m ago"
        elif delta < timedelta(days=1):
            return f"{delta.seconds // 3600}h ago"
        else:
            return f"{delta.days}d ago" 