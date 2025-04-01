# Dream.OS Intelligence Scanner

A comprehensive code analysis and optimization tool for Dream.OS that helps identify opportunities for improvement in your codebase.

## Features

- **Deep AST Analysis**: Analyzes code structure, complexity, and quality metrics
- **Test Coverage Analysis**: Maps test files to implementations and suggests missing tests
- **Agent Analysis**: Identifies and profiles agent-related code, suggesting optimizations
- **Dependency Analysis**: Tracks import relationships and suggests architectural improvements
- **Code Quality Metrics**: Measures complexity, documentation, and maintainability
- **Optimization Suggestions**: Provides actionable insights for code improvement

## Installation

```bash
# Clone the repository
git clone https://github.com/dream-os/intelligence-scanner.git
cd intelligence-scanner

# Install the package
pip install -e .

# For development dependencies
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

The scanner can be run from the command line using the `dream-scan` command:

```bash
# Basic usage
dream-scan /path/to/project

# Show summary only
dream-scan /path/to/project --summary-only

# Focus on specific aspects
dream-scan /path/to/project --focus tests
dream-scan /path/to/project --focus agents
dream-scan /path/to/project --focus dependencies
dream-scan /path/to/project --focus quality

# Full analysis with custom output
dream-scan /path/to/project -o analysis_report.json

# Verbose output
dream-scan /path/to/project -v

# Force full rescan
dream-scan /path/to/project --no-incremental
```

### Python API

You can also use the scanner programmatically:

```python
from scanner import IntelligenceScanner
from pathlib import Path

# Initialize scanner
scanner = IntelligenceScanner(Path("/path/to/project"))

# Run analysis
report = scanner.scan_project()

# Get summary statistics
stats = scanner.get_summary_stats()

# Save report
scanner.save_report(Path("report.json"))
```

## Analysis Components

### Deep AST Analyzer

- Parses Python source code using AST
- Extracts functions, classes, and their relationships
- Calculates complexity metrics
- Analyzes documentation coverage

### Test Mapper

- Maps test files to their implementations
- Calculates test coverage metrics
- Identifies missing tests
- Suggests test improvements

### Agent Mapper

- Identifies agent-related code
- Profiles agent capabilities and maturity
- Tracks agent dependencies
- Suggests agent optimizations

### Dependency Mapper

- Builds import dependency graph
- Detects circular dependencies
- Identifies high-risk imports
- Suggests architectural improvements

## Report Format

The analysis report is generated in JSON format with the following structure:

```json
{
    "project_info": {
        "root": "/path/to/project",
        "files_analyzed": 100,
        "last_scan_time": "2024-03-14T12:00:00"
    },
    "analysis_results": {
        "file_analysis": {
            "path/to/file.py": {
                "classes": [...],
                "functions": [...],
                "imports": [...],
                "metrics": {...}
            }
        },
        "insights": {
            "test_insights": {...},
            "agent_insights": {...},
            "dependency_insights": {...},
            "code_quality": {...},
            "optimization_opportunities": [...]
        }
    },
    "metrics": {...},
    "suggestions": [...]
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 