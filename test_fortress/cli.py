#!/usr/bin/env python3
"""
Test Fortress CLI

Command-line interface for running Test Fortress test suites.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .runners.orchestrator_test_runner import run_orchestrator_tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_fortress.cli')

class TestFortressCLI:
    """Command-line interface for Test Fortress."""
    
    def __init__(self):
        """Initialize CLI parser."""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description='Test Fortress - Comprehensive Testing Framework',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            '--subsystem',
            type=str,
            choices=['orchestrator'],
            required=True,
            help='Subsystem to test'
        )
        
        parser.add_argument(
            '--templates',
            type=str,
            help='Path to failure templates JSON file'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Directory to save test results'
        )
        
        parser.add_argument(
            '--log-level',
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Logging level'
        )
        
        parser.add_argument(
            '--fail-fast',
            action='store_true',
            help='Stop on first test failure'
        )
        
        parser.add_argument(
            '--report-format',
            type=str,
            choices=['json', 'text'],
            default='text',
            help='Test report output format'
        )
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run Test Fortress with provided arguments.
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            parsed_args = self.parser.parse_args(args)
            
            # Configure logging
            logging.getLogger().setLevel(parsed_args.log_level)
            
            # Run tests based on subsystem
            if parsed_args.subsystem == 'orchestrator':
                return self._run_orchestrator_tests(parsed_args)
            else:
                logger.error(f"Unknown subsystem: {parsed_args.subsystem}")
                return 1
                
        except Exception as e:
            logger.error(f"Error running Test Fortress: {str(e)}")
            return 1
    
    def _run_orchestrator_tests(self, args: argparse.Namespace) -> int:
        """Run orchestrator tests."""
        try:
            # Import orchestrator here to avoid circular imports
            from dream_os.orchestrator import PromptCycleOrchestrator
            
            # Create orchestrator instance
            orchestrator = PromptCycleOrchestrator()
            
            # Run tests
            summary = run_orchestrator_tests(orchestrator, args.templates)
            
            # Save results if output directory specified
            if args.output:
                self._save_results(summary, args)
            
            # Display results
            self._display_results(summary, args)
            
            # Return exit code based on test results
            return 0 if summary['failed'] == 0 else 1
            
        except Exception as e:
            logger.error(f"Error running orchestrator tests: {str(e)}")
            return 1
    
    def _save_results(self, summary: Dict, args: argparse.Namespace):
        """Save test results to file."""
        try:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if args.report_format == 'json':
                output_file = output_dir / 'test_results.json'
                with open(output_file, 'w') as f:
                    json.dump(summary, f, indent=2)
            else:
                output_file = output_dir / 'test_results.txt'
                with open(output_file, 'w') as f:
                    self._write_text_report(summary, f)
            
            logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
    
    def _display_results(self, summary: Dict, args: argparse.Namespace):
        """Display test results."""
        if args.report_format == 'json':
            print(json.dumps(summary, indent=2))
        else:
            self._write_text_report(summary, sys.stdout)
    
    def _write_text_report(self, summary: Dict, output):
        """Write text format test report."""
        output.write("\n=== Test Fortress Results ===\n\n")
        output.write(f"Total Tests: {summary['total_tests']}\n")
        output.write(f"Passed: {summary['passed']}\n")
        output.write(f"Failed: {summary['failed']}\n")
        output.write(f"Duration: {summary['duration']:.2f}s\n")
        
        if summary['failed'] > 0:
            output.write("\nFailed Tests:\n")
            for result in summary['results']:
                if not result['success']:
                    output.write(f"- {result['name']}: {result.get('error', 'Unknown error')}\n")
                    if 'validation' in result:
                        output.write("  Validation Results:\n")
                        for check, value in result['validation'].items():
                            output.write(f"    {check}: {'PASS' if value else 'FAIL'}\n")
        
        output.write("\n")

def main():
    """CLI entry point."""
    cli = TestFortressCLI()
    sys.exit(cli.run())

if __name__ == '__main__':
    main() 