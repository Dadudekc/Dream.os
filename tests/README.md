# ChatMate Tests

This directory contains automated tests for the ChatMate application.

## Test Structure

The tests are organized into the following directories:

- `gui/`: Tests for PyQt5 GUI components
- `integration/`: Integration tests between different components
- `performance/`: Performance and load tests
- Unit tests directly in the `tests/` directory

## Running Tests

### Running All Tests

To run all tests:

```bash
python -m pytest
```

### Running GUI Tests

The GUI tests require a QApplication instance and handle PyQt5 components. Run them with:

```bash
python tests/gui/run_gui_tests.py
```

This will generate an HTML report in `tests/gui/report.html`.

### Running Specific Test Types

To run only unit tests:

```bash
python -m pytest tests/ --ignore=tests/integration --ignore=tests/performance --ignore=tests/gui
```

To run only integration tests:

```bash
python -m pytest tests/integration/
```

To run only performance tests:

```bash
python -m pytest tests/performance/
```

## Test Requirements

The following packages are required for testing:

- pytest
- pytest-mock
- pytest-qt (for GUI tests)
- pytest-html (for HTML reports)

Install them with:

```bash
pip install pytest pytest-mock pytest-qt pytest-html
```

## Writing Tests

### Guidelines for Writing Tests

1. Use descriptive test names that indicate what is being tested
2. Follow the AAA (Arrange, Act, Assert) pattern
3. Mock external dependencies
4. Test both success and failure cases
5. Keep tests independent of each other

### Example Test

```python
def test_my_function():
    # Arrange
    input_data = [1, 2, 3]
    expected_result = 6
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_result
```

### GUI Test Example

```python
def test_my_gui_component(qapp, qtbot):
    # Arrange
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    # Act
    qtbot.mouseClick(widget.button, Qt.LeftButton)
    
    # Assert
    assert widget.label.text() == "Clicked!"
```

## Test Fixtures

Common test fixtures are defined in `conftest.py` files. The main fixtures include:

- `qapp`: QApplication instance for GUI tests
- `qtbot`: QtBot for simulating user interactions
- `mock_*`: Various mock objects for testing

## Adding New Tests

When adding new tests:

1. Create a new file named `test_*.py`
2. Use existing fixtures from conftest.py when appropriate
3. Follow the naming convention `test_*` for test functions
4. Add appropriate imports and documentation
5. Run the tests to ensure they pass

# Test Coverage Tools

This directory contains the tests and tools for ensuring comprehensive test coverage of the Chat Mate codebase.

## Quick Start

To run the complete test coverage pipeline:

**Windows:**
```powershell
.\run_coverage_pipeline.ps1 --visualize --auto-generate
```

**Linux/macOS:**
```bash
./run_coverage_pipeline.sh --visualize --auto-generate
```

## Tools Overview

The test coverage system includes several tools:

1. **overnight_test_generator.py** - Generates tests for Python modules using Ollama's deepseek-r1 model and measures their coverage.
2. **analyze_test_coverage.py** - Analyzes and reports on overall test coverage, identifying modules and files that need additional tests.
3. **generate_missing_tests.py** - Identifies modules without tests and generates template or AI-powered test files.
4. **run_coverage_pipeline.ps1/sh** - Scripts to run the complete test coverage pipeline.

## Usage Options

### Run Coverage Pipeline

**Parameters:**
- `--threshold=<percentage>` - Set the minimum coverage threshold (default: 70%)
- `--visualize` - Generate visualizations of coverage data
- `--auto-generate` - Automatically generate tests for modules without tests
- `--use-ollama` - Use Ollama for test generation instead of templates
- `--module=<module_name>` - Focus on a specific module

### Analyze Test Coverage

```bash
python analyze_test_coverage.py --threshold=70 --visualize
```

**Parameters:**
- `--threshold=<percentage>` - Set the minimum coverage threshold (default: 70%)
- `--visualize` - Generate visualizations of coverage data

### Generate Missing Tests

```bash
python generate_missing_tests.py --auto-generate --use-ollama
```

**Parameters:**
- `--auto-generate` - Automatically generate tests for modules without tests
- `--module=<module_name>` - Generate tests for a specific module only
- `--min-methods=<number>` - Minimum number of methods to consider a file for testing (default: 1)
- `--run-tests` - Run pytest on the generated tests
- `--use-ollama` - Use Ollama for test generation instead of templates

### Overnight Test Generator

```bash
python overnight_test_generator.py --coverage-only
```

**Parameters:**
- `--coverage-only` - Focus on files with insufficient coverage

## Coverage Reports

After running the test coverage pipeline, reports can be found in:

- HTML Report: `reports/coverage/index.html`
- Visualizations: `reports/coverage/visualizations/`

## Best Practices

1. **Regular Testing**: Run the coverage pipeline regularly to identify and address coverage gaps.
2. **Fix Low Coverage**: Focus on files with less than 70% coverage.
3. **Write Meaningful Tests**: Auto-generated tests are a starting point; review and enhance them.
4. **Test New Features**: Add tests as part of feature development, not as an afterthought.
5. **Include Edge Cases**: Make sure tests cover error conditions and edge cases.

## Troubleshooting

- **Import Errors**: If generated tests have import errors, check that the module path is correct.
- **Dependency Issues**: Ensure all test dependencies are installed.
- **Ollama Issues**: If Ollama test generation fails, try the template-based approach instead.
- **Path Issues**: If running on Windows, check that the path separators are correct. 