import os
import json
import glob
from datetime import datetime
from typing import Optional, Dict, Any
from core.config.config_manager import ConfigManager
from interfaces.pyqt.ILoggingAgent import ILoggingAgent
from core.PathManager import PathManager

class FileLogger(ILoggingAgent):
    """Logger implementation for file output with rotation."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.debug_mode = config_manager.get('logging.debug_mode', False)
        self.max_file_size = config_manager.get('logging.file.max_size_mb', 10) * 1024 * 1024
        self.max_files = config_manager.get('logging.file.max_files', 5)
        self.log_dir = os.path.join(PathManager.get_path('logs'), 'system')
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _get_log_file(self) -> str:
        """Get the current log file path."""
        date_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"system_{date_str}.log")
        
    def _rotate_logs(self) -> None:
        """Rotate log files if needed."""
        log_files = sorted(glob.glob(os.path.join(self.log_dir, "system_*.log")))
        
        # Remove oldest files if we exceed max_files
        while len(log_files) >= self.max_files:
            try:
                os.remove(log_files[0])
                log_files.pop(0)
            except Exception as e:
                print(f"Error rotating log files: {str(e)}")
                break
                
    def _write_log(self, log_data: Dict[str, Any]) -> None:
        """Write a log entry to file with rotation."""
        log_file = self._get_log_file()
        
        # Check if rotation is needed
        if os.path.exists(log_file) and os.path.getsize(log_file) >= self.max_file_size:
            self._rotate_logs()
            
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
            
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """Log a message to file with domain and level."""
        timestamp = datetime.now().isoformat()
        log_data = {
            "timestamp": timestamp,
            "level": level,
            "domain": domain,
            "message": message
        }
        self._write_log(log_data)
        
    def log_error(self, message: str, domain: str = "General") -> None:
        """Log an error message."""
        self.log(message, domain=domain, level="ERROR")
        
    def log_debug(self, message: str, domain: str = "General") -> None:
        """Log a debug message if debug mode is enabled."""
        if self.debug_mode:
            self.log(message, domain=domain, level="DEBUG")
            
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """Log a structured event."""
        event_message = f"{event_name} - {payload}"
        self.log(event_message, domain=domain, level="EVENT")
        
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """Log a system event."""
        event_message = f"{event} - {message}"
        self.log(event_message, domain=domain, level="SYSTEM") 
