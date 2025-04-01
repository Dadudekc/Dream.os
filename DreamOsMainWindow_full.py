#!/usr/bin/env python3
"""
DreamOsMainWindow_full.py - Self-Healing Agent Layer Implementation

This file integrates the Self-Healing Agent Layer components:
- RecoveryEngine: Handles stall detection and adaptive recovery
- MetricsService: Tracks task execution and recovery metrics
- AgentFailureHook: Bridges agents and recovery systems
- TabValidatorService: Ensures tabs have required dependencies
"""

import sys
import os
import time
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from unittest.mock import MagicMock
import importlib

# --------------------
# PyQt Imports
# --------------------
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QLabel, QSplitter, QListWidget, QListWidgetItem, QStatusBar,
    QPushButton, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal, QThread, QEvent

# Import tab factories
from interfaces.pyqt.tabs.unified_dashboard.UnifiedDashboardTab import UnifiedDashboardTabFactory
from interfaces.pyqt.tabs.draggable_prompt_board_tab import DraggablePromptBoardTabFactory

# Import service factories
from core.project_context_analyzer_factory import ProjectContextAnalyzerFactory

# --------------------
# Setup Logging
# --------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --------------------
# Fallback Mock Services (for development)
# --------------------
class MockTemplateManager:
    """Mock implementation of TemplateManager that won't crash when templates can't be loaded."""
    def __init__(self, *args, **kwargs):
        self.templates = {}
        self.is_initialized = False
        logger.info("⚠️ Using MockTemplateManager (development mode)")
    
    def get_template(self, template_name, *args, **kwargs):
        return f"Mock template: {template_name}"
    
    def render_template(self, template_name, context=None, *args, **kwargs):
        context = context or {}
        return f"Rendered {template_name} with context: {json.dumps(context, default=str)}"
    
    def get_available_templates(self, category="general"):
        return ["mock_template_1", "mock_template_2", "mock_template_3"]

class MockTestRunner:
    """Mock implementation of TestRunner for development."""
    def __init__(self, project_root=None, *args, **kwargs):
        self.project_root = project_root or os.getcwd()
        logger.info("⚠️ Using MockTestRunner (development mode)")
    
    def run_tests(self, path=None, pattern=None):
        return {
            "success": True,
            "output": "Mock test runner output: All tests passed!",
            "errors": [],
            "return_code": 0
        }
    
    def run_specific_test(self, test_name):
        return {
            "success": True,
            "output": f"Mock test runner output: Test {test_name} passed!",
            "errors": [],
            "return_code": 0
        }
    
    def get_test_coverage(self):
        return {
            "success": True,
            "coverage": "85%",
            "output": "Coverage report: 85% of code covered by tests"
        }

class MockGitManager:
    """Mock implementation of GitManager for development."""
    def __init__(self, project_root=None, *args, **kwargs):
        self.project_root = project_root or os.getcwd()
        logger.info("⚠️ Using MockGitManager (development mode)")
    
    def get_status(self):
        return {
            "is_clean": True,
            "changes": []
        }
    
    def stage_file(self, file_path):
        return True
    
    def commit(self, message, files=None):
        return True
    
    def get_current_branch(self):
        return "main"
    
    def create_branch(self, branch_name):
        return True
    
    def checkout_branch(self, branch_name):
        return True

class MockCursorDispatcher:
    """Mock implementation of CursorDispatcher for development."""
    def __init__(self, *args, **kwargs):
        logger.info("⚠️ Using MockCursorDispatcher (development mode)")
    
    def execute_command(self, command, context=None):
        return f"Executed command: {command}"
    
    def get_status(self):
        return {
            "is_loaded": True,
            "is_connected": True
        }

# --------------------
# Enhanced TabValidatorService 
# --------------------
class TabValidatorService:
    """
    Enhanced service for validating PyQt tab constructors and dependencies.
    Provides graceful degradation and detailed error reporting.
    """
    def __init__(self, services: Dict[str, Any], enable_fallbacks: bool = True):
        self.services = services
        self.validation_results = {}
        self.error_details = {}
        self.enable_fallbacks = enable_fallbacks
        self.tab_factories = {
            'cursor_execution': {
                'factory': CursorExecutionTabFactory,
                'tab_class': CursorExecutionTab,
                'required_services': CursorExecutionTabFactory.REQUIRED_SERVICES
            }
            # Additional tab factories can be registered here.
        }
    
    def validate_all_tabs(self) -> Dict[str, bool]:
        """Validate all registered tabs and provide fallbacks if enabled."""
        for tab_name, config in self.tab_factories.items():
            try:
                self._validate_tab_factory(tab_name, config)
                self.validation_results[tab_name] = True
                logger.info(f"✅ Tab '{tab_name}' validated successfully")
            except Exception as e:
                self.validation_results[tab_name] = False
                self.error_details[tab_name] = str(e)
                logger.error(f"❌ Tab '{tab_name}' validation failed: {str(e)}")
                
                # Create fallbacks if enabled
                if self.enable_fallbacks:
                    self._create_service_fallbacks(tab_name, config)
        
        return self.validation_results
    
    def _validate_tab_factory(self, tab_name: str, config: Dict[str, Any]) -> None:
        """Validate a specific tab factory and its requirements."""
        factory = config['factory']
        required_services = config['required_services']
        
        # Check for missing services
        missing_services = [service for service in required_services if service not in self.services]
        if missing_services:
            raise ValueError(f"Tab '{tab_name}' missing required services: {', '.join(missing_services)}")
    
    def _create_service_fallbacks(self, tab_name: str, config: Dict[str, Any]) -> None:
        """Create fallback implementations for missing services."""
        required_services = config['required_services']
        
        for service_name in required_services:
            if service_name not in self.services:
                logger.warning(f"⚠️ Creating fallback for missing service: {service_name}")
                
                # Create appropriate mock based on service name
                if service_name == "template_manager":
                    self.services[service_name] = MockTemplateManager()
                elif service_name == "test_runner":
                    self.services[service_name] = MockTestRunner()
                elif service_name == "git_manager":
                    self.services[service_name] = MockGitManager()
                elif service_name == "cursor_dispatcher":
                    self.services[service_name] = MockCursorDispatcher()
                else:
                    # Generic mock for any other service
                    self.services[service_name] = MagicMock()
                
                logger.info(f"✅ Created fallback for '{service_name}'")
    
    def get_validation_status(self, tab_name: str) -> Optional[bool]:
        """Get validation status for a specific tab."""
        return self.validation_results.get(tab_name)
    
    def get_error_details(self, tab_name: str) -> Optional[str]:
        """Get detailed error information for a failed tab validation."""
        return self.error_details.get(tab_name)

# --------------------
# RecoveryEngine (Enhanced with Error Categories)
# --------------------
class RecoveryEngine:
    """
    Centralized engine for handling task recovery and stall detection.
    
    Encapsulates recovery logic including:
    - Stall detection and recovery action selection
    - Execution of recovery actions via CursorSessionManager
    - Metrics tracking and strategy performance updates
    """
    def __init__(
        self,
        cursor_session: Any,
        metrics_service: Any,
        config_path: str = "config/recovery_strategies.json",
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2
    ):
        self.cursor_session = cursor_session
        self.metrics_service = metrics_service
        self.config_path = Path(config_path)
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        
        # Error categories for better recovery targeting
        self.error_categories = {
            "timeout": ["timeout", "timed out", "deadline exceeded"],
            "connection": ["connection", "network", "unreachable"],
            "auth": ["authentication", "unauthorized", "permission"],
            "resource": ["resource", "memory", "disk", "quota"],
            "rate_limit": ["rate limit", "too many requests", "throttle"],
            "context": ["context", "token", "too long"],
            "parsing": ["parse", "syntax", "format", "json"],
            "api": ["api", "endpoint", "service"],
            "ui": ["ui", "interface", "display", "render"],
            "internal": ["internal", "unknown", "unexpected"]
        }
        
        self.strategies = self._load_strategies()
        self.performance_cache = {}
        self._update_performance_metrics()
        
        logger.info("Recovery engine initialized")
    
    def _load_strategies(self) -> Dict[str, Any]:
        """Load recovery strategies from the config file."""
        default_strategies = {
            "start_new_chat": {
                "weight": 0.7,
                "conditions": ["retry_count > 2", "error_type == 'context'"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "reload_context": {
                "weight": 0.8,
                "conditions": ["error_type == 'parsing'", "retry_count < 3"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "reset_cursor": {
                "weight": 0.6,
                "conditions": ["error_type == 'ui'", "retry_count < 2"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "retry_last_command": {
                "weight": 0.5,
                "conditions": ["error_type == 'timeout'", "error_type == 'connection'"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            }
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_strategies = json.load(f)
                logger.info(f"Loaded {len(loaded_strategies)} strategies from {self.config_path}")
                return loaded_strategies
        except Exception as e:
            logger.error(f"Failed to load strategies from {self.config_path}: {e}")
        
        # Use default strategies if file doesn't exist or has error
        logger.warning(f"Using default recovery strategies")
        return default_strategies
    
    def handle_stall(self, task_context: Dict[str, Any]) -> bool:
        task_id = task_context["task_id"]
        retry_count = task_context["metrics"].get("retry_count", 0)
        
        logger.warning(f"Stall detected for task {task_id} (retry {retry_count})")
        
        # Categorize error if provided
        if "error" in task_context:
            task_context["error_type"] = self._categorize_error(task_context["error"])
        
        if retry_count >= task_context["max_retries"]:
            self._handle_max_retries_exceeded(task_id, retry_count)
            return False
            
        try:
            recovery_action = self._select_recovery_action(task_context)
            logger.info(f"Selected recovery action: {recovery_action}")
            
            success = self.execute_recovery_action(recovery_action, task_context)
            self._update_recovery_metrics(task_id, recovery_action, success)
            return success
            
        except Exception as e:
            logger.error(f"Recovery failed for task {task_id}: {e}")
            self._update_recovery_metrics(task_id, "unknown", False, error=str(e))
            return False
    
    def execute_recovery_action(self, action: str, task_context: Dict[str, Any]) -> bool:
        if not self.cursor_session:
            logger.error("No cursor session available")
            return False
            
        start_time = time.time()
        task_id = task_context["task_id"]
        
        try:
            if action == "start_new_chat":
                self.cursor_session.start_new_chat()
            else:
                self.cursor_session.execute_recovery_action(action, task_context)
            
            execution_time = time.time() - start_time
            self._update_task_metrics(
                task_id,
                "recovering",
                retry_count=task_context["metrics"]["retry_count"] + 1,
                recovery_action=action,
                execution_time=execution_time
            )
            self._update_strategy_performance(action, True, execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Recovery action '{action}' failed: {e}")
            self._update_task_metrics(
                task_id,
                "error",
                error=str(e),
                recovery_action=action,
                execution_time=execution_time
            )
            self._update_strategy_performance(action, False, execution_time)
            return False
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize an error message to help select appropriate recovery strategies."""
        error_message = error_message.lower()
        
        for category, patterns in self.error_categories.items():
            if any(pattern in error_message for pattern in patterns):
                return category
                
        return "unknown"
    
    def _update_recovery_metrics(self, task_id: str, action: str, success: bool, **kwargs) -> None:
        """Update recovery metrics for a task."""
        try:
            status = "recovered" if success else "error"
            metrics = {
                "recovery_action": action,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            
            self._update_task_metrics(task_id, status, **metrics)
        except Exception as e:
            logger.error(f"Failed to update recovery metrics: {e}")
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics for all strategies."""
        # Simple initialization of performance cache
        for strategy_name, strategy in self.strategies.items():
            if strategy_name not in self.performance_cache:
                self.performance_cache[strategy_name] = {
                    "success_rate": 0.0,
                    "avg_time": 0.0,
                    "attempts": 0
                }
        
        # If metrics service is available, we could update from real metrics
        if self.metrics_service and hasattr(self.metrics_service, 'get_global_metrics'):
            try:
                metrics = self.metrics_service.get_global_metrics()
                action_stats = metrics.get("recovery_action_stats", {})
                
                for action, stats in action_stats.items():
                    if action in self.strategies and stats.get("attempts", 0) > 0:
                        success_rate = (stats["successes"] / stats["attempts"] * 100) 
                        
                        self.performance_cache[action] = {
                            "success_rate": success_rate,
                            "avg_time": stats.get("avg_execution_time", 0),
                            "attempts": stats["attempts"],
                            "last_updated": datetime.now().isoformat()
                        }
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
    
    # Rest of the RecoveryEngine implementation...
    # [Same as in the original code]

# --------------------
# MetricsService (Thread-Safe Implementation)
# --------------------
class MetricsService:
    """
    Thread-safe service for tracking and analyzing task execution metrics.
    Persists data to disk for historical analysis.
    """
    def __init__(self, metrics_dir: str):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "task_metrics.json"
        self.metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # Thread safety
        self._last_save_time = time.time()
        self._save_interval = 5.0  # Save at most every 5 seconds
        
        self._load_metrics()
    
    def _load_metrics(self):
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    self.metrics_cache = json.load(f)
                logger.info(f"Loaded metrics from {self.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            self.metrics_cache = {}
    
    def _save_metrics(self, force=False):
        current_time = time.time()
        # Rate limit saving to disk
        if not force and (current_time - self._last_save_time < self._save_interval):
            return
            
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_cache, f, indent=2)
            self._last_save_time = current_time
            logger.debug("Saved metrics to disk")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def update_task_metrics(self, task_id: str, status: str, **kwargs):
        with self._lock:  # Thread safety
            if task_id not in self.metrics_cache:
                self.metrics_cache[task_id] = {
                    "created_at": datetime.now().isoformat(),
                    "status_history": [],
                    "prompt_count": 0,
                    "execution_cycles": 0,
                    "retry_count": 0,
                    "total_execution_time": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "stall_count": 0,
                    "recovery_attempts": 0,
                    "successful_recoveries": 0,
                    "recovery_actions": {}
                }
            
            metrics = self.metrics_cache[task_id]
            current_time = datetime.now()
            
            metrics["status_history"].append({
                "status": status,
                "timestamp": current_time.isoformat(),
                **kwargs
            })
            
            if status == "queued":
                metrics["execution_cycles"] += 1
            elif status == "completed":
                metrics["success_count"] += 1
                if "result" in kwargs:
                    metrics["last_result"] = kwargs["result"]
                if "execution_time" in kwargs:
                    metrics["total_execution_time"] += kwargs["execution_time"]
            elif status in ["error", "failed"]:
                metrics["error_count"] += 1
                if "error" in kwargs:
                    metrics["last_error"] = kwargs["error"]
            elif status == "recovering":
                metrics["recovery_attempts"] += 1
                if "recovery_action" in kwargs:
                    action = kwargs["recovery_action"]
                    if action not in metrics["recovery_actions"]:
                        metrics["recovery_actions"][action] = {"attempts": 0, "successes": 0}
                    metrics["recovery_actions"][action]["attempts"] += 1
            
            if "stall_detected" in kwargs and kwargs["stall_detected"]:
                metrics["stall_count"] += 1
            
            if status == "completed" and metrics["recovery_attempts"] > 0:
                metrics["successful_recoveries"] += 1
                if "recovery_action" in kwargs:
                    action = kwargs["recovery_action"]
                    if action in metrics["recovery_actions"]:
                        metrics["recovery_actions"][action]["successes"] += 1
            
            if "retry_count" in kwargs:
                metrics["retry_count"] = kwargs["retry_count"]
            
            total_attempts = metrics["success_count"] + metrics["error_count"]
            metrics["success_rate"] = (metrics["success_count"] / total_attempts * 100) if total_attempts > 0 else 0
            
            if metrics["recovery_attempts"] > 0:
                metrics["recovery_success_rate"] = (metrics["successful_recoveries"] / metrics["recovery_attempts"] * 100)
            else:
                metrics["recovery_success_rate"] = 0
            
            self._save_metrics()
    
    def get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.metrics_cache.get(task_id, {})
    
    def get_global_metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_tasks = len(self.metrics_cache)
            if total_tasks == 0:
                return {
                    "total_tasks": 0,
                    "success_rate": 0,
                    "average_execution_time": 0,
                    "total_execution_cycles": 0,
                    "total_stalls": 0,
                    "recovery_success_rate": 0,
                    "recovery_action_stats": {}
                }
            
            total_success = sum(m["success_count"] for m in self.metrics_cache.values())
            total_cycles = sum(m["execution_cycles"] for m in self.metrics_cache.values())
            total_time = sum(m["total_execution_time"] for m in self.metrics_cache.values())
            total_stalls = sum(m["stall_count"] for m in self.metrics_cache.values())
            total_recoveries = sum(m["recovery_attempts"] for m in self.metrics_cache.values())
            successful_recoveries = sum(m["successful_recoveries"] for m in self.metrics_cache.values())
            
            recovery_action_stats = {}
            for metrics in self.metrics_cache.values():
                for action, stats in metrics["recovery_actions"].items():
                    if action not in recovery_action_stats:
                        recovery_action_stats[action] = {"attempts": 0, "successes": 0}
                    recovery_action_stats[action]["attempts"] += stats["attempts"]
                    recovery_action_stats[action]["successes"] += stats["successes"]
            
            return {
                "total_tasks": total_tasks,
                "success_rate": (total_success / total_tasks) * 100,
                "average_execution_time": total_time / total_tasks if total_tasks > 0 else 0,
                "total_execution_cycles": total_cycles,
                "total_stalls": total_stalls,
                "recovery_success_rate": (successful_recoveries / total_recoveries * 100) if total_recoveries > 0 else 0,
                "recovery_action_stats": recovery_action_stats,
                "tasks_by_status": self._get_tasks_by_status(),
                "hourly_execution_stats": self._get_hourly_stats()
            }
    
    def _get_tasks_by_status(self) -> Dict[str, int]:
        status_counts = {}
        for metrics in self.metrics_cache.values():
            if metrics["status_history"]:
                current_status = metrics["status_history"][-1]["status"]
                status_counts[current_status] = status_counts.get(current_status, 0) + 1
        return status_counts
    
    def _get_hourly_stats(self) -> Dict[str, Any]:
        now = datetime.now()
        hourly_stats = {"executions": [0] * 24, "successes": [0] * 24, "failures": [0] * 24}
        for metrics in self.metrics_cache.values():
            for status_entry in metrics["status_history"]:
                try:
                    timestamp = datetime.fromisoformat(status_entry["timestamp"])
                    if now - timestamp <= timedelta(hours=24):
                        hour_index = 23 - (now - timestamp).seconds // 3600
                        if hour_index >= 0:
                            hourly_stats["executions"][hour_index] += 1
                            if status_entry["status"] == "completed":
                                hourly_stats["successes"][hour_index] += 1
                            elif status_entry["status"] in ["error", "failed"]:
                                hourly_stats["failures"][hour_index] += 1
                except Exception:
                    continue
        return hourly_stats

# --------------------
# CursorExecutionTab Implementation
# --------------------
class CursorExecutionTab(QWidget):
    """
    Real implementation of CursorExecutionTab with UI and logic.
    Includes error handling and recovery integration.
    """
    def __init__(self, services: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.services = services
        self.template_manager = services.get("template_manager")
        self.cursor_dispatcher = services.get("cursor_dispatcher")
        self.test_runner = services.get("test_runner") 
        self.git_manager = services.get("git_manager")
        self.recovery_engine = services.get("recovery_engine")
        self.metrics_service = services.get("metrics_service")
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Template selection and execution controls
        controls_group = QGroupBox("Execution Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Template combo (simplified as QLabel for this example)
        self.template_combo = QLabel("Template: mock_template.md")
        controls_layout.addWidget(self.template_combo)
        
        # Execute button
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_prompt)
        controls_layout.addWidget(self.execute_button)
        
        layout.addWidget(controls_group)
        
        # Context editor
        context_group = QGroupBox("Context")
        context_layout = QVBoxLayout(context_group)
        self.context_edit = QTextEdit()
        self.context_edit.setPlaceholderText("Enter context as JSON...")
        context_layout.addWidget(self.context_edit)
        layout.addWidget(context_group)
        
        # Code/output view
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)
        
        # Status bar at the bottom
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)
    
    def execute_prompt(self):
        self.log_message("Executing prompt...")
        
        # Generate unique task ID
        task_id = f"cursor_exec_{uuid.uuid4().hex[:8]}"
        self.current_task_id = task_id
        
        # Get context from editor
        context_text = self.context_edit.toPlainText().strip()
        try:
            if context_text:
                context = json.loads(context_text)
            else:
                context = {}
        except json.JSONDecodeError as e:
            self.log_message(f"Error: Invalid JSON context - {str(e)}")
            return
        
        # Record task start in metrics
        if self.metrics_service:
            self.metrics_service.update_task_metrics(
                task_id,
                "queued",
                task_type="cursor_execution",
                context=context
            )
        
        # Create task_context for recovery
        task_context = {
            "task_id": task_id,
            "max_retries": 3,
            "retry_delay": 5,
            "timeout": 300,
            "metrics": {
                "retry_count": 0,
                "start_time": datetime.now().isoformat(),
                "status": "queued"
            },
            "context": context
        }
        
        # Execute in background thread to avoid UI freezing
        self.execute_button.setEnabled(False)
        self.status_label.setText("Executing...")
        
        # Define execution logic
        def execute_task():
            start_time = time.time()
            try:
                # If we have cursor_dispatcher, use it to execute
                if self.cursor_dispatcher:
                    result = self.cursor_dispatcher.execute_command(
                        "execute_prompt", 
                        {"context": context}
                    )
                else:
                    # Mock execution for testing
                    time.sleep(2)  # Simulate work
                    result = f"Mock execution result with context: {json.dumps(context)}"
                
                # Record success in metrics
                if self.metrics_service:
                    self.metrics_service.update_task_metrics(
                        task_id,
                        "completed",
                        execution_time=time.time() - start_time,
                        result=result
                    )
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"Error during execution: {error_msg}")
                
                # Record error in metrics
                if self.metrics_service:
                    self.metrics_service.update_task_metrics(
                        task_id,
                        "error",
                        error=error_msg,
                        execution_time=time.time() - start_time
                    )
                
                # Attempt recovery if available
                if self.recovery_engine:
                    task_context["error"] = error_msg
                    task_context["error_type"] = "execution_error"
                    self.recovery_engine.handle_stall(task_context)
                
                return f"Error: {error_msg}"
        
        # Create and start worker thread
        worker_thread = threading.Thread(target=self._execute_with_ui_update, args=(execute_task,))
        worker_thread.daemon = True
        worker_thread.start()
    
    def _execute_with_ui_update(self, task_callable):
        """Execute a task and update the UI when done."""
        try:
            result = task_callable()
            
            # Update UI in the main thread
            QApplication.instance().postEvent(
                self, 
                ExecutionCompletedEvent(result=result)
            )
            
        except Exception as e:
            # Update UI with error
            QApplication.instance().postEvent(
                self, 
                ExecutionCompletedEvent(result=f"Error: {str(e)}")
            )
    
    def log_message(self, message):
        """Add a message to the output log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.append(f"[{timestamp}] {message}")
    
    def customEvent(self, event):
        """Handle custom events posted from worker threads."""
        if isinstance(event, ExecutionCompletedEvent):
            self.output_text.append(event.result)
            self.execute_button.setEnabled(True)
            self.status_label.setText("Ready")

# Custom event for thread-to-UI communication
class ExecutionCompletedEvent(QEvent):
    """Custom event for notifying UI of task completion."""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, result):
        super().__init__(self.EVENT_TYPE)
        self.result = result

# --------------------
# CursorExecutionTabFactory 
# --------------------
class CursorExecutionTabFactory:
    """Factory for creating CursorExecutionTab instances with validated dependencies."""
    REQUIRED_SERVICES = [
        'cursor_dispatcher',
        'template_manager',
        'test_runner',
        'git_manager'
    ]
    
    @classmethod
    def create(cls, services: Dict[str, Any], parent: Optional[QWidget] = None) -> CursorExecutionTab:
        cls._validate_services(services)
        return CursorExecutionTab(services=services, parent=parent)
    
    @classmethod
    def _validate_services(cls, services: Dict[str, Any]) -> None:
        missing_services = [service for service in cls.REQUIRED_SERVICES if service not in services]
        if missing_services:
            missing_str = ', '.join(missing_services)
            logger.error(f"Missing required services for CursorExecutionTab: {missing_str}")
            raise ValueError(f"Missing required services for CursorExecutionTab: {missing_str}")

# --------------------
# ServiceDiagnosticTab
# --------------------
class ServiceDiagnosticTab(QWidget):
    """
    Diagnostic tab for monitoring service status and attempting service recovery.
    Displays all required services, their status, and provides retry options.
    """
    def __init__(self, services: Dict[str, Any], tab_validator: TabValidatorService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.services = services
        self.tab_validator = tab_validator
        self._init_ui()
        self._refresh_status()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Service Diagnostic Panel")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Monitor service status and attempt recovery of failed services.")
        layout.addWidget(desc_label)
        
        # Services List
        services_group = QGroupBox("Services Status")
        services_layout = QVBoxLayout(services_group)
        
        self.services_list = QListWidget()
        services_layout.addWidget(self.services_list)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self._refresh_status)
        controls_layout.addWidget(self.refresh_button)
        
        self.retry_button = QPushButton("Retry Failed Services")
        self.retry_button.clicked.connect(self._retry_failed_services)
        controls_layout.addWidget(self.retry_button)
        
        services_layout.addLayout(controls_layout)
        layout.addWidget(services_group)
        
        # Tab Validation Status
        tabs_group = QGroupBox("Tab Validation Status")
        tabs_layout = QVBoxLayout(tabs_group)
        
        self.tabs_list = QListWidget()
        tabs_layout.addWidget(self.tabs_list)
        
        self.validate_button = QPushButton("Validate All Tabs")
        self.validate_button.clicked.connect(self._validate_all_tabs)
        tabs_layout.addWidget(self.validate_button)
        
        layout.addWidget(tabs_group)
        
        # Log Output
        log_group = QGroupBox("Diagnostic Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def _refresh_status(self):
        """Refresh the status of all services."""
        self.services_list.clear()
        self.log_message("Refreshing service status...")
        
        required_services = [
            "cursor_dispatcher",
            "template_manager",
            "test_runner",
            "git_manager",
            "cursor_session_manager",
            "metrics_service",
            "recovery_engine"
        ]
        
        for service_name in required_services:
            service = self.services.get(service_name)
            
            if service is None:
                status = "❌ Missing"
                color = "red"
            elif isinstance(service, MagicMock):
                status = "⚠️ Mock"
                color = "orange"
            else:
                status = "✅ Available"
                color = "green"
            
            item = QListWidgetItem(f"{service_name}: {status}")
            item.setData(Qt.UserRole, service_name)
            item.setForeground(Qt.GlobalColor.red if status == "❌ Missing" else 
                              Qt.GlobalColor.darkYellow if status == "⚠️ Mock" else
                              Qt.GlobalColor.darkGreen)
            self.services_list.addItem(item)
        
        self.log_message("Service status refresh complete.")
    
    def _retry_failed_services(self):
        """Attempt to initialize failed services."""
        self.log_message("Attempting to recover failed services...")
        
        # Get list of failed services
        failed_services = []
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            service_name = item.data(Qt.UserRole)
            if "Missing" in item.text() or "Mock" in item.text():
                failed_services.append(service_name)
        
        if not failed_services:
            self.log_message("No failed services to recover.")
            return
        
        # Try to initialize each failed service with appropriate fallbacks
        for service_name in failed_services:
            self.log_message(f"Attempting to recover {service_name}...")
            
            try:
                # Service-specific initialization logic
                if service_name == "template_manager":
                    from core.TemplateManager import TemplateManager
                    self.services[service_name] = TemplateManager()
                
                elif service_name == "cursor_dispatcher":
                    from core.chatgpt_automation.controllers.cursor_dispatcher import CursorDispatcher
                    self.services[service_name] = CursorDispatcher()
                
                elif service_name == "test_runner":
                    from interfaces.pyqt.services.TestRunner import TestRunner
                    self.services[service_name] = TestRunner(project_root=str(Path.cwd()))
                
                elif service_name == "git_manager":
                    from interfaces.pyqt.services.GitManager import GitManager
                    self.services[service_name] = GitManager(project_root=str(Path.cwd()))
                
                elif service_name == "cursor_session_manager":
                    from core.CursorSessionManager import CursorSessionManager
                    self.services[service_name] = CursorSessionManager()
                
                elif service_name == "metrics_service":
                    # Use our implementation
                    metrics_dir = Path("metrics")
                    metrics_dir.mkdir(parents=True, exist_ok=True)
                    self.services[service_name] = MetricsService(str(metrics_dir))
                
                elif service_name == "recovery_engine":
                    # Use our implementation
                    self.services[service_name] = RecoveryEngine(
                        cursor_session=self.services.get("cursor_session_manager"),
                        metrics_service=self.services.get("metrics_service")
                    )
                
                self.log_message(f"✅ Successfully recovered {service_name}")
            
            except Exception as e:
                self.log_message(f"❌ Failed to recover {service_name}: {str(e)}")
                
                # Create mock as fallback
                if service_name == "template_manager":
                    self.services[service_name] = MockTemplateManager()
                elif service_name == "test_runner":
                    self.services[service_name] = MockTestRunner()
                elif service_name == "git_manager":
                    self.services[service_name] = MockGitManager()
                elif service_name == "cursor_dispatcher":
                    self.services[service_name] = MockCursorDispatcher()
                else:
                    self.services[service_name] = MagicMock()
                
                self.log_message(f"⚠️ Created mock for {service_name}")
        
        # Refresh status after recovery attempts
        self._refresh_status()
    
    def _validate_all_tabs(self):
        """Validate all tabs using the TabValidatorService."""
        self.tabs_list.clear()
        self.log_message("Validating all tabs...")
        
        validation_results = self.tab_validator.validate_all_tabs()
        
        for tab_name, is_valid in validation_results.items():
            status = "✅ Valid" if is_valid else "❌ Invalid"
            color = Qt.GlobalColor.darkGreen if is_valid else Qt.GlobalColor.red
            
            item = QListWidgetItem(f"{tab_name}: {status}")
            item.setForeground(color)
            
            # Add error details if validation failed
            if not is_valid:
                error_details = self.tab_validator.get_error_details(tab_name)
                if error_details:
                    self.log_message(f"Tab '{tab_name}' validation failed: {error_details}")
            
            self.tabs_list.addItem(item)
        
        self.log_message("Tab validation complete.")
    
    def log_message(self, message):
        """Add a message to the diagnostic log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

# --------------------
# DreamOsMainWindow Integration
# --------------------
class DreamOsMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS - AI Integration Platform")
        self.resize(1200, 800)
        
        # Initialize services with robust error handling
        try:
            self.services = self._initialize_services()
            logger.info("✅ Services initialized")
        except Exception as e:
            logger.error(f"⚠️ Error during service initialization: {e}")
            self.services = {}  # Empty dict as fallback
        
        # Validate tab constructors with fallbacks enabled
        try:
            self.tab_validator = TabValidatorService(self.services, enable_fallbacks=True)
            validation_results = self.tab_validator.validate_all_tabs()
            
            for tab_name, is_valid in validation_results.items():
                status = "✅" if is_valid else "⚠️"
                logger.info(f"{status} Tab '{tab_name}' validation: {'passed' if is_valid else 'warnings - fallbacks created'}")
        except Exception as e:
            logger.error(f"⚠️ Error during tab validation: {e}")
            # Create minimal validator as fallback
            self.tab_validator = TabValidatorService({}, enable_fallbacks=True)
        
        # Initialize UI with error handling
        try:
            self._init_ui()
            self.setStatusBar(QStatusBar())
            self.statusBar().showMessage("Dream.OS Ready")
        except Exception as e:
            logger.error(f"⚠️ Error during UI initialization: {e}")
            # Create minimal UI as fallback
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            error_label = QLabel(f"Error initializing UI: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(error_label)
            
            retry_button = QPushButton("Retry")
            retry_button.clicked.connect(self._retry_initialization)
            layout.addWidget(retry_button)
        
        # Run diagnostics to help troubleshoot missing services
        self._diagnose_services()
    
    def _initialize_services(self) -> Dict[str, Any]:
        """Initialize services used by the application."""
        services = {}
        
        # Initialize ConfigManager
        try:
            from core.config.config_manager import ConfigManager
            services["config_manager"] = ConfigManager()
            logger.info(f"ConfigManager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ConfigManager: {e}")
            services["config_manager"] = None
        
        # Initialize TemplateManager
        try:
            from core.TemplateManager import TemplateManager
            template_manager = TemplateManager()
            services["template_manager"] = template_manager
            logger.info(f"TemplateManager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize TemplateManager: {e}")
            services["template_manager"] = MockTemplateManager()
            logger.info(f"Using MockTemplateManager")
        
        # Initialize TestRunner
        try:
            from core.TestRunner import TestRunner
            test_runner = TestRunner()
            services["test_runner"] = test_runner
            logger.info(f"TestRunner initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize TestRunner: {e}")
            services["test_runner"] = MockTestRunner()
            logger.info(f"Using MockTestRunner")
        
        # Initialize GitManager
        try:
            from core.GitManager import GitManager
            git_manager = GitManager()
            services["git_manager"] = git_manager
            logger.info(f"GitManager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize GitManager: {e}")
            services["git_manager"] = MockGitManager()
            logger.info(f"Using MockGitManager")
        
        # Initialize CursorDispatcher
        try:
            from core.CursorDispatcher import CursorDispatcher
            cursor_dispatcher = CursorDispatcher()
            services["cursor_dispatcher"] = cursor_dispatcher
            logger.info(f"CursorDispatcher initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize CursorDispatcher: {e}")
            services["cursor_dispatcher"] = MockCursorDispatcher()
            logger.info(f"Using MockCursorDispatcher")
        
        # Initialize CursorSessionManager
        try:
            from core.CursorSessionManager import CursorSessionManager
            cursor_session_manager = CursorSessionManager()
            services["cursor_session_manager"] = cursor_session_manager
            logger.info(f"CursorSessionManager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize CursorSessionManager: {e}")
            from unittest.mock import MagicMock
            services["cursor_session_manager"] = MagicMock()
            services["cursor_session_manager"].__class__.__name__ = "MockCursorSessionManager"
            logger.info(f"Using MockCursorSessionManager")
        
        # Initialize MetricsService
        try:
            metrics_dir = "metrics"
            metrics_service = MetricsService(metrics_dir)
            services["metrics_service"] = metrics_service
            logger.info(f"MetricsService initialized with directory: {metrics_dir}")
        except Exception as e:
            logger.warning(f"Failed to initialize MetricsService: {e}")
            services["metrics_service"] = None
        
        # Initialize RecoveryEngine
        try:
            from core.recovery.recovery_engine import RecoveryEngine
            recovery_engine = RecoveryEngine(
                cursor_session=services.get("cursor_session_manager"),
                metrics_service=services.get("metrics_service")
            )
            services["recovery_engine"] = recovery_engine
            logger.info(f"RecoveryEngine initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize RecoveryEngine: {e}")
            from unittest.mock import MagicMock
            services["recovery_engine"] = MagicMock()
            services["recovery_engine"].__class__.__name__ = "MockRecoveryEngine"
            logger.info(f"Using MockRecoveryEngine: {e}")
        
        # Initialize prompt execution service
        try:
            from core.PromptExecutionService import PromptExecutionService
            prompt_service = PromptExecutionService()
            services["prompt_service"] = prompt_service
            logger.info("✅ PromptExecutionService initialized")
        except Exception as e:
            logger.error(f"⚠️ Error initializing PromptExecutionService: {e}")
            services["prompt_service"] = MagicMock()
            
        # Initialize project context analyzer
        try:
            context_analyzer = ProjectContextAnalyzerFactory.create(services)
            if context_analyzer:
                services["context_analyzer"] = context_analyzer
                logger.info("✅ ProjectContextAnalyzer initialized")
            else:
                logger.error("⚠️ Failed to create ProjectContextAnalyzer")
                services["context_analyzer"] = MagicMock()
        except Exception as e:
            logger.error(f"⚠️ Error initializing ProjectContextAnalyzer: {e}")
            services["context_analyzer"] = MagicMock()
        
        return services
    
    def _init_ui(self):
        """Initialize the main UI components."""
        self.setMinimumSize(1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add service diagnostic tab
        self.diagnostic_tab = ServiceDiagnosticTab(self.services, self.tab_validator)
        self.tabs.addTab(self.diagnostic_tab, "Service Diagnostics")
        
        # Add tabs
        self._add_tab_safely("cursor_execution", "interfaces.pyqt.tabs.cursor_execution_tab", "CursorExecutionTab")
        self._add_tab_safely("contextual_chat", None, None, factory=UnifiedDashboardTabFactory.create(self.services))
        
        # Add draggable prompt board tab
        self._add_tab_safely("prompt_board", None, None, factory=DraggablePromptBoardTabFactory.create(self.services))
        
        # Add tabs layout to main layout
        main_layout.addWidget(self.tabs)
        
        # Create a timer for checking service status
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # 1 second
    
    def _add_tab_safely(self, tab_name, module_path, class_name, get_widget=False, factory=None):
        """
        Safely add a tab to the UI, with error handling.
        
        Args:
            tab_name: Name of the tab
            module_path: Import path for the module
            class_name: Name of the class to instantiate
            get_widget: Whether to return the widget
            factory: Optional factory class to use instead of dynamic import
        
        Returns:
            The created widget if get_widget is True, None otherwise
        """
        try:
            # First check if tab already exists
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == tab_name.replace('_', ' ').title():
                    logger.warning(f"Tab {tab_name} already exists, skipping")
                    return self.tabs.widget(i) if get_widget else None
            
            widget = None
            if factory:
                # Use factory method to create tab
                widget = factory.create(self.services, self)
                logger.info(f"Created {tab_name} tab using factory.")
            else:
                # Import the module dynamically
                module = importlib.import_module(module_path)
                
                # Get the class from the module
                tab_class = getattr(module, class_name)
                
                # Create an instance of the class
                widget = tab_class(self.services, self)
                logger.info(f"Created {tab_name} tab using dynamic import.")
            
            # Add the widget to the tab widget
            tab_title = tab_name.replace('_', ' ').title()
            self.tabs.addTab(widget, tab_title)
            
            # Mark as loaded
            if tab_name in self.tab_validator.validation_results:
                self.tab_validator.validation_results[tab_name] = True
            
            return widget if get_widget else None
        except Exception as e:
            error_message = f"Error adding tab {tab_name}: {str(e)}"
            logger.error(error_message)
            self.tab_validator.error_messages[tab_name] = error_message
            self.tab_validator.validation_results[tab_name] = False
            
            # Show error in status bar
            self.statusBar().showMessage(f"Failed to load {tab_name} tab")
            
            # Add a placeholder widget with error
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"Failed to load {tab_name} tab:\n{str(e)}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            
            retry_button = QPushButton(f"Retry Loading {tab_name}")
            retry_button.clicked.connect(lambda: self._retry_load_tab(tab_name, module_path, class_name, factory))
            error_layout.addWidget(retry_button)
            
            tab_title = tab_name.replace('_', ' ').title() + " (Error)"
            self.tabs.addTab(error_widget, tab_title)
            
            return None
    
    def _retry_load_tab(self, tab_name, module_path, class_name, factory=None):
        """Retry loading a specific tab."""
        try:
            # Find the index of the tab
            for i in range(self.tabs.count()):
                if tab_name.lower() in self.tabs.tabText(i).lower():
                    # Remove the existing tab
                    self.tabs.removeTab(i)
                    break
            
            # Try loading again
            self._add_tab_safely(tab_name, module_path, class_name, factory=factory)
            self.statusBar().showMessage(f"Successfully reloaded {tab_name} tab")
        except Exception as e:
            error_message = f"Error retrying to load tab {tab_name}: {str(e)}"
            logger.error(error_message)
            self.statusBar().showMessage(error_message)
    
    def _retry_initialization(self):
        """Retry initialization of failed components."""
        # Re-validate all tabs
        self.tab_validator.validate_all_tabs()
        
        # Update the diagnostic tab
        self.diagnostic_tab._refresh_status()
        
        # Try adding cursor tab again if it failed
        if not self.tab_validator.get_validation_status("cursor_execution"):
            self._retry_load_cursor_tab()
        
        # Try adding unified dashboard tab if it failed
        if "contextual_chat" in self.tab_validator.validation_results:
            if not self.tab_validator.get_validation_status("contextual_chat"):
                self._retry_load_tab("contextual_chat", None, None, factory=UnifiedDashboardTabFactory.create(self.services))
        
        # Show status message
        self.statusBar().showMessage("Retry initialization completed")
    
    def _retry_load_cursor_tab(self):
        """Retry loading just the cursor execution tab."""
        try:
            # Make sure required services are available
            for service_name in CursorExecutionTabFactory.REQUIRED_SERVICES:
                if service_name not in self.services or self.services[service_name] is None:
                    # Create mock if missing
                    if service_name == "template_manager":
                        self.services[service_name] = MockTemplateManager()
                    elif service_name == "test_runner":
                        self.services[service_name] = MockTestRunner()
                    elif service_name == "git_manager":
                        self.services[service_name] = MockGitManager()
                    elif service_name == "cursor_dispatcher":
                        self.services[service_name] = MockCursorDispatcher()
            
            # Create tab via factory
            self.cursor_execution_tab = CursorExecutionTabFactory.create(services=self.services, parent=self)
            
            # Find and replace the error tab
            for i in range(self.tabs.count()):
                if "Cursor Execution" in self.tabs.tabText(i):
                    self.tabs.removeTab(i)
                    self.tabs.insertTab(i, self.cursor_execution_tab, "Cursor Execution")
                    self.tabs.setCurrentIndex(i)
                    break
            
            self.statusBar().showMessage("Cursor Execution Tab loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload Cursor Execution Tab: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reload Cursor Execution Tab: {str(e)}")

    def _diagnose_services(self):
        """Print detailed diagnostic information about services to help with debugging."""
        print("\n=== SERVICE DIAGNOSTIC REPORT ===")
        
        critical_services = [
            "cursor_session_manager",
            "metrics_service", 
            "recovery_engine",
            "cursor_dispatcher",
            "template_manager",
            "test_runner",
            "git_manager"
        ]
        
        for service_name in critical_services:
            if service_name not in self.services:
                print(f"❌ {service_name}: MISSING (key not in services dict)")
            elif self.services[service_name] is None:
                print(f"❌ {service_name}: NULL (key exists but value is None)")
            elif isinstance(self.services[service_name], MagicMock):
                print(f"⚠️ {service_name}: MOCK (using fallback mock implementation)")
            else:
                print(f"✅ {service_name}: AVAILABLE ({type(self.services[service_name]).__name__})")
        
        # Add a call to this diagnostic at the end of initialization
        print("\n=== SERVICE INITIALIZATION PATHS ===")
        try:
            from importlib.util import find_spec
            
            modules_to_check = [
                "core.CursorSessionManager", 
                "core.recovery.recovery_engine",
                "core.chatgpt_automation.controllers.cursor_dispatcher"
            ]
            
            for module_path in modules_to_check:
                spec = find_spec(module_path)
                if spec:
                    print(f"✅ Module {module_path} found at: {spec.origin}")
                else:
                    print(f"❌ Module {module_path} NOT FOUND")
        except Exception as e:
            print(f"Error checking module paths: {e}")
            
        print("================================\n")

    # Dummy placeholder for task handling (the real implementation can be integrated later)
    def _handle_queued_task(self, task: Dict[str, Any]):
        task_id = task.get("id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            if self.services.get("metrics_service"):
                self.services["metrics_service"].update_task_metrics(
                    task_id,
                    "queued",
                    task_type=task.get("action", "unknown"),
                    title=task.get("title", "Untitled Task")
                )
            
            # Gather context and build prompt
            context = "Dummy conversation context"
            prompt = f"Task: {task.get('prompt', 'No prompt provided')}\nContext: {context}"
            
            task_context = {
                "task_id": task_id,
                "max_retries": 3,
                "retry_delay": 5,
                "timeout": 300,
                "metrics": {
                    "retry_count": 0,
                    "start_time": datetime.now().isoformat(),
                    "status": "queued"
                },
                "error_type": "unknown"
            }
            
            cursor_session = self.services.get("cursor_session_manager")
            if not cursor_session:
                raise RuntimeError("CursorSessionManager not available")
            
            # Define recovery callback
            def on_stall():
                if "recovery_engine" in self.services and self.services["recovery_engine"]:
                    return self.services["recovery_engine"].handle_stall(task_context)
                return False
            
            # Queue prompt execution
            result = cursor_session.queue_prompt(
                prompt,
                isolation_level="high",
                on_stall=on_stall,
                timeout=task_context["timeout"]
            )
            
            execution_time = time.time() - start_time
            
            if self.services.get("metrics_service"):
                self.services["metrics_service"].update_task_metrics(
                    task_id,
                    "completed",
                    execution_time=execution_time,
                    result=result
                )
            
            return result
            
        except Exception as e:
            if self.services.get("metrics_service"):
                self.services["metrics_service"].update_task_metrics(
                    task_id,
                    "error",
                    error=str(e),
                    execution_time=time.time() - start_time
                )
            
            # Try recovery
            if "recovery_engine" in self.services and self.services["recovery_engine"]:
                task_context["error"] = str(e)
                task_context["error_type"] = "execution_error"
                self.services["recovery_engine"].handle_stall(task_context)
            
            raise RuntimeError(f"Task failed: {e}")

    def _on_tab_changed(self, index):
        """Handle tab switching events."""
        try:
            # Update status bar with current tab name
            current_tab = self.tabs.tabText(index)
            self.statusBar().showMessage(f"Current tab: {current_tab}")
            
            # Refresh the tab data if it supports refreshing
            current_widget = self.tabs.widget(index)
            if hasattr(current_widget, 'refresh_data') and callable(current_widget.refresh_data):
                current_widget.refresh_data()
                logger.info(f"Refreshed data for tab: {current_tab}")
        except Exception as e:
            logger.error(f"Error handling tab change: {e}")

    def _update_status(self):
        """Periodically update the status of services."""
        self.diagnostic_tab._refresh_status()

# Application entry point
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = DreamOsMainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        # Show error dialog for user
        if QApplication.instance():
            QMessageBox.critical(None, "Fatal Error", f"Application failed to start: {str(e)}")
        sys.exit(1)
