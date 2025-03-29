import threading
import logging
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto

from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.MemoryManager import MemoryManager
from core.ThreadPoolManager import ThreadPoolManager

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """System component health status."""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()

@dataclass
class HealthMetrics:
    """Health metrics for a system component."""
    status: HealthStatus
    message: str
    metrics: Dict[str, Any]
    last_check: datetime

class SystemHealthMonitor:
    """
    Centralized system health monitoring.
    Features:
    - Component health checks
    - Resource utilization monitoring
    - Performance metrics tracking
    - Automatic alerts
    - Historical metrics
    """

    def __init__(
        self,
        driver_manager: Any,
        memory_manager: MemoryManager,
        thread_pool: ThreadPoolManager,
        check_interval: int = 60,
        history_size: int = 1000
    ):
        """
        Initialize the SystemHealthMonitor.
        
        Args:
            driver_manager: WebDriver manager instance
            memory_manager: Memory manager instance
            thread_pool: Thread pool manager instance
            check_interval: Interval between health checks in seconds
            history_size: Number of historical metrics to keep
        """
        self.driver_manager = driver_manager
        self.memory_manager = memory_manager
        self.thread_pool = thread_pool
        self.check_interval = check_interval
        self.history_size = history_size
        
        self.logger = UnifiedLoggingAgent()
        
        # Component health status
        self.component_health: Dict[str, HealthMetrics] = {}
        
        # Historical metrics
        self.metrics_history: List[Dict[str, Any]] = []
        
        # Monitoring state
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Alert thresholds
        self.thresholds = {
            "memory_usage_percent": 85.0,
            "cpu_usage_percent": 80.0,
            "thread_pool_queue_size": 100,
            "response_time_ms": 5000
        }

    def start_monitoring(self) -> None:
        """Start the health monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Health monitoring is already running")
            return
            
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.log_system_event(
            event_type="monitoring_started",
            message="System health monitoring started"
        )

    def stop_monitoring(self) -> None:
        """Stop the health monitoring thread."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        self.logger.log_system_event(
            event_type="monitoring_stopped",
            message="System health monitoring stopped"
        )

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self.perform_health_checks()
                self._store_metrics()
                self._check_alerts()
                
                # Wait for next check interval
                self._stop_event.wait(timeout=self.check_interval)
                
            except Exception as e:
                self.logger.log_system_event(
                    event_type="monitoring_error",
                    message=f"Error in monitoring loop: {str(e)}",
                    level="error"
                )
                time.sleep(5)  # Brief pause on error

    def perform_health_checks(self) -> Dict[str, HealthMetrics]:
        """
        Perform health checks on all system components.
        
        Returns:
            Dictionary of component health metrics
        """
        with self._lock:
            # Check WebDriver
            self.component_health["driver"] = self._check_driver()
            
            # Check memory manager
            self.component_health["memory"] = self._check_memory()
            
            # Check thread pool
            self.component_health["thread_pool"] = self._check_thread_pool()
            
            # Check system resources
            self.component_health["system"] = self._check_system_resources()
            
            return self.component_health

    def _check_driver(self) -> HealthMetrics:
        """Check WebDriver health."""
        try:
            driver = self.driver_manager.get_driver()
            if not driver:
                return HealthMetrics(
                    status=HealthStatus.UNHEALTHY,
                    message="WebDriver not initialized",
                    metrics={},
                    last_check=datetime.now()
                )
            
            # Try to get current URL as a basic health check
            _ = driver.current_url
            
            return HealthMetrics(
                status=HealthStatus.HEALTHY,
                message="WebDriver operational",
                metrics={"session_id": driver.session_id},
                last_check=datetime.now()
            )
            
        except Exception as e:
            return HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                message=f"WebDriver error: {str(e)}",
                metrics={"error": str(e)},
                last_check=datetime.now()
            )

    def _check_memory(self) -> HealthMetrics:
        """Check memory manager health."""
        try:
            stats = self.memory_manager.get_stats()
            cache_usage = stats["cache_size"] / stats["cache_maxsize"] * 100
            
            status = HealthStatus.HEALTHY
            message = "Memory manager operational"
            
            if cache_usage > self.thresholds["memory_usage_percent"]:
                status = HealthStatus.DEGRADED
                message = f"High cache usage: {cache_usage:.1f}%"
            
            return HealthMetrics(
                status=status,
                message=message,
                metrics=stats,
                last_check=datetime.now()
            )
            
        except Exception as e:
            return HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                message=f"Memory manager error: {str(e)}",
                metrics={"error": str(e)},
                last_check=datetime.now()
            )

    def _check_thread_pool(self) -> HealthMetrics:
        """Check thread pool health."""
        try:
            metrics = self.thread_pool.get_metrics()
            total_queued = sum(
                size for size in metrics["queue_sizes"].values()
            )
            
            status = HealthStatus.HEALTHY
            message = "Thread pool operational"
            
            if total_queued > self.thresholds["thread_pool_queue_size"]:
                status = HealthStatus.DEGRADED
                message = f"High queue size: {total_queued} tasks"
            
            if metrics["tasks_failed"] > 0:
                failure_rate = (
                    metrics["tasks_failed"] /
                    (metrics["tasks_completed"] + metrics["tasks_failed"])
                    * 100
                )
                if failure_rate > 10:  # More than 10% failure rate
                    status = HealthStatus.DEGRADED
                    message = f"High failure rate: {failure_rate:.1f}%"
            
            return HealthMetrics(
                status=status,
                message=message,
                metrics=metrics,
                last_check=datetime.now()
            )
            
        except Exception as e:
            return HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                message=f"Thread pool error: {str(e)}",
                metrics={"error": str(e)},
                last_check=datetime.now()
            )

    def _check_system_resources(self) -> HealthMetrics:
        """Check system resource utilization."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
            
            status = HealthStatus.HEALTHY
            message = "System resources normal"
            
            # Check thresholds
            if cpu_percent > self.thresholds["cpu_usage_percent"]:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage: {cpu_percent}%"
            elif memory.percent > self.thresholds["memory_usage_percent"]:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent}%"
            elif disk.percent > 90:  # Fixed threshold for disk
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {disk.percent}%"
            
            return HealthMetrics(
                status=status,
                message=message,
                metrics=metrics,
                last_check=datetime.now()
            )
            
        except Exception as e:
            return HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                message=f"Resource check error: {str(e)}",
                metrics={"error": str(e)},
                last_check=datetime.now()
            )

    def _store_metrics(self) -> None:
        """Store current metrics in history."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: {
                    "status": health.status.name,
                    "message": health.message,
                    **health.metrics
                }
                for name, health in self.component_health.items()
            }
        }
        
        with self._lock:
            self.metrics_history.append(metrics)
            # Maintain history size limit
            if len(self.metrics_history) > self.history_size:
                self.metrics_history = self.metrics_history[-self.history_size:]

    def _check_alerts(self) -> None:
        """Check for alert conditions and log them."""
        unhealthy_components = [
            name for name, health in self.component_health.items()
            if health.status == HealthStatus.UNHEALTHY
        ]
        
        degraded_components = [
            name for name, health in self.component_health.items()
            if health.status == HealthStatus.DEGRADED
        ]
        
        if unhealthy_components:
            self.logger.log_system_event(
                event_type="system_alert",
                message=f"Unhealthy components detected: {', '.join(unhealthy_components)}",
                level="error",
                metadata={
                    "unhealthy_components": unhealthy_components,
                    "component_details": {
                        name: {
                            "message": self.component_health[name].message,
                            "metrics": self.component_health[name].metrics
                        }
                        for name in unhealthy_components
                    }
                }
            )
        
        if degraded_components:
            self.logger.log_system_event(
                event_type="system_warning",
                message=f"Degraded components detected: {', '.join(degraded_components)}",
                level="warning",
                metadata={
                    "degraded_components": degraded_components,
                    "component_details": {
                        name: {
                            "message": self.component_health[name].message,
                            "metrics": self.component_health[name].metrics
                        }
                        for name in degraded_components
                    }
                }
            )

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get current system health status.
        
        Returns:
            Dictionary containing overall system health metrics
        """
        with self._lock:
            component_status = {
                name: {
                    "status": health.status.name,
                    "message": health.message,
                    "last_check": health.last_check.isoformat(),
                    **health.metrics
                }
                for name, health in self.component_health.items()
            }
            
            # Calculate overall system status
            status_values = [h.status for h in self.component_health.values()]
            if any(s == HealthStatus.UNHEALTHY for s in status_values):
                overall_status = HealthStatus.UNHEALTHY
            elif any(s == HealthStatus.DEGRADED for s in status_values):
                overall_status = HealthStatus.DEGRADED
            else:
                overall_status = HealthStatus.HEALTHY
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status.name,
                "components": component_status,
                "active_monitoring": bool(self._monitor_thread and self._monitor_thread.is_alive())
            }

    def get_historical_metrics(
        self,
        component: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics for analysis.
        
        Args:
            component: Optional component name to filter metrics
            start_time: Optional start time for metrics
            end_time: Optional end time for metrics
            
        Returns:
            List of historical metrics matching the filters
        """
        with self._lock:
            filtered_metrics = self.metrics_history[:]
            
        if start_time:
            filtered_metrics = [
                m for m in filtered_metrics
                if datetime.fromisoformat(m["timestamp"]) >= start_time
            ]
            
        if end_time:
            filtered_metrics = [
                m for m in filtered_metrics
                if datetime.fromisoformat(m["timestamp"]) <= end_time
            ]
            
        if component:
            filtered_metrics = [
                {
                    "timestamp": m["timestamp"],
                    "metrics": m["components"].get(component, {})
                }
                for m in filtered_metrics
            ]
            
        return filtered_metrics
