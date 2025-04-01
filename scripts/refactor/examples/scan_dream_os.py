"""
Example script demonstrating how to use the Dream.OS Intelligence Scanner.

This script shows how to:
1. Initialize and run the scanner
2. Focus on specific aspects of the analysis
3. Process and display the results
4. Generate targeted improvement suggestions
"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scanner import IntelligenceScanner

def analyze_dream_os():
    """Run intelligence scan on Dream.OS codebase."""
    # Initialize rich console for pretty output
    console = Console()
    
    # Get Dream.OS project root (adjust path as needed)
    project_root = Path(__file__).parent.parent.parent.parent
    
    console.print(Panel.fit(
        "[bold blue]Dream.OS Intelligence Scanner Demo[/bold blue]\n"
        f"Analyzing project at: {project_root}"
    ))
    
    # Initialize scanner
    scanner = IntelligenceScanner(project_root)
    
    # Run full analysis
    with console.status("[bold green]Running analysis...[/bold green]"):
        report = scanner.scan_project()
    
    # Display summary statistics
    display_summary(console, scanner)
    
    # Show focused analysis for each aspect
    display_test_analysis(console, report)
    display_agent_analysis(console, report)
    display_dependency_analysis(console, report)
    display_quality_analysis(console, report)
    
    # Save full report
    output_path = project_root / "scanner_report.json"
    with output_path.open('w') as f:
        json.dump(report, f, indent=2)
    
    console.print(f"\nFull analysis report saved to: {output_path}")

def display_summary(console: Console, scanner: IntelligenceScanner):
    """Display summary statistics in a table."""
    stats = scanner.get_summary_stats()
    
    table = Table(title="Project Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Files", str(stats['total_files']))
    table.add_row("Total Classes", str(stats['total_classes']))
    table.add_row("Total Functions", str(stats['total_functions']))
    table.add_row("Test Coverage", f"{stats['test_coverage']:.1%}")
    table.add_row("Average Complexity", f"{stats['average_complexity']:.2f}")
    
    console.print("\n", table)

def display_test_analysis(console: Console, report: dict):
    """Display test coverage analysis."""
    insights = report["analysis_results"]["insights"]
    test_insights = insights["test_insights"]
    
    table = Table(title="Test Coverage Analysis")
    table.add_column("File", style="blue")
    table.add_column("Status", style="red")
    
    for item in test_insights["missing_tests"][:5]:
        table.add_row(item["file"], "Missing Tests")
    
    console.print("\n", table)

def display_agent_analysis(console: Console, report: dict):
    """Display agent analysis results."""
    insights = report["analysis_results"]["insights"]
    agent_insights = insights["agent_insights"]
    
    table = Table(title="Agent Analysis")
    table.add_column("Agent", style="blue")
    table.add_column("Type", style="cyan")
    table.add_column("Maturity", style="green")
    table.add_column("Suggestion", style="yellow")
    
    for item in agent_insights["suggestions"][:5]:
        table.add_row(
            item["agent"],
            item.get("type", "unknown"),
            item.get("maturity", "unknown"),
            item["message"]
        )
    
    console.print("\n", table)

def display_dependency_analysis(console: Console, report: dict):
    """Display dependency analysis results."""
    insights = report["analysis_results"]["insights"]
    dep_insights = insights["dependency_insights"]
    
    table = Table(title="Dependency Analysis")
    table.add_column("Source", style="blue")
    table.add_column("Target", style="blue")
    table.add_column("Risk", style="red")
    
    for item in dep_insights["high_risk_imports"][:5]:
        table.add_row(
            item["source"],
            item["target"],
            item.get("risk_level", "high")
        )
    
    console.print("\n", table)

def display_quality_analysis(console: Console, report: dict):
    """Display code quality analysis results."""
    insights = report["analysis_results"]["insights"]
    quality = insights["code_quality"]
    
    table = Table(title="Code Quality Issues")
    table.add_column("File", style="blue")
    table.add_column("Issue", style="yellow")
    table.add_column("Priority", style="red")
    
    for item in quality["quality_issues"][:5]:
        table.add_row(
            item["file"],
            item["message"],
            item.get("priority", "medium")
        )
    
    console.print("\n", table)

if __name__ == "__main__":
    analyze_dream_os() 