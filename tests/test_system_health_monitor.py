import os
import sys
import unittest
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.SystemHealthMonitor import SystemHealthMonitor

class TestSystemHealthMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize SystemHealthMonitor
        self.monitor = SystemHealthMonitor(
            output_dir=self.test_output_dir,
            check_interval=1,  # 1 second for testing
            log_level="DEBUG"
        )
        
        # Test data
        self.test_metrics = {
            "cpu_usage": 45.5,
            "memory_usage": 60.2,
            "disk_usage": 75.8,
            "network_io": {
                "bytes_sent": 1024000,
                "bytes_recv": 2048000
            },
            "process_count": 150,
            "thread_count": 450
        }
    
    def test_initialization(self):
        """Test if SystemHealthMonitor initializes correctly."""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.check_interval, 1)
        self.assertEqual(self.monitor.log_level, "DEBUG")
        self.assertTrue(os.path.exists(self.monitor.output_dir))
        self.assertIsNotNone(self.monitor.logger)
    
    def test_collect_system_metrics(self):
        """Test system metrics collection."""
        # Mock psutil functions
        with patch('psutil.cpu_percent') as mock_cpu:
            with patch('psutil.virtual_memory') as mock_mem:
                with patch('psutil.disk_usage') as mock_disk:
                    with patch('psutil.net_io_counters') as mock_net:
                        with patch('psutil.pids') as mock_pids:
                            # Setup mock returns
                            mock_cpu.return_value = 45.5
                            mock_mem.return_value = MagicMock(percent=60.2)
                            mock_disk.return_value = MagicMock(percent=75.8)
                            mock_net.return_value = MagicMock(
                                bytes_sent=1024000,
                                bytes_recv=2048000
                            )
                            mock_pids.return_value = list(range(150))
                            
                            # Collect metrics
                            metrics = self.monitor._collect_system_metrics()
                            
                            # Verify
                            self.assertEqual(metrics["cpu_usage"], 45.5)
                            self.assertEqual(metrics["memory_usage"], 60.2)
                            self.assertEqual(metrics["disk_usage"], 75.8)
                            self.assertEqual(metrics["network_io"]["bytes_sent"], 1024000)
                            self.assertEqual(metrics["network_io"]["bytes_recv"], 2048000)
                            self.assertEqual(metrics["process_count"], 150)
    
    def test_check_system_health(self):
        """Test system health checking."""
        # Test healthy metrics
        self.monitor._collect_system_metrics = Mock(return_value=self.test_metrics)
        
        health_status = self.monitor._check_system_health()
        
        # Verify
        self.assertTrue(health_status["is_healthy"])
        self.assertEqual(len(health_status["warnings"]), 0)
        self.assertEqual(len(health_status["errors"]), 0)
        
        # Test unhealthy metrics
        unhealthy_metrics = self.test_metrics.copy()
        unhealthy_metrics["cpu_usage"] = 95.0
        unhealthy_metrics["memory_usage"] = 90.0
        unhealthy_metrics["disk_usage"] = 95.0
        
        self.monitor._collect_system_metrics = Mock(return_value=unhealthy_metrics)
        
        health_status = self.monitor._check_system_health()
        
        # Verify
        self.assertFalse(health_status["is_healthy"])
        self.assertEqual(len(health_status["warnings"]), 3)
        self.assertEqual(len(health_status["errors"]), 0)
    
    def test_generate_health_report(self):
        """Test health report generation."""
        # Setup test data
        self.monitor._collect_system_metrics = Mock(return_value=self.test_metrics)
        self.monitor._check_system_health = Mock(return_value={
            "is_healthy": True,
            "warnings": [],
            "errors": []
        })
        
        # Generate report
        report_path = self.monitor._generate_health_report()
        
        # Verify report file was created
        self.assertTrue(os.path.exists(report_path))
        
        # Verify report content
        with open(report_path, 'r') as f:
            report = json.load(f)
            self.assertIn("timestamp", report)
            self.assertIn("metrics", report)
            self.assertIn("health_status", report)
            self.assertIn("system_info", report)
    
    def test_monitor_system(self):
        """Test system monitoring functionality."""
        # Setup mocks
        self.monitor._collect_system_metrics = Mock(return_value=self.test_metrics)
        self.monitor._check_system_health = Mock(return_value={
            "is_healthy": True,
            "warnings": [],
            "errors": []
        })
        self.monitor._generate_health_report = Mock(return_value="test_report.json")
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Wait for one check interval
        import time
        time.sleep(1.1)  # Slightly longer than check_interval
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify
        self.assertTrue(self.monitor._collect_system_metrics.called)
        self.assertTrue(self.monitor._check_system_health.called)
        self.assertTrue(self.monitor._generate_health_report.called)
    
    def test_alert_handling(self):
        """Test alert handling functionality."""
        # Setup test alerts
        test_alerts = [
            {"level": "warning", "message": "High CPU usage"},
            {"level": "error", "message": "Critical memory usage"}
        ]
        
        # Test alert handling
        for alert in test_alerts:
            self.monitor._handle_alert(alert)
        
        # Verify alerts were logged
        self.assertEqual(len(self.monitor.alerts), 2)
        self.assertEqual(self.monitor.alerts[0]["level"], "warning")
        self.assertEqual(self.monitor.alerts[1]["level"], "error")
    
    def test_cleanup_old_reports(self):
        """Test cleanup of old health reports."""
        # Create test report files with different timestamps
        old_report = os.path.join(self.test_output_dir, "health_report_20240301.json")
        new_report = os.path.join(self.test_output_dir, "health_report_20240321.json")
        
        with open(old_report, 'w') as f:
            json.dump({"timestamp": "2024-03-01T00:00:00"}, f)
        
        with open(new_report, 'w') as f:
            json.dump({"timestamp": datetime.now().isoformat()}, f)
        
        # Run cleanup
        self.monitor._cleanup_old_reports(days=7)
        
        # Verify
        self.assertFalse(os.path.exists(old_report))
        self.assertTrue(os.path.exists(new_report))
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop monitoring if running
        if hasattr(self, 'monitor') and self.monitor.is_monitoring:
            self.monitor.stop_monitoring()
        
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 