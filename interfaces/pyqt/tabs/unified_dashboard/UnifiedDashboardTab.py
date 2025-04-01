#!/usr/bin/env python3
"""
UnifiedDashboardTab.py

This module provides a unified dashboard tab for Dream.OS that aggregates key metrics,
task summaries, and recovery status into one interface.
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QTextEdit, QFrame, QComboBox,
    QApplication, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, QTime

logger = logging.getLogger(__name__)

class UnifiedDashboardTab(QWidget):
    def __init__(self, services: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize the Unified Dashboard Tab.
        
        Args:
            services: Dictionary of application services.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.services = services
        self.logger = logging.getLogger("UnifiedDashboardTab")
        
        self._init_ui()
        self._setup_timer()
        self.refresh_data()  # Initial data load
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header: Title and refresh controls
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Dream.OS Unified Dashboard")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        
        self.refresh_button = QPushButton("Refresh Now")
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)
        
        # Time range selector
        self.time_range = QComboBox()
        self.time_range.addItems(["Last Hour", "Last 24 Hours", "Last Week"])
        self.time_range.currentTextChanged.connect(self.refresh_data)
        header_layout.addWidget(QLabel("Time Range:"))
        header_layout.addWidget(self.time_range)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Splitter to separate task summary and metrics/recovery view
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Task Summary (simple table)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Task Summary"))
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels(["Task ID", "Title", "Status"])
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        left_layout.addWidget(self.task_table)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Metrics and Recovery Overview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Recovery Metrics Table
        right_layout.addWidget(QLabel("Recovery Metrics"))
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(4)
        self.metrics_table.setHorizontalHeaderLabels(["Action", "Success Rate", "Avg Time", "Attempts"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        right_layout.addWidget(self.metrics_table)
        
        # Recovery Recommendations / Insights
        right_layout.addWidget(QLabel("Recovery Insights & Recommendations"))
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setMinimumHeight(100)
        right_layout.addWidget(self.insights_text)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        
        # Log Panel at the bottom
        layout.addWidget(QLabel("System Logs"))
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setMinimumHeight(150)
        layout.addWidget(self.log_panel)
        
        self.setLayout(layout)
    
    def _setup_timer(self):
        """Set up a timer to refresh data periodically."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds
    
    def refresh_data(self):
        """Refresh all data on the dashboard."""
        try:
            self._refresh_task_summary()
            self._refresh_metrics()
            self._refresh_insights()
            self._refresh_logs()
            
            # Log refresh activity
            now = QTime.currentTime().toString("hh:mm:ss")
            self.log_panel.append(f"[{now}] Dashboard data refreshed successfully.")
        except Exception as e:
            self.logger.error(f"Error refreshing dashboard data: {e}")
            now = QTime.currentTime().toString("hh:mm:ss")
            self.log_panel.append(f"[{now}] Error refreshing data: {str(e)}")
    
    def _refresh_task_summary(self):
        """Refresh the task summary table."""
        try:
            # First check for episode generator in component_managers
            episode_generator = None
            if "component_managers" in self.services:
                episode_generator = self.services["component_managers"].get("episode_generator")
            
            # If found, use it to get episodes
            tasks = []
            if episode_generator:
                tasks = episode_generator.get_episodes() or []
                self.logger.info(f"Retrieved {len(tasks)} tasks from episode_generator")
            else:
                # Fallback to cursor_session_manager history if available
                cursor_manager = self.services.get("cursor_session_manager")
                if cursor_manager:
                    session_history = cursor_manager.get_session_history(20)  # Last 20 sessions
                    tasks = [
                        {
                            "id": session.get("id", "unknown"),
                            "title": session.get("prompt", "")[:40] + "..." if len(session.get("prompt", "")) > 40 else session.get("prompt", ""),
                            "status": session.get("status", "unknown")
                        }
                        for session in session_history
                    ]
            
            # Update table with tasks
            self.task_table.setRowCount(len(tasks))
            for row, task in enumerate(tasks):
                task_id = task.get("id", "N/A")
                title = task.get("title", "No Title")
                status = task.get("status", "Unknown")
                
                self.task_table.setItem(row, 0, QTableWidgetItem(str(task_id)))
                self.task_table.setItem(row, 1, QTableWidgetItem(str(title)))
                
                status_item = QTableWidgetItem(str(status))
                # Color code status items
                if status.lower() in ['completed', 'success']:
                    status_item.setBackground(Qt.green)
                elif status.lower() in ['failed', 'error']:
                    status_item.setBackground(Qt.red)
                elif status.lower() in ['running', 'recovering', 'active']:
                    status_item.setBackground(Qt.yellow)
                
                self.task_table.setItem(row, 2, status_item)
            
            self.task_table.sortItems(0, Qt.DescendingOrder)  # Sort by ID (newest first)
        except Exception as e:
            self.logger.error(f"Error refreshing task summary: {e}")
            raise
    
    def _refresh_metrics(self):
        """Refresh recovery and global metrics from MetricsService."""
        try:
            metrics_service = self.services.get("metrics_service")
            if not metrics_service:
                self.log_panel.append("MetricsService not available.")
                return
            
            global_metrics = metrics_service.get_global_metrics()
            recovery_stats = global_metrics.get("recovery_action_stats", {})
            
            actions = list(recovery_stats.keys())
            self.metrics_table.setRowCount(len(actions))
            for row, action in enumerate(actions):
                stats = recovery_stats[action]
                
                # Action name
                self.metrics_table.setItem(row, 0, QTableWidgetItem(action))
                
                # Success rate
                attempts = stats.get("attempts", 0)
                successes = stats.get("successes", 0)
                success_rate = (successes / attempts * 100) if attempts > 0 else 0
                rate_item = QTableWidgetItem(f"{success_rate:.1f}%")
                
                # Color code success rates
                if success_rate >= 80:
                    rate_item.setBackground(Qt.green)
                elif success_rate >= 50:
                    rate_item.setBackground(Qt.yellow)
                else:
                    rate_item.setBackground(Qt.red)
                    
                self.metrics_table.setItem(row, 1, rate_item)
                
                # Average time
                # Check if the recovery engine has performance stats
                recovery_engine = self.services.get("recovery_engine")
                avg_time = 0.0
                if recovery_engine:
                    try:
                        performance_stats = recovery_engine.get_performance_stats()
                        strategy_stats = performance_stats.get("strategies", {}).get(action, {})
                        avg_time = strategy_stats.get("avg_execution_time", 0.0)
                    except AttributeError:
                        # Fallback if get_performance_stats is not available
                        avg_time = 5.0  # Default value
                
                self.metrics_table.setItem(row, 2, QTableWidgetItem(f"{avg_time:.1f}s"))
                
                # Attempts
                self.metrics_table.setItem(row, 3, QTableWidgetItem(str(attempts)))
            
            self.metrics_table.sortItems(1, Qt.DescendingOrder)  # Sort by success rate
        except Exception as e:
            self.logger.error(f"Error refreshing metrics: {e}")
            raise
    
    def _refresh_insights(self):
        """Update insights and recommendations from RecoveryEngine."""
        try:
            recovery_engine = self.services.get("recovery_engine")
            if not recovery_engine:
                self.insights_text.setPlainText("RecoveryEngine not available.")
                return
            
            # Try getting recommendations through recovery_stats
            recommendations = []
            try:
                stats = recovery_engine.get_recovery_stats()
                recommendations = stats.get("recommendations", [])
            except AttributeError:
                # Fallback if get_recovery_stats is not available
                pass
            
            # If no recommendations through that method, try another approach
            if not recommendations and hasattr(recovery_engine, "get_performance_stats"):
                performance_stats = recovery_engine.get_performance_stats()
                
                # Generate some basic insights from performance data
                strategies = performance_stats.get("strategies", {})
                for name, stats in strategies.items():
                    if stats.get("success_rate", 0) < 50 and stats.get("attempts", 0) > 5:
                        recommendations.append(f"Strategy '{name}' has low success rate ({stats.get('success_rate')}%)")
            
            # Format insights
            if recommendations:
                insights = "Recommendations:\n\n" + "\n".join(f"• {rec}" for rec in recommendations)
            else:
                insights = "No recovery recommendations available at this time."
                
            # Add some general stats if available
            metrics_service = self.services.get("metrics_service")
            if metrics_service:
                try:
                    global_metrics = metrics_service.get_global_metrics()
                    total_tasks = global_metrics.get("total_tasks", 0)
                    success_rate = global_metrics.get("success_rate", 0)
                    insights += f"\n\nOverall System Stats:\n• Total Tasks: {total_tasks}\n• Success Rate: {success_rate:.1f}%"
                except (AttributeError, KeyError):
                    pass
                
            self.insights_text.setPlainText(insights)
        except Exception as e:
            self.logger.error(f"Error refreshing insights: {e}")
            raise
    
    def _refresh_logs(self):
        """Append latest logs from a log source if available."""
        try:
            # Get recent log entries if a log source is available
            # For now, we'll just show the refresh operation
            now = QTime.currentTime().toString("hh:mm:ss")
            
            # Try to get some real metrics if available
            metrics_service = self.services.get("metrics_service")
            if metrics_service:
                try:
                    global_metrics = metrics_service.get_global_metrics()
                    recovery_count = sum(
                        stats.get("attempts", 0) 
                        for stats in global_metrics.get("recovery_action_stats", {}).values()
                    )
                    self.log_panel.append(f"[{now}] System stats: {recovery_count} recovery attempts tracked.")
                except (AttributeError, KeyError):
                    pass
            
            recovery_engine = self.services.get("recovery_engine")
            if recovery_engine:
                try:
                    active_recoveries = recovery_engine.get_recovery_stats().get("active_recoveries", [])
                    if active_recoveries:
                        self.log_panel.append(f"[{now}] {len(active_recoveries)} active recovery operations.")
                except AttributeError:
                    pass
        except Exception as e:
            self.logger.error(f"Error refreshing logs: {e}")
            # Don't raise the exception here to avoid breaking the refresh cycle

# Factory for creating UnifiedDashboardTab instances with validated dependencies
class UnifiedDashboardTabFactory:
    """Factory for creating UnifiedDashboardTab instances with validated dependencies."""
    
    REQUIRED_SERVICES = ["metrics_service"]
    OPTIONAL_SERVICES = ["recovery_engine", "cursor_session_manager", "component_managers"]
    
    @classmethod
    def create(cls, services: Dict[str, Any], parent: Optional[QWidget] = None) -> UnifiedDashboardTab:
        """Create a new UnifiedDashboardTab instance with validated services."""
        cls._validate_services(services)
        return UnifiedDashboardTab(services, parent)
    
    @classmethod
    def _validate_services(cls, services: Dict[str, Any]) -> None:
        """Validate that all required services are available."""
        missing_services = [svc for svc in cls.REQUIRED_SERVICES if svc not in services]
        if missing_services:
            raise ValueError(f"Missing required services for UnifiedDashboardTab: {', '.join(missing_services)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create dummy services for testing
    from unittest.mock import MagicMock
    dummy_episode_generator = MagicMock()
    dummy_episode_generator.get_episodes.return_value = [
        {"id": "task1", "title": "Test Task 1", "status": "queued"},
        {"id": "task2", "title": "Test Task 2", "status": "completed"}
    ]
    services = {
        "component_managers": {
            "episode_generator": dummy_episode_generator,
            "template_manager": MagicMock()
        },
        "metrics_service": MagicMock(),
        "recovery_engine": MagicMock()
    }
    # For metrics, simulate some recovery action stats
    services["metrics_service"].get_global_metrics.return_value = {
        "recovery_action_stats": {
            "start_new_chat": {"attempts": 10, "successes": 8},
            "reload_context": {"attempts": 5, "successes": 3}
        }
    }
    # For recovery_engine, simulate recommendations
    services["recovery_engine"].get_recovery_stats.return_value = {
        "global_metrics": {"recovery_success_rate": 80.0},
        "recovery_action_stats": {
            "start_new_chat": {"attempts": 10, "successes": 8},
            "reload_context": {"attempts": 5, "successes": 3}
        },
        "active_recoveries": [],
        "recommendations": [
            "Consider optimizing reload_context strategy for faster recovery.",
            "Review start_new_chat logs for consistent performance."
        ]
    }
    
    dashboard = UnifiedDashboardTab(services)
    dashboard.show()
    sys.exit(app.exec_()) 