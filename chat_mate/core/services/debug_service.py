import os
import logging
import json
from datetime import datetime

class DebugService:
    def __init__(self, config):
        """
        Initialize the DebugService with a configuration dictionary.
        Expects config to include at least:
            log_dir: directory path for storing debug info
        """
        self.config = config
        self.logger = logging.getLogger("DebugService")
        self.debug_info_path = os.path.join(self.config.get("log_dir", "."), "debug_info.json")
        os.makedirs(os.path.dirname(self.debug_info_path), exist_ok=True)
        self.logger.info("DebugService initialized. Debug info path: %s", self.debug_info_path)

    def start_debug_session(self, target):
        """
        Start a debug session for the specified target.
        
        Args:
            target (str): Identifier for the target component or system.
            
        Returns:
            str: Confirmation message with a generated session ID.
        """
        session_id = f"debug_{self._get_current_timestamp()}"
        debug_info = {
            "target": target,
            "session_id": session_id,
            "status": "started",
            "details": "Debug session initiated successfully."
        }
        self._save_debug_info(debug_info)
        self.logger.info("Debug session started for %s with session id %s", target, session_id)
        return f"Debug session for {target} started with session id {session_id}."

    def get_debug_info(self, target):
        """
        Retrieve debug information for the specified target.
        
        Args:
            target (str): Identifier for the target component.
            
        Returns:
            str: Debug information or an error message.
        """
        if os.path.exists(self.debug_info_path):
            try:
                with open(self.debug_info_path, 'r', encoding='utf-8') as f:
                    debug_data = json.load(f)
                return f"Debug info for {target}: {json.dumps(debug_data, indent=2)}"
            except Exception as e:
                self.logger.error("Error reading debug info: %s", e)
                return f"Error retrieving debug info for {target}."
        else:
            return f"No debug info available for {target}."

    def _save_debug_info(self, debug_info):
        """
        Save debug information to a JSON file.
        """
        try:
            with open(self.debug_info_path, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=4)
        except Exception as e:
            self.logger.error("Failed to save debug info: %s", e)

    def _get_current_timestamp(self):
        return datetime.utcnow().isoformat()

# Example usage when run as a script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = {"log_dir": "./logs"}
    debug_service = DebugService(config)
    start_msg = debug_service.start_debug_session("ComponentXYZ")
    print(start_msg)
    debug_info = debug_service.get_debug_info("ComponentXYZ")
    print(debug_info)
