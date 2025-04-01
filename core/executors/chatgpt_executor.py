import logging
from typing import Dict, Any, Optional
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.executors.base_executor import BaseExecutor
from core.DriverManager import DriverManager
from core.PathManager import PathManager
from core.config.config_manager import ConfigManager

class ChatGPTExecutor(BaseExecutor):
    """Executor for running prompts through ChatGPT web interface."""
    
    def __init__(self,
                 driver_manager: DriverManager,
                 config_manager: ConfigManager,
                 path_manager: PathManager,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the ChatGPT executor.
        
        Args:
            driver_manager: Driver manager instance
            config_manager: Configuration manager instance
            path_manager: Path manager instance
            logger: Optional logger instance
        """
        self.driver_manager = driver_manager
        self.config = config_manager
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute(self,
                     prompt: str,
                     test_file: Optional[str] = None,
                     generate_tests: bool = False,
                     **kwargs) -> Dict[str, Any]:
        """
        Execute a prompt through ChatGPT.
        
        Args:
            prompt: The prompt to execute
            test_file: Optional path to test file
            generate_tests: Whether to generate tests
            **kwargs: Additional parameters:
                - model: str (e.g., "gpt-4", "gpt-3.5-turbo")
                - temperature: float
                - max_tokens: int
                
        Returns:
            Dict containing execution results
        """
        try:
            # Get driver for ChatGPT
            driver = self.driver_manager.get_driver("chatgpt")
            if not driver:
                return {
                    "success": False,
                    "error": "Failed to initialize ChatGPT driver",
                    "response": "",
                    "artifacts": {}
                }
                
            # Navigate to ChatGPT if not already there
            if not driver.current_url.startswith("https://chat.openai.com"):
                driver.get("https://chat.openai.com")
                await asyncio.sleep(2)  # Wait for page load
                
            # Set model if specified
            model = kwargs.get("model", "gpt-4")
            if model != "gpt-4":
                await self._set_model(driver, model)
                
            # Send prompt
            success = await self._send_prompt(driver, prompt)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to send prompt",
                    "response": "",
                    "artifacts": {}
                }
                
            # Wait for and get response
            response = await self._get_response(driver)
            if not response:
                return {
                    "success": False,
                    "error": "No response received",
                    "response": "",
                    "artifacts": {}
                }
                
            return {
                "success": True,
                "response": response,
                "error": None,
                "artifacts": {}
            }
            
        except Exception as e:
            self.logger.error(f"Error executing ChatGPT prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "artifacts": {}
            }
            
    async def _send_prompt(self, driver, prompt: str) -> bool:
        """Send prompt to ChatGPT."""
        try:
            # Wait for input box
            wait = WebDriverWait(driver, 10)
            input_box = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "textarea[data-id='root']")
            ))
            
            # Send prompt
            input_box.clear()
            input_box.send_keys(prompt)
            input_box.send_keys("\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending prompt: {str(e)}")
            return False
            
    async def _get_response(self, driver, timeout: int = 120) -> Optional[str]:
        """
        Wait for and get ChatGPT's response.
        
        Args:
            driver: WebDriver instance
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            Response text or None if no response
        """
        try:
            start_time = asyncio.get_event_loop().time()
            last_response = None
            stable_count = 0
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                # Get latest response
                responses = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".markdown.prose.w-full.break-words"
                )
                
                if responses:
                    current_response = responses[-1].text.strip()
                    
                    # Check if response has stabilized
                    if current_response == last_response:
                        stable_count += 1
                        if stable_count >= 3:  # Response stable for 3 checks
                            return current_response
                    else:
                        stable_count = 0
                        last_response = current_response
                        
                await asyncio.sleep(1)
                
            return last_response  # Return last response if timeout
            
        except Exception as e:
            self.logger.error(f"Error getting response: {str(e)}")
            return None
            
    async def _set_model(self, driver, model: str):
        """Set the ChatGPT model."""
        try:
            # Click model selector
            model_button = driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Model selector']"
            )
            model_button.click()
            
            # Wait for model list
            await asyncio.sleep(1)
            
            # Click desired model
            model_option = driver.find_element(
                By.XPATH,
                f"//div[contains(text(), '{model}')]"
            )
            model_option.click()
            
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Error setting model to {model}: {str(e)}")
            
    def shutdown(self):
        """No specific cleanup needed as DriverManager handles driver lifecycle."""
        pass 
