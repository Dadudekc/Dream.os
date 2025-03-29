import logging
from typing import Dict, Any, Optional
import json
import asyncio
import websockets
from pathlib import Path

from core.executors.base_executor import BaseExecutor
from config.ConfigManager import ConfigManager
from core.PathManager import PathManager

class CursorExecutor(BaseExecutor):
    """Executor for running prompts through Cursor's websocket interface."""
    
    def __init__(self,
                 config_manager: ConfigManager,
                 path_manager: PathManager,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the Cursor executor.
        
        Args:
            config_manager: Configuration manager instance
            path_manager: Path manager instance
            logger: Optional logger instance
        """
        self.config = config_manager
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        self.websocket = None
        
    async def execute(self,
                     prompt: str,
                     test_file: Optional[str] = None,
                     generate_tests: bool = False,
                     **kwargs) -> Dict[str, Any]:
        """
        Execute a prompt through Cursor.
        
        Args:
            prompt: The prompt to execute
            test_file: Optional path to test file
            generate_tests: Whether to generate tests
            **kwargs: Additional parameters:
                - workspace_path: str (path to workspace)
                - file_path: str (path to file being edited)
                - cursor_position: dict (line and character position)
                
        Returns:
            Dict containing execution results
        """
        try:
            # Connect to Cursor websocket
            if not await self._ensure_connection():
                return {
                    "success": False,
                    "error": "Failed to connect to Cursor",
                    "response": "",
                    "artifacts": {}
                }
                
            # Prepare request payload
            request = {
                "type": "prompt",
                "prompt": prompt,
                "workspace_path": kwargs.get("workspace_path", str(self.path_manager.get_workspace_path())),
                "file_path": kwargs.get("file_path"),
                "cursor_position": kwargs.get("cursor_position", {"line": 0, "character": 0}),
                "generate_tests": generate_tests,
                "test_file": test_file
            }
            
            # Send request and get response
            await self.websocket.send(json.dumps(request))
            response = await self._get_response()
            
            if not response:
                return {
                    "success": False,
                    "error": "No response received from Cursor",
                    "response": "",
                    "artifacts": {}
                }
                
            # Process response
            return self._process_response(response)
            
        except Exception as e:
            self.logger.error(f"Error executing Cursor prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "artifacts": {}
            }
            
    async def _ensure_connection(self) -> bool:
        """Ensure websocket connection to Cursor is established."""
        try:
            if self.websocket and not self.websocket.closed:
                return True
                
            # Get Cursor websocket URL from config
            ws_url = self.config.get("cursor_websocket_url", "ws://localhost:8765")
            
            # Connect to websocket
            self.websocket = await websockets.connect(ws_url)
            self.logger.info("Connected to Cursor websocket")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to Cursor: {str(e)}")
            return False
            
    async def _get_response(self, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Wait for and get Cursor's response.
        
        Args:
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            Response data or None if no response
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1
                    )
                    return json.loads(response)
                except asyncio.TimeoutError:
                    continue
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting response: {str(e)}")
            return None
            
    def _process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Cursor's response into standard format."""
        try:
            if response.get("error"):
                return {
                    "success": False,
                    "error": response["error"],
                    "response": "",
                    "artifacts": {}
                }
                
            artifacts = {}
            
            # Process file changes
            if "file_changes" in response:
                artifacts["file_changes"] = response["file_changes"]
                
            # Process generated tests
            if "generated_tests" in response:
                artifacts["generated_tests"] = response["generated_tests"]
                
            return {
                "success": True,
                "response": response.get("response", ""),
                "error": None,
                "artifacts": artifacts
            }
            
        except Exception as e:
            self.logger.error(f"Error processing response: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing response: {str(e)}",
                "response": "",
                "artifacts": {}
            }
            
    def shutdown(self):
        """Close websocket connection."""
        if self.websocket and not self.websocket.closed:
            asyncio.create_task(self.websocket.close()) 