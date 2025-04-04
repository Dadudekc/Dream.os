"""
Test Generator Service module for generating tests.
"""
from typing import Optional, Any, Dict, List
import logging
import traceback # For detailed error logging

class TestGeneratorService:
    """Service for generating tests."""
    
    def __init__(
        self,
        prompt_manager: Any,
        chat_manager: Any,
        config: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the test generator service.
        
        Args:
            prompt_manager: The prompt manager instance
            chat_manager: The chat manager instance
            config: The configuration manager
            logger: Optional logger instance
        """
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Helper to read the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def generate_test(self, file_path: str, function_name: str) -> Optional[str]:
        """
        Generate a test for a function using the chat manager.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function
            
        Returns:
            Generated test code or None
        """
        try:
            # Get the source code
            file_content = self._read_file_content(file_path)
            if not file_content:
                return None # Error logged in helper
            
            # Get the appropriate prompt template
            prompt = self.prompt_manager.get_prompt("test_generation")
            if not prompt:
                self.logger.warning("No test generation prompt template found")
                return None
            
            # Format the prompt with the function details and source context
            formatted_prompt = prompt.format(
                file_path=file_path,
                function_name=function_name,
                # Pass full file content as context for now
                source_code=file_content 
            )
            
            # TODO: Implement actual test generation - Replaced below
            # Placeholder code removed
            # test_code = f"""...
            # """
            # self.logger.info(f"Generated test for: {function_name}")
            # return test_code
            
            # Use ChatManager to generate the test
            self.logger.info(f"Requesting test generation for {function_name} in {file_path}...")
            generated_code = self.chat_manager.send_message(formatted_prompt)

            if generated_code and "error" not in generated_code.lower(): # Basic check
                 self.logger.info(f"Successfully generated test for: {function_name}")
                 return generated_code
            else:
                 self.logger.error(f"Failed to generate test for {function_name}. Response: {generated_code}")
                 return None
            
        except Exception as e:
            self.logger.error(f"Error generating test: {e}\n{traceback.format_exc()}")
            return None
            
    def generate_test_suite(self, file_path: str) -> Optional[str]:
        """
        Generate a test suite for a file using the chat manager.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Generated test suite code or None
        """
        try:
            # Get the source code
            file_content = self._read_file_content(file_path)
            if not file_content:
                return None # Error logged in helper

            # Get the appropriate prompt template
            prompt = self.prompt_manager.get_prompt("test_suite_generation")
            if not prompt:
                self.logger.warning("No test suite generation prompt template found")
                return None
            
            # Format the prompt with the file details and source code
            formatted_prompt = prompt.format(
                file_path=file_path,
                source_code=file_content
            )
            
            # TODO: Implement actual test suite generation - Replaced below
            # Placeholder code removed
            # test_suite_code = f"""...
            # """
            # self.logger.info(f"Generated test suite for: {file_path}")
            # return test_suite_code

            # Use ChatManager to generate the test suite
            self.logger.info(f"Requesting test suite generation for {file_path}...")
            generated_code = self.chat_manager.send_message(formatted_prompt)

            if generated_code and "error" not in generated_code.lower(): # Basic check
                 self.logger.info(f"Successfully generated test suite for: {file_path}")
                 return generated_code
            else:
                 self.logger.error(f"Failed to generate test suite for {file_path}. Response: {generated_code}")
                 return None
            
        except Exception as e:
            self.logger.error(f"Error generating test suite: {e}\n{traceback.format_exc()}")
            return None 