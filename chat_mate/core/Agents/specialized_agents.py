from typing import Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.interfaces import ILoggingAgent
from chat_mate.core.Agents.CursorAgentInterface import CursorAgentInterface
from .refactoring_utils import (
    CodeAnalyzer,
    CodeTransformer,
    CodeFormatter,
    read_file,
    write_file,
    parse_code,
    unparse_code
)

class SpecializedAgent(CursorAgentInterface):
    """Base class for specialized agents."""

    def __init__(self, config_manager: ConfigManager, logger: ILoggingAgent):
        self.config_manager = config_manager
        self.logger = logger
        self.analyzer = CodeAnalyzer()
        self.transformer = CodeTransformer()
        self.formatter = CodeFormatter()
        
    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle code refactoring tasks.
        
        Args:
            task: Dictionary containing task details with keys:
                - file_path: Path to the file to refactor
                - refactor_type: Type of refactoring (e.g., "extract_method", "rename_variable")
                - parameters: Additional parameters for the refactoring
                
        Returns:
            Dict containing the refactoring results
        """
        try:
            file_path = task.get("file_path")
            refactor_type = task.get("refactor_type")
            parameters = task.get("parameters", {})
            
            if not file_path or not refactor_type:
                raise ValueError("Missing required parameters: file_path and refactor_type")
            
            self.logger.log(
                f"Starting refactoring task: {refactor_type} on {file_path}",
                domain="RefactorAgent",
                level="INFO"
            )
            
            # Read the file
            code = read_file(file_path)
            
            # Parse the code into an AST
            tree = parse_code(code)
            
            # Apply the refactoring based on type
            changes_made = False
            if refactor_type == "extract_method":
                start_line = parameters.get("start_line")
                end_line = parameters.get("end_line")
                new_method_name = parameters.get("method_name")
                
                if not all([start_line, end_line, new_method_name]):
                    raise ValueError("Missing required parameters for extract_method")
                
                tree = self.transformer.extract_method(tree, start_line, end_line, new_method_name)
                changes_made = True
                
            elif refactor_type == "rename_variable":
                old_name = parameters.get("old_name")
                new_name = parameters.get("new_name")
                
                if not all([old_name, new_name]):
                    raise ValueError("Missing required parameters for rename_variable")
                
                tree = self.transformer.rename_variable(tree, old_name, new_name)
                changes_made = True
                
            elif refactor_type == "inline_function":
                function_name = parameters.get("function_name")
                
                if not function_name:
                    raise ValueError("Missing required parameter function_name for inline_function")
                
                tree = self.transformer.inline_function(tree, function_name)
                changes_made = True
                
            else:
                raise ValueError(f"Unsupported refactoring type: {refactor_type}")
            
            if changes_made:
                # Convert AST back to code
                new_code = unparse_code(tree)
                
                # Format the code
                formatted_code = self.formatter.format_code(new_code)
                
                # Write back to file
                write_file(file_path, formatted_code)
                
                self.logger.log(
                    f"Successfully applied {refactor_type} refactoring",
                    domain="RefactorAgent",
                    level="INFO"
                )
            
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "refactor_type": refactor_type,
                "file_path": file_path,
                "changes_made": changes_made,
                "parameters": parameters
            }
            
            self.logger.log(
                f"Completed refactoring task: {refactor_type}",
                domain="RefactorAgent",
                level="INFO"
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                f"Refactoring task failed: {str(e)}",
                domain="RefactorAgent"
            )
            raise

class TestAgent(BaseAgent):
    """Agent responsible for generating and running tests."""
    
    def __init__(self, name: str = "TestAgent"):
        super().__init__(name)
        self.logger = CompositeLogger([ConsoleLogger()])
        
    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle test generation and execution tasks.
        
        Args:
            task: Dictionary containing task details with keys:
                - file_path: Path to the file to test
                - test_type: Type of test (e.g., "unit", "integration")
                - framework: Testing framework to use (e.g., "pytest", "unittest")
                - coverage_target: Minimum coverage percentage
                
        Returns:
            Dict containing the test results
        """
        try:
            file_path = task.get("file_path")
            test_type = task.get("test_type")
            framework = task.get("framework", "pytest")
            coverage_target = task.get("coverage_target", 90)
            
            if not file_path or not test_type:
                raise ValueError("Missing required parameters: file_path and test_type")
            
            self.logger.log(
                f"Starting test generation task: {test_type} tests for {file_path}",
                domain="TestAgent",
                level="INFO"
            )
            
            # TODO: Implement actual test generation logic here
            # This would involve:
            # 1. Analyzing the source code
            # 2. Generating appropriate test cases
            # 3. Writing test files
            # 4. Running tests and collecting coverage
            
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "test_type": test_type,
                "file_path": file_path,
                "framework": framework,
                "coverage": 95.0,  # Placeholder
                "tests_generated": 10,  # Placeholder
                "tests_passed": 10  # Placeholder
            }
            
            self.logger.log(
                f"Completed test generation task: {test_type}",
                domain="TestAgent",
                level="INFO"
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                f"Test generation task failed: {str(e)}",
                domain="TestAgent"
            )
            raise

class DocAgent(BaseAgent):
    """Agent responsible for generating documentation."""
    
    def __init__(self, name: str = "DocAgent"):
        super().__init__(name)
        self.logger = CompositeLogger([ConsoleLogger()])
        
    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle documentation generation tasks.
        
        Args:
            task: Dictionary containing task details with keys:
                - file_path: Path to the file to document
                - doc_type: Type of documentation (e.g., "api", "usage", "architecture")
                - format: Output format (e.g., "markdown", "html", "rst")
                - include_examples: Whether to include usage examples
                
        Returns:
            Dict containing the documentation results
        """
        try:
            file_path = task.get("file_path")
            doc_type = task.get("doc_type")
            format = task.get("format", "markdown")
            include_examples = task.get("include_examples", True)
            
            if not file_path or not doc_type:
                raise ValueError("Missing required parameters: file_path and doc_type")
            
            self.logger.log(
                f"Starting documentation task: {doc_type} docs for {file_path}",
                domain="DocAgent",
                level="INFO"
            )
            
            # TODO: Implement actual documentation generation logic here
            # This would involve:
            # 1. Analyzing the source code
            # 2. Generating appropriate documentation
            # 3. Formatting according to specified format
            # 4. Writing documentation files
            
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "doc_type": doc_type,
                "file_path": file_path,
                "format": format,
                "include_examples": include_examples,
                "sections_generated": 5,  # Placeholder
                "examples_generated": 3 if include_examples else 0  # Placeholder
            }
            
            self.logger.log(
                f"Completed documentation task: {doc_type}",
                domain="DocAgent",
                level="INFO"
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                f"Documentation task failed: {str(e)}",
                domain="DocAgent"
            )
            raise 
