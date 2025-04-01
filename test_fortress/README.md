# Test Fortress 🏰

A comprehensive testing framework that treats your codebase like a fortress under siege. Not just checking if it works, but actively trying to break it in every conceivable way.

## Philosophy

> "You test a project so well that when it runs, it has no problems... by designing the test system like a training simulation for war."

The Test Fortress combines multiple testing strategies into a unified assault on your code's weaknesses:

1. **Unit Testing + Contracts** (Red-Green-Refactor)
2. **Integration Testing** (Real Usage Simulation)
3. **Failure Mode Injection** (Systematic Breaking)
4. **Mutation Testing** (Test Your Tests)
5. **Validation + Consistency** (Runtime Checks)
6. **Preflight System** (Launch Readiness)

## Features

- 🎯 **Comprehensive Test Runner**
  - Unit tests with coverage reporting
  - Mutation testing to validate test quality
  - Failure injection from templates
  - Integration test coordination

- 💥 **Failure Injection System**
  - Template-based failure scenarios
  - Missing files/config
  - Invalid input data
  - Service timeouts/failures
  - Memory corruption
  - Race conditions

- 🔍 **Validation Framework**
  - Runtime consistency checks
  - Schema validation
  - State verification
  - Log message validation

- 📊 **Reporting**
  - Detailed test results
  - Coverage metrics
  - Mutation scores
  - Failure scenario statistics

## Installation

```bash
cd test_fortress
pip install -r requirements.txt
```

## Usage

### Basic Test Run

```bash
python test_runner.py
```

### Run Specific Test Types

```bash
# Unit tests only
python test_runner.py --unit-only

# Mutation testing only
python test_runner.py --mutation-only

# Failure injection only
python test_runner.py --failure-only
```

### Configure Test Targets

```bash
python test_runner.py \
  --coverage-target 95.0 \
  --mutation-target 80.0
```

## Failure Templates

The system includes templates for common failure scenarios:

- `missing_config.json` - Missing configuration files
- `invalid_task.json` - Malformed task data
- `service_timeout.json` - Service timeouts and retries
- `memory_corruption.json` - Memory store corruption
- `race_condition.json` - Concurrent execution issues

### Creating Custom Templates

Templates are JSON files with the following structure:

```json
{
    "id": "unique_id",
    "type": "failure_type",
    "description": "What this tests",
    "expected_behavior": {
        "should_x": true,
        "should_y": false
    },
    "validation": {
        "verify_a": true,
        "verify_b": true
    }
}
```

## Contributing

1. Create new failure templates in `failure_templates/`
2. Add corresponding test implementations
3. Update documentation
4. Run the full test suite
5. Submit a PR

## License

MIT

## Acknowledgments

Inspired by:
- Military training simulations
- Chaos engineering principles
- Property-based testing
- Mutation testing theory 