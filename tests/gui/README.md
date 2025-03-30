# GUI Tests Documentation

This directory contains the test suite for the PyQt5-based GUI components of the Digital Dreamscape project.

## Test Structure

The test suite is organized into several files, each focusing on different aspects of the GUI:

- `test_digital_dreamscape_tab.py`: Tests for the DigitalDreamscapeTab and its components
- `test_main_tabs.py`: Tests for the main tab container and navigation
- `test_prompt_execution_tab.py`: Tests for prompt execution functionality
- `test_dreamscape_generation_tab.py`: Tests for dreamscape generation features
- `test_community_management_tab.py`: Tests for community management features
- `test_analytics_tab.py`: Tests for analytics visualization
- `test_settings_tab.py`: Tests for application settings
- `test_logs_tab.py`: Tests for log viewing functionality
- `test_historical_chats_tab.py`: Tests for chat history features
- `test_configuration_tab.py`: Tests for configuration management

## Tabs Tests

The `tabs` directory contains tests for individual tabs in the Dream.OS UI:

- `test_meredith_tab.py`: Tests for the MeredithTab component, which provides profile scanning and resonance analysis capabilities. Tests cover UI initialization, ScraperThread logic, button behavior, table rendering, dispatcher integration, and more.

## Running the Tests

### Prerequisites

1. Ensure you have all required dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure you have pytest and its GUI testing plugins:
   ```bash
   pip install pytest pytest-qt pytest-xvfb pytest-timeout pytest-html
   ```

### Running All Tests

To run all GUI tests:
```bash
python tests/gui/run_gui_tests.py
```

### Running Specific Tests

To run a specific test file:
```bash
python tests/gui/run_gui_tests.py --test test_digital_dreamscape_tab.py
```

To run a specific test case:
```bash
python tests/gui/run_gui_tests.py --test test_digital_dreamscape_tab.py::test_tab_initialization
```

### Additional Options

- `--no-html`: Disable HTML report generation
- `--coverage`: Generate coverage report
- `--list`: List available tests without running them

### Test Reports

After running the tests, you can find:
- HTML test report: `chat_mate/tests/gui/report.html`
- Coverage report (if enabled): `chat_mate/tests/gui/coverage/index.html`

## Test Coverage

The test suite covers:

1. Component Initialization
   - Proper creation of all UI components
   - Correct initial state
   - Signal/slot connections

2. User Interface Interaction
   - View mode changes (Standard/Compact/Minimalist)
   - Theme toggling (Light/Dark)
   - Panel visibility controls
   - Component resizing and layout

3. Functionality Testing
   - Template management
   - Context handling
   - Prompt execution
   - Feedback cycle management
   - Metrics updates
   - Episode publishing
   - Cursor IDE integration

4. Error Handling
   - Invalid input validation
   - Error message display
   - Recovery from error states

5. Resource Management
   - Proper cleanup on tab closure
   - Memory leak prevention
   - Timer management

## Writing New Tests

When adding new tests:

1. Create a new test file if testing a new component
2. Add the test file to the `test_files` list in `run_gui_tests.py`
3. Use the provided fixtures from `conftest.py`
4. Follow the existing test patterns for consistency
5. Include docstrings and comments for complex test cases
6. Ensure proper cleanup in teardown methods

## Best Practices

1. Use fixtures for common setup and teardown
2. Mock external dependencies
3. Test both success and failure cases
4. Keep tests focused and independent
5. Use descriptive test names
6. Add appropriate assertions
7. Handle Qt events properly using `QTest`

## Troubleshooting

Common issues and solutions:

1. **Tests hanging**: Use the `--timeout` option or check for event loop issues
2. **Display errors**: Ensure Xvfb is running or use pytest-xvfb
3. **Import errors**: Check PYTHONPATH and sys.path setup
4. **Qt warnings**: Use `-p no:warnings` to suppress Qt warnings
5. **Resource cleanup**: Verify that all widgets are properly closed

For more help, check the pytest documentation or open an issue in the project repository. 