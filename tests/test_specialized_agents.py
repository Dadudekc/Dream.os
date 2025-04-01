import pytest
import tempfile
import os
from datetime import datetime
from core.Agents.specialized_agents import RefactorAgent, TestAgent, DocAgent

@pytest.fixture
def refactor_agent():
    return RefactorAgent()

@pytest.fixture
def test_agent():
    return TestAgent()

@pytest.fixture
def doc_agent():
    return DocAgent()

@pytest.fixture
def sample_python_file():
    """Create a temporary Python file with sample code for testing."""
    code = """
class ExampleClass:
    def long_method(self):
        # Calculate total
        total = 0
        for i in range(10):
            total += i
        
        # Process results
        result = total * 2
        return result
    
    def process_data(self, data):
        processed = []
        for item in data:
            processed.append(item * 2)
        return processed
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        return f.name

def test_refactor_agent_initialization(refactor_agent):
    """Test RefactorAgent initialization."""
    assert refactor_agent.name == "RefactorAgent"
    assert refactor_agent.task_queue == []
    assert refactor_agent.running is False

def test_refactor_agent_extract_method(refactor_agent, sample_python_file):
    """Test extracting a method from existing code."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "extract_method",
        "parameters": {
            "start_line": 4,
            "end_line": 8,
            "method_name": "calculate_total"
        }
    }
    
    result = refactor_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["refactor_type"] == "extract_method"
    assert result["changes_made"] is True
    
    # Verify the changes
    with open(sample_python_file, 'r') as f:
        modified_code = f.read()
        assert "def calculate_total(self):" in modified_code
        assert "self.calculate_total()" in modified_code
    
    # Clean up
    os.unlink(sample_python_file)

def test_refactor_agent_rename_variable(refactor_agent, sample_python_file):
    """Test renaming a variable in the code."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "rename_variable",
        "parameters": {
            "old_name": "total",
            "new_name": "sum_total"
        }
    }
    
    result = refactor_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["refactor_type"] == "rename_variable"
    assert result["changes_made"] is True
    
    # Verify the changes
    with open(sample_python_file, 'r') as f:
        modified_code = f.read()
        assert "sum_total = 0" in modified_code
        assert "sum_total += i" in modified_code
        assert "result = sum_total * 2" in modified_code
    
    # Clean up
    os.unlink(sample_python_file)

def test_refactor_agent_inline_function(refactor_agent, sample_python_file):
    """Test inlining a function call."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "inline_function",
        "parameters": {
            "function_name": "process_data"
        }
    }
    
    result = refactor_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["refactor_type"] == "inline_function"
    assert result["changes_made"] is True
    
    # Clean up
    os.unlink(sample_python_file)

def test_refactor_agent_invalid_task(refactor_agent):
    """Test RefactorAgent with invalid task."""
    task = {
        "file_path": "test.py"
        # Missing refactor_type
    }
    
    with pytest.raises(ValueError, match="Missing required parameters"):
        refactor_agent.handle_task(task)

def test_refactor_agent_invalid_file(refactor_agent):
    """Test RefactorAgent with non-existent file."""
    task = {
        "file_path": "nonexistent.py",
        "refactor_type": "extract_method",
        "parameters": {
            "start_line": 1,
            "end_line": 5,
            "method_name": "new_method"
        }
    }
    
    with pytest.raises(FileNotFoundError):
        refactor_agent.handle_task(task)

def test_refactor_agent_invalid_method_params(refactor_agent, sample_python_file):
    """Test RefactorAgent with invalid method parameters."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "extract_method",
        "parameters": {
            "start_line": 1,
            "end_line": 5
            # Missing method_name
        }
    }
    
    with pytest.raises(ValueError, match="Missing required parameters"):
        refactor_agent.handle_task(task)
    
    # Clean up
    os.unlink(sample_python_file)

def test_refactor_agent_invalid_rename_params(refactor_agent, sample_python_file):
    """Test RefactorAgent with invalid rename parameters."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "rename_variable",
        "parameters": {
            "old_name": "total"
            # Missing new_name
        }
    }
    
    with pytest.raises(ValueError, match="Missing required parameters"):
        refactor_agent.handle_task(task)
    
    # Clean up
    os.unlink(sample_python_file)

def test_refactor_agent_unsupported_type(refactor_agent, sample_python_file):
    """Test RefactorAgent with unsupported refactoring type."""
    task = {
        "file_path": sample_python_file,
        "refactor_type": "unsupported_type",
        "parameters": {}
    }
    
    with pytest.raises(ValueError, match="Unsupported refactoring type"):
        refactor_agent.handle_task(task)
    
    # Clean up
    os.unlink(sample_python_file)

def test_test_agent_initialization(test_agent):
    """Test TestAgent initialization."""
    assert test_agent.name == "TestAgent"
    assert test_agent.task_queue == []
    assert test_agent.running is False

def test_test_agent_handle_task(test_agent):
    """Test TestAgent task handling."""
    task = {
        "file_path": "test.py",
        "test_type": "unit",
        "framework": "pytest",
        "coverage_target": 95
    }
    
    result = test_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["test_type"] == "unit"
    assert result["file_path"] == "test.py"
    assert result["framework"] == "pytest"
    assert result["coverage"] == 95.0
    assert result["tests_generated"] == 10
    assert result["tests_passed"] == 10
    assert "timestamp" in result

def test_test_agent_invalid_task(test_agent):
    """Test TestAgent with invalid task."""
    task = {
        "file_path": "test.py"
        # Missing test_type
    }
    
    with pytest.raises(ValueError, match="Missing required parameters"):
        test_agent.handle_task(task)

def test_doc_agent_initialization(doc_agent):
    """Test DocAgent initialization."""
    assert doc_agent.name == "DocAgent"
    assert doc_agent.task_queue == []
    assert doc_agent.running is False

def test_doc_agent_handle_task(doc_agent):
    """Test DocAgent task handling."""
    task = {
        "file_path": "test.py",
        "doc_type": "api",
        "format": "markdown",
        "include_examples": True
    }
    
    result = doc_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["doc_type"] == "api"
    assert result["file_path"] == "test.py"
    assert result["format"] == "markdown"
    assert result["include_examples"] is True
    assert result["sections_generated"] == 5
    assert result["examples_generated"] == 3
    assert "timestamp" in result

def test_doc_agent_handle_task_no_examples(doc_agent):
    """Test DocAgent task handling without examples."""
    task = {
        "file_path": "test.py",
        "doc_type": "api",
        "format": "markdown",
        "include_examples": False
    }
    
    result = doc_agent.handle_task(task)
    
    assert result["status"] == "success"
    assert result["doc_type"] == "api"
    assert result["file_path"] == "test.py"
    assert result["format"] == "markdown"
    assert result["include_examples"] is False
    assert result["sections_generated"] == 5
    assert result["examples_generated"] == 0
    assert "timestamp" in result

def test_doc_agent_invalid_task(doc_agent):
    """Test DocAgent with invalid task."""
    task = {
        "file_path": "test.py"
        # Missing doc_type
    }
    
    with pytest.raises(ValueError, match="Missing required parameters"):
        doc_agent.handle_task(task) 
