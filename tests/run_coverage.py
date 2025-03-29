#!/usr/bin/env python
"""
Test coverage runner for ChatMate.

This script runs the test suite with coverage and generates a report.
"""
import os
import sys
import argparse
import subprocess
import webbrowser
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run tests with coverage reporting')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--open', action='store_true', help='Open HTML report in browser')
    parser.add_argument('--module', type=str, help='Run tests for specific module (e.g., "gui", "core")')
    parser.add_argument('--file', type=str, help='Run tests for specific file')
    parser.add_argument('--min-coverage', type=int, default=80, help='Minimum coverage percentage (default: 80)')
    return parser.parse_args()

def run_coverage(args):
    """Run pytest with coverage and generate report."""
    # Determine the pytest path
    base_dir = Path(__file__).parent.parent
    report_dir = base_dir / 'reports' / 'coverage'
    os.makedirs(report_dir, exist_ok=True)
    
    # Build the command
    cmd = ['pytest']
    
    # Add coverage options
    cmd.extend(['--cov=chat_mate'])
    
    # Add module or file if specified
    if args.module:
        if args.module == 'gui':
            cmd.append('tests/gui/')
        elif args.module == 'core':
            cmd.append('tests/unit/core/')
        elif args.module == 'services':
            cmd.append('tests/unit/services/')
        elif args.module == 'integration':
            cmd.append('tests/integration/')
        else:
            cmd.append(f'tests/{args.module}/')
    elif args.file:
        cmd.append(args.file)
    
    # Run the tests with coverage
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(base_dir))
    
    if result.returncode != 0:
        print(f"Tests failed with exit code {result.returncode}")
        return result.returncode
    
    # Generate HTML report if requested
    if args.html:
        html_cmd = ['coverage', 'html', '-d', str(report_dir)]
        subprocess.run(html_cmd, cwd=str(base_dir))
        
        print(f"HTML coverage report generated in {report_dir}")
        
        # Open the report in the browser if requested
        if args.open:
            index_path = report_dir / 'index.html'
            if index_path.exists():
                webbrowser.open(f'file://{index_path.absolute()}')
            else:
                print(f"Could not find HTML report at {index_path}")
    
    # Check coverage against minimum
    coverage_cmd = ['coverage', 'report', '--fail-under', str(args.min_coverage)]
    coverage_result = subprocess.run(coverage_cmd, cwd=str(base_dir))
    
    return coverage_result.returncode

def main():
    """Main entry point."""
    args = parse_args()
    sys.exit(run_coverage(args))

if __name__ == '__main__':
    main() 