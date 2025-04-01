"""
Command-line interface for Dream.OS Intelligence Scanner.

Provides a user-friendly interface to run the scanner and view results.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from .core.scanner import IntelligenceScanner

def setup_logging(verbose: bool):
    """Configure logging based on verbosity level."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Dream.OS Intelligence Scanner - Analyze and optimize your codebase"
    )
    
    parser.add_argument(
        "project_root",
        type=Path,
        help="Root directory of the project to analyze"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("scanner_report.json"),
        help="Path to save the analysis report (default: scanner_report.json)"
    )
    
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Disable incremental scanning (analyze all files)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging output"
    )
    
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show summary statistics without saving full report"
    )
    
    parser.add_argument(
        "--focus",
        choices=["tests", "agents", "dependencies", "quality"],
        help="Focus analysis on a specific aspect"
    )
    
    return parser.parse_args()

def display_summary(scanner: IntelligenceScanner):
    """Display summary statistics of the analysis."""
    stats = scanner.get_summary_stats()
    
    print("\nDream.OS Intelligence Scan Summary")
    print("=" * 40)
    print(f"Total Files Analyzed: {stats['total_files']}")
    print(f"Total Classes: {stats['total_classes']}")
    print(f"Total Functions: {stats['total_functions']}")
    print(f"Test Coverage: {stats['test_coverage']:.1%}")
    print(f"Average Complexity: {stats['average_complexity']:.2f}")
    print("=" * 40)

def display_focused_results(scanner: IntelligenceScanner, focus: str,
                          report: Optional[dict] = None):
    """Display focused analysis results based on user selection."""
    if report is None:
        report = scanner.scan_project()
    
    insights = report["analysis_results"]["insights"]
    
    print(f"\nFocused Analysis: {focus.upper()}")
    print("=" * 40)
    
    if focus == "tests":
        coverage = insights["test_insights"]["coverage_summary"]
        missing = insights["test_insights"]["missing_tests"]
        
        print(f"Overall Test Coverage: {coverage.get('coverage_score', 0):.1%}")
        print(f"Files Missing Tests: {len(missing)}")
        
        if missing:
            print("\nTop Files Needing Tests:")
            for item in missing[:5]:
                print(f"- {item['file']}")
                
    elif focus == "agents":
        metrics = insights["agent_insights"]["metrics"]
        suggestions = insights["agent_insights"]["suggestions"]
        
        print(f"Total Agents: {metrics['total_agents']}")
        print("\nAgent Types:")
        for agent_type, count in metrics["by_type"].items():
            print(f"- {agent_type}: {count}")
            
        if suggestions:
            print("\nTop Agent Improvements:")
            for item in suggestions[:5]:
                print(f"- {item['agent']}: {item['message']}")
                
    elif focus == "dependencies":
        high_risk = insights["dependency_insights"]["high_risk_imports"]
        suggestions = insights["dependency_insights"]["refactor_suggestions"]
        
        if high_risk:
            print("High Risk Dependencies:")
            for item in high_risk[:5]:
                print(f"- {item['source']} -> {item['target']}")
                
        if suggestions:
            print("\nRefactoring Suggestions:")
            for item in suggestions[:5]:
                print(f"- {item['message']}")
                
    elif focus == "quality":
        quality = insights["code_quality"]
        issues = quality["quality_issues"]
        
        print(f"Average Code Complexity: {quality['average_complexity']:.2f}")
        print(f"Average Documentation: {quality['average_documentation']:.1%}")
        
        if issues:
            print("\nTop Quality Issues:")
            for item in issues[:5]:
                print(f"- {item['file']}: {item['message']}")

def main():
    """Main entry point for the scanner CLI."""
    args = parse_args()
    setup_logging(args.verbose)
    
    # Validate project root
    if not args.project_root.is_dir():
        print(f"Error: {args.project_root} is not a valid directory")
        return 1
    
    try:
        # Initialize and run scanner
        scanner = IntelligenceScanner(args.project_root)
        
        if args.summary_only:
            # Quick scan for summary stats
            scanner._perform_ast_analysis(not args.no_incremental)
            display_summary(scanner)
            return 0
        
        # Full analysis
        report = scanner.scan_project(not args.no_incremental)
        
        # Display focused results if requested
        if args.focus:
            display_focused_results(scanner, args.focus, report)
        else:
            # Display summary and save full report
            display_summary(scanner)
            
            # Save report
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('w') as f:
                json.dump(report, f, indent=2)
            print(f"\nFull analysis report saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error during analysis: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main()) 