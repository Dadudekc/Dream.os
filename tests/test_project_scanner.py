import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from ProjectScanner import (
    ProjectScanner,
    LanguageAnalyzer,
    FileProcessor,
    ReportGenerator,
    BotWorker,
    MultibotManager
)

# Test data
SAMPLE_PYTHON_CODE = """
def test_function():
    pass

class TestClass:
    def method1(self):
        pass
    def method2(self):
        pass

@app.route('/test')
def route_handler():
    pass
"""

SAMPLE_RUST_CODE = """
fn test_function() {
    // test
}

struct TestStruct {
    field: i32,
}

impl TestStruct {
    fn method1(&self) {}
    fn method2(&self) {}
}
"""

SAMPLE_JS_CODE = """
function testFunction() {
    // test
}

class TestClass {
    method1() {}
    method2() {}
}

app.get('/test', (req, res) => {});
"""

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    # Create Python files
    py_dir = tmp_path / "python_pkg"
    py_dir.mkdir()
    (py_dir / "module1.py").write_text(SAMPLE_PYTHON_CODE)
    (py_dir / "module2.py").write_text(SAMPLE_PYTHON_CODE)
    
    # Create Rust files
    rs_dir = tmp_path / "rust_pkg"
    rs_dir.mkdir()
    (rs_dir / "module1.rs").write_text(SAMPLE_RUST_CODE)
    
    # Create JS files
    js_dir = tmp_path / "js_pkg"
    js_dir.mkdir()
    (js_dir / "module1.js").write_text(SAMPLE_JS_CODE)
    
    return tmp_path

@pytest.fixture
def mock_cache():
    """Create a mock cache for testing."""
    return {
        "python_pkg/module1.py": {"hash": "abc123"},
        "python_pkg/module2.py": {"hash": "def456"},
        "rust_pkg/module1.rs": {"hash": "ghi789"},
        "js_pkg/module1.js": {"hash": "jkl012"}
    }

def test_language_analyzer_analyze_python():
    """Test Python code analysis."""
    analyzer = LanguageAnalyzer()
    result = analyzer._analyze_python(SAMPLE_PYTHON_CODE)
    
    assert "test_function" in result["functions"]
    assert "TestClass" in result["classes"]
    assert len(result["classes"]["TestClass"]) == 2
    assert len(result["routes"]) == 1
    assert result["routes"][0]["path"] == "/test"

def test_language_analyzer_analyze_rust():
    """Test Rust code analysis."""
    analyzer = LanguageAnalyzer()
    result = analyzer._analyze_rust(SAMPLE_RUST_CODE)
    
    assert "test_function" in result["functions"]
    assert "TestStruct" in result["classes"]
    assert len(result["classes"]["TestStruct"]) == 2

def test_language_analyzer_analyze_javascript():
    """Test JavaScript code analysis."""
    analyzer = LanguageAnalyzer()
    result = analyzer._analyze_javascript(SAMPLE_JS_CODE)
    
    assert "testFunction" in result["functions"]
    assert "TestClass" in result["classes"]
    assert len(result["classes"]["TestClass"]) == 2
    assert len(result["routes"]) == 1
    assert result["routes"][0]["path"] == "/test"

def test_file_processor_hash_file(temp_project):
    """Test file hashing functionality."""
    processor = FileProcessor(
        temp_project,
        {},
        MagicMock(),
        set()
    )
    
    test_file = temp_project / "test.txt"
    test_file.write_text("test content")
    
    hash1 = processor.hash_file(test_file)
    assert hash1 != ""
    
    # Same content should produce same hash
    hash2 = processor.hash_file(test_file)
    assert hash1 == hash2
    
    # Different content should produce different hash
    test_file.write_text("different content")
    hash3 = processor.hash_file(test_file)
    assert hash1 != hash3

def test_file_processor_should_exclude(temp_project):
    """Test file exclusion logic."""
    processor = FileProcessor(
        temp_project,
        {},
        MagicMock(),
        {"excluded_dir"}
    )
    
    # Test default exclusions
    assert processor.should_exclude(temp_project / "venv" / "test.py")
    assert processor.should_exclude(temp_project / "__pycache__" / "test.py")
    
    # Test custom exclusions
    assert processor.should_exclude(temp_project / "excluded_dir" / "test.py")
    assert not processor.should_exclude(temp_project / "included_dir" / "test.py")

def test_report_generator_save_report(temp_project):
    """Test report saving functionality."""
    analysis = {
        "python_pkg/module1.py": {
            "functions": ["test_function"],
            "classes": {"TestClass": ["method1", "method2"]},
            "routes": [{"path": "/test"}]
        }
    }
    
    generator = ReportGenerator(temp_project, analysis)
    generator.save_report()
    
    report_path = temp_project / "project_analysis.json"
    assert report_path.exists()
    
    with open(report_path) as f:
        saved_data = json.load(f)
    assert saved_data == analysis

def test_report_generator_generate_init_files(temp_project):
    """Test __init__.py file generation."""
    analysis = {
        "python_pkg/module1.py": {},
        "python_pkg/module2.py": {}
    }
    
    generator = ReportGenerator(temp_project, analysis)
    generator.generate_init_files(overwrite=True)
    
    init_file = temp_project / "python_pkg" / "__init__.py"
    assert init_file.exists()
    
    content = init_file.read_text()
    assert "from . import module1" in content
    assert "from . import module2" in content
    assert "'module1'" in content
    assert "'module2'" in content

def test_project_scanner_scan_project(temp_project, mock_cache):
    """Test the main project scanning functionality."""
    with patch("ProjectScanner.ProjectScanner.load_cache", return_value=mock_cache):
        scanner = ProjectScanner(temp_project)
        
        # Mock the file processor to avoid actual file operations
        scanner.file_processor.process_file = Mock(return_value=(
            "python_pkg/module1.py",
            {
                "functions": ["test_function"],
                "classes": {"TestClass": ["method1", "method2"]},
                "routes": [{"path": "/test"}]
            }
        ))
        
        scanner.scan_project()
        
        assert "python_pkg/module1.py" in scanner.analysis
        assert scanner.file_processor.process_file.called

def test_bot_worker():
    """Test the BotWorker class."""
    task_queue = MagicMock()
    results_list = []
    scanner = MagicMock()
    status_callback = Mock()
    
    worker = BotWorker(task_queue, results_list, scanner, status_callback)
    
    # Simulate processing a file
    test_file = Path("test.py")
    task_queue.get.return_value = test_file
    scanner._process_file.return_value = ("test.py", {"functions": ["test"]})
    
    # Run the worker once
    worker.run()
    
    assert scanner._process_file.called_with(test_file)
    assert status_callback.called_with(test_file, ("test.py", {"functions": ["test"]}))

def test_multibot_manager():
    """Test the MultibotManager class."""
    scanner = MagicMock()
    manager = MultibotManager(scanner, num_workers=2)
    
    test_file = Path("test.py")
    manager.add_task(test_file)
    
    assert manager.task_queue.get() == test_file
    assert len(manager.workers) == 2 