import os
import sys
import unittest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ResilientPromptExecutor import ResilientPromptExecutor

class TestResilientPromptExecutor(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize ResilientPromptExecutor
        self.executor = ResilientPromptExecutor(
            output_dir=self.test_output_dir,
            max_retries=3,
            retry_delay=1,
            timeout=5
        )
        
        # Test data
        self.test_prompt = {
            "id": "test_prompt_1",
            "type": "text_generation",
            "content": "Test prompt content",
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 100
            }
        }
    
    def test_initialization(self):
        """Test if ResilientPromptExecutor initializes correctly."""
        self.assertIsNotNone(self.executor)
        self.assertEqual(self.executor.max_retries, 3)
        self.assertEqual(self.executor.retry_delay, 1)
        self.assertEqual(self.executor.timeout, 5)
        self.assertTrue(os.path.exists(self.executor.output_dir))
        self.assertIsNotNone(self.executor.logger)
    
    def test_execute_prompt(self):
        """Test basic prompt execution functionality."""
        # Mock API response
        mock_response = {
            "id": "test_response_1",
            "content": "Test response content",
            "metadata": {
                "tokens": 50,
                "finish_reason": "stop"
            }
        }
        
        with patch.object(self.executor, '_call_api', return_value=mock_response):
            # Execute prompt
            response = self.executor.execute_prompt(self.test_prompt)
            
            # Verify response
            self.assertEqual(response["id"], "test_response_1")
            self.assertEqual(response["content"], "Test response content")
            self.assertEqual(response["metadata"]["tokens"], 50)
    
    def test_execute_prompt_with_retry(self):
        """Test prompt execution with retry functionality."""
        # Mock API failures and success
        mock_responses = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            {
                "id": "test_response_1",
                "content": "Test response content"
            }
        ]
        
        with patch.object(self.executor, '_call_api', side_effect=mock_responses):
            # Execute prompt
            response = self.executor.execute_prompt(self.test_prompt)
            
            # Verify response after retries
            self.assertEqual(response["id"], "test_response_1")
            self.assertEqual(response["content"], "Test response content")
    
    def test_execute_prompt_timeout(self):
        """Test prompt execution timeout handling."""
        # Mock slow API response
        def slow_api_call(*args, **kwargs):
            time.sleep(6)  # Longer than timeout
            return {"id": "test_response_1", "content": "Test response content"}
        
        with patch.object(self.executor, '_call_api', side_effect=slow_api_call):
            # Execute prompt
            with self.assertRaises(TimeoutError):
                self.executor.execute_prompt(self.test_prompt)
    
    def test_execute_prompt_validation(self):
        """Test prompt validation functionality."""
        # Create invalid prompt
        invalid_prompt = {
            "id": "test_prompt_2",
            "type": "text_generation"
            # Missing required fields
        }
        
        # Execute invalid prompt
        with self.assertRaises(ValueError):
            self.executor.execute_prompt(invalid_prompt)
    
    def test_save_response(self):
        """Test response saving functionality."""
        # Create test response
        test_response = {
            "id": "test_response_1",
            "content": "Test response content",
            "metadata": {
                "prompt_id": "test_prompt_1",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Save response
        file_path = self.executor.save_response(test_response)
        
        # Verify file exists
        self.assertTrue(os.path.exists(file_path))
        
        # Verify file content
        with open(file_path, 'r') as f:
            saved_content = json.load(f)
            self.assertEqual(saved_content["id"], "test_response_1")
            self.assertEqual(saved_content["content"], "Test response content")
    
    def test_load_response(self):
        """Test response loading functionality."""
        # Create and save test response
        test_response = {
            "id": "test_response_1",
            "content": "Test response content"
        }
        file_path = self.executor.save_response(test_response)
        
        # Load response
        loaded_response = self.executor.load_response(file_path)
        
        # Verify loaded response
        self.assertEqual(loaded_response["id"], "test_response_1")
        self.assertEqual(loaded_response["content"], "Test response content")
    
    def test_handle_error(self):
        """Test error handling functionality."""
        # Mock API error
        mock_error = Exception("Test API error")
        
        with patch.object(self.executor, '_call_api', side_effect=mock_error):
            # Execute prompt
            with self.assertRaises(Exception):
                self.executor.execute_prompt(self.test_prompt)
            
            # Verify error was logged
            log_file = os.path.join(self.test_output_dir, "executor.log")
            self.assertTrue(os.path.exists(log_file))
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                self.assertIn("Test API error", log_content)
    
    def test_cleanup_old_responses(self):
        """Test old response cleanup functionality."""
        # Create old response
        old_response = {
            "id": "old_response_1",
            "content": "Old response content",
            "metadata": {
                "timestamp": (datetime.now() - timedelta(days=8)).isoformat()
            }
        }
        self.executor.save_response(old_response)
        
        # Create recent response
        recent_response = {
            "id": "recent_response_1",
            "content": "Recent response content",
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
        self.executor.save_response(recent_response)
        
        # Cleanup old responses
        self.executor.cleanup_old_responses(days=7)
        
        # Verify cleanup
        response_files = os.listdir(self.test_output_dir)
        self.assertEqual(len(response_files), 1)
        self.assertIn("recent_response_1", response_files[0])
    
    def test_get_execution_metrics(self):
        """Test execution metrics collection."""
        # Execute multiple prompts
        mock_response = {
            "id": "test_response_1",
            "content": "Test response content"
        }
        
        with patch.object(self.executor, '_call_api', return_value=mock_response):
            for i in range(3):
                prompt = self.test_prompt.copy()
                prompt["id"] = f"test_prompt_{i}"
                self.executor.execute_prompt(prompt)
        
        # Get metrics
        metrics = self.executor.get_execution_metrics()
        
        # Verify metrics
        self.assertIn("total_executions", metrics)
        self.assertIn("successful_executions", metrics)
        self.assertIn("failed_executions", metrics)
        self.assertIn("average_execution_time", metrics)
    
    def test_validate_response(self):
        """Test response validation functionality."""
        # Create valid response
        valid_response = {
            "id": "test_response_1",
            "content": "Test response content",
            "metadata": {
                "tokens": 50,
                "finish_reason": "stop"
            }
        }
        
        # Create invalid response
        invalid_response = {
            "id": "test_response_2"
            # Missing required fields
        }
        
        # Verify validation
        self.assertTrue(self.executor._validate_response(valid_response))
        self.assertFalse(self.executor._validate_response(invalid_response))
    
    def test_preprocess_prompt(self):
        """Test prompt preprocessing functionality."""
        # Create prompt with preprocessing needed
        prompt = self.test_prompt.copy()
        prompt["content"] = "  Test prompt content  "  # Extra whitespace
        
        # Preprocess prompt
        processed_prompt = self.executor._preprocess_prompt(prompt)
        
        # Verify preprocessing
        self.assertEqual(processed_prompt["content"], "Test prompt content")
    
    def test_postprocess_response(self):
        """Test response postprocessing functionality."""
        # Create response with postprocessing needed
        response = {
            "id": "test_response_1",
            "content": "  Test response content  ",  # Extra whitespace
            "metadata": {
                "tokens": 50,
                "finish_reason": "stop"
            }
        }
        
        # Postprocess response
        processed_response = self.executor._postprocess_response(response)
        
        # Verify postprocessing
        self.assertEqual(processed_response["content"], "Test response content")
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 