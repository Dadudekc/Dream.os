# Dreamscape Tab Test Suite

This directory contains a comprehensive test suite for the Dreamscape Generation Tab of Chat Mate.

## Test Structure

The test suite is organized into three main categories:

1. **Unit Tests** - Tests for individual components of the Dreamscape tab
2. **Integration Tests** - Tests for interactions between components
3. **UI Component Tests** - Tests for UI elements and their behavior

## Files

- `test_dreamscape_tab_unit.py` - Unit tests for Dreamscape tab components
- `test_dreamscape_tab_integration.py` - Integration tests for component interactions
- `test_dreamscape_ui_components.py` - Tests for UI components and layout
- `run_dreamscape_tests.py` - Script to run all tests
- `pytest.ini` - Configuration for pytest

## Running Tests

To run all tests:

```bash
python run_dreamscape_tests.py
```

To run tests with coverage reporting:

```bash
python run_dreamscape_tests.py --coverage
```

To run a specific test file:

```bash
pytest test_dreamscape_tab_unit.py -v
```

## Test Coverage

The test suite aims to provide comprehensive coverage of:

- UI initialization and component properties
- Service interactions (chat manager, episode generator, etc.)
- User interaction flow (selecting chats, generating episodes, sharing)
- Episode generation processes
- Error handling

## Mocking Strategy

The tests use a consistent mocking strategy to isolate components:

1. Service mocks are provided via fixtures
2. The `ServiceInitializer` is patched to return mock services
3. Temporary output directories are used for file operations
4. UI events are simulated for interaction testing

## Future Improvements

Planned improvements for the test suite include:

- Event simulation testing for complex user interactions
- Performance testing for episode generation
- CI/CD integration for automated test runs
- Visual regression testing for UI elements

## Developer Guidelines

When developing tests for the Dreamscape tab, follow these guidelines:

1. **Follow TDD principles**:
   - Write failing tests first
   - Implement code to make tests pass
   - Refactor while keeping tests green

2. **Keep tests isolated**:
   - Each test should run independently
   - Use fixtures for common setup
   - Clean up any modifications after tests

3. **Test both happy and error paths**:
   - Verify correct behavior with valid inputs
   - Test error handling with invalid inputs
   - Test edge cases thoroughly

4. **Organize tests logically**:
   - Group related tests in the same file
   - Maintain clear naming conventions
   - Use descriptive test names that explain the purpose 