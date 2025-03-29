#!/usr/bin/env python3
"""
analyze_test_coverage.py

Analyzes test coverage for the chat_mate project and identifies gaps in coverage.
Provides detailed reports on modules and files that need additional tests.

Usage:
    python analyze_test_coverage.py [--html] [--threshold=70]
"""

import subprocess
import json
import sys
import argparse
import os
from pathlib import Path
from tabulate import tabulate
import matplotlib.pyplot as plt
import time

# Configuration
PROJECT_ROOT = Path(".").resolve()
COVERAGE_DIR = PROJECT_ROOT / "reports" / "coverage"
DEFAULT_THRESHOLD = 70

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze test coverage and identify gaps')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--threshold', type=int, default=DEFAULT_THRESHOLD, 
                        help=f'Coverage threshold percentage (default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--visualize', action='store_true', help='Generate coverage visualization')
    parser.add_argument('--mock-data', action='store_true', help='Use mock data if coverage analysis fails')
    return parser.parse_args()

def run_coverage_analysis():
    """Run pytest with coverage and generate JSON report."""
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run pytest with coverage
        cmd = [
            "pytest", 
            "--cov=chat_mate", 
            "--cov-report", f"html:{COVERAGE_DIR}",
            "--cov-report", "term",
            "tests/"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        
        if "ImportError" in proc.stderr or "ModuleNotFoundError" in proc.stderr:
            print("Warning: Import errors detected in tests. Coverage may be incomplete.")
            print(proc.stderr)
        
        # Generate JSON report
        cov_cmd = ["coverage", "json", "-o", str(COVERAGE_DIR / "coverage.json")]
        subprocess.run(cov_cmd, cwd=str(PROJECT_ROOT))
        
        return COVERAGE_DIR / "coverage.json"
    except Exception as e:
        print(f"Error running coverage analysis: {e}")
        return None

def find_python_files():
    """Find all Python modules in the codebase."""
    modules = []
    exclude_dirs = {"venv", "__pycache__", ".git", ".pytest_cache", ".cursor"}
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                
                # Skip files in tests directory
                if rel_path.startswith('tests'):
                    continue
                
                modules.append(rel_path)
                
    return modules

def generate_mock_coverage_data(threshold):
    """Generate mock coverage data for analysis when actual coverage fails."""
    python_files = find_python_files()
    
    mock_data = {
        "meta": {
            "version": "7.0.0",
            "timestamp": time.time(),
            "branch_coverage": False,
            "show_contexts": False
        },
        "files": {},
        "totals": {
            "covered_lines": 0,
            "num_statements": 0,
            "percent_covered": 0.0,
            "missing_lines": 0,
            "excluded_lines": 0
        }
    }
    
    # Generate random coverage data for each file
    import random
    total_statements = 0
    total_covered = 0
    
    for file_path in python_files:
        # Read the file to count lines
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            # Count non-empty lines
            code_lines = [i+1 for i, line in enumerate(content) if line.strip() and not line.strip().startswith('#')]
            
            if not code_lines:
                continue
                
            num_statements = len(code_lines)
            
            # Generate random coverage between threshold-30 and 100
            min_coverage = max(10, threshold - 30)
            coverage_pct = random.uniform(min_coverage, 100)
            
            # Calculate covered and missing lines
            num_covered = int(num_statements * (coverage_pct / 100))
            covered_lines = random.sample(code_lines, min(num_covered, len(code_lines)))
            missing_lines = [line for line in code_lines if line not in covered_lines]
            
            mock_data["files"][file_path] = {
                "executed_lines": covered_lines,
                "summary": {
                    "covered_lines": num_covered,
                    "num_statements": num_statements,
                    "percent_covered": coverage_pct,
                    "missing_lines": len(missing_lines)
                },
                "missing_lines": missing_lines,
                "excluded_lines": []
            }
            
            total_statements += num_statements
            total_covered += num_covered
            
        except Exception:
            # Skip files that can't be read
            continue
    
    # Update totals
    if total_statements > 0:
        mock_data["totals"]["covered_lines"] = total_covered
        mock_data["totals"]["num_statements"] = total_statements
        mock_data["totals"]["percent_covered"] = (total_covered / total_statements) * 100
        mock_data["totals"]["missing_lines"] = total_statements - total_covered
    
    # Save the mock data
    mock_file = COVERAGE_DIR / "coverage.json"
    with open(mock_file, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, indent=2)
    
    print("Generated mock coverage data for analysis.")
    return mock_file

def analyze_coverage_data(json_file, threshold):
    """Analyze coverage data from JSON file."""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        total_coverage = data.get("totals", {}).get("percent_covered", 0)
        
        # Group files by module
        modules = {}
        below_threshold = []
        
        for file_path, file_data in data.get("files", {}).items():
            # Skip test files
            if "/tests/" in file_path or file_path.endswith("test.py") or file_path.startswith("test_"):
                continue
            
            # Determine module (first directory after chat_mate)
            parts = file_path.split(os.sep)
            try:
                if "chat_mate" in parts:
                    idx = parts.index("chat_mate")
                    if idx + 1 < len(parts):
                        module = parts[idx + 1]
                    else:
                        module = "root"
                else:
                    module = parts[0] if parts else "unknown"
            except (ValueError, IndexError):
                module = "unknown"
            
            if module not in modules:
                modules[module] = {"files": [], "total_statements": 0, "covered_statements": 0}
            
            covered = file_data.get("summary", {}).get("covered_lines", 0)
            total = file_data.get("summary", {}).get("num_statements", 0)
            percent = file_data.get("summary", {}).get("percent_covered", 0)
            missing_lines = file_data.get("missing_lines", [])
            
            file_info = {
                "path": file_path,
                "covered_lines": covered,
                "total_statements": total,
                "percent_covered": percent,
                "missing_lines": missing_lines
            }
            
            modules[module]["files"].append(file_info)
            modules[module]["total_statements"] += total
            modules[module]["covered_statements"] += covered
            
            if percent < threshold:
                below_threshold.append(file_info)
        
        # Calculate module percentages
        for module in modules:
            if modules[module]["total_statements"] > 0:
                modules[module]["percent_covered"] = (
                    modules[module]["covered_statements"] / modules[module]["total_statements"] * 100
                )
            else:
                modules[module]["percent_covered"] = 0
        
        return {
            "total_coverage": total_coverage,
            "modules": modules,
            "below_threshold": below_threshold
        }
    except Exception as e:
        print(f"Error analyzing coverage data: {e}")
        return {
            "total_coverage": 0,
            "modules": {},
            "below_threshold": []
        }

def print_coverage_report(analysis, threshold):
    """Print a formatted coverage report."""
    print("\n=== COVERAGE SUMMARY ===")
    print(f"Total Coverage: {analysis['total_coverage']:.2f}%")
    print(f"Threshold: {threshold}%")
    
    # Module summary
    module_data = []
    for name, data in analysis["modules"].items():
        module_data.append([
            name,
            f"{data['percent_covered']:.2f}%",
            data["covered_statements"],
            data["total_statements"],
            len(data["files"])
        ])
    
    if module_data:
        print("\n=== MODULE COVERAGE ===")
        print(tabulate(
            sorted(module_data, key=lambda x: float(x[1].rstrip('%')), reverse=True),
            headers=["Module", "Coverage", "Covered", "Total", "Files"],
            tablefmt="grid"
        ))
    else:
        print("\nNo module coverage data available.")
    
    # Files below threshold
    if analysis["below_threshold"]:
        below_data = []
        for file in sorted(analysis["below_threshold"], key=lambda x: x["percent_covered"]):
            below_data.append([
                file["path"],
                f"{file['percent_covered']:.2f}%",
                file["covered_lines"],
                file["total_statements"],
                len(file["missing_lines"])
            ])
        
        print(f"\n=== FILES BELOW {threshold}% COVERAGE ===")
        print(tabulate(
            below_data,
            headers=["File", "Coverage", "Covered", "Total", "Missing Lines"],
            tablefmt="grid"
        ))
    else:
        print(f"\nAll files meet the {threshold}% coverage threshold!")

def visualize_coverage(analysis):
    """Generate coverage visualization charts."""
    # Create directory for visualizations
    vis_dir = COVERAGE_DIR / "visualizations"
    vis_dir.mkdir(exist_ok=True)
    
    # Module coverage bar chart
    module_names = []
    module_coverages = []
    
    for name, data in sorted(
        analysis["modules"].items(), 
        key=lambda x: x[1]["percent_covered"], 
        reverse=True
    ):
        if data["total_statements"] > 10:  # Only include modules with significant code
            module_names.append(name)
            module_coverages.append(data["percent_covered"])
    
    if module_names:
        plt.figure(figsize=(12, 8))
        bars = plt.barh(module_names, module_coverages, color='skyblue')
        
        # Add coverage percentage labels
        for bar in bars:
            width = bar.get_width()
            plt.text(
                width + 1, 
                bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}%', 
                va='center'
            )
        
        plt.xlabel('Coverage (%)')
        plt.title('Test Coverage by Module')
        plt.axvline(x=DEFAULT_THRESHOLD, color='red', linestyle='--', label=f'Threshold ({DEFAULT_THRESHOLD}%)')
        plt.legend()
        plt.tight_layout()
        plt.savefig(vis_dir / "module_coverage.png")
        
        # Files below threshold pie chart
        if analysis["below_threshold"]:
            # Count files by coverage range
            ranges = {
                "0-25%": 0,
                "25-50%": 0,
                "50-75%": 0,
                "75-100%": 0
            }
            
            for file in analysis["below_threshold"]:
                coverage = file["percent_covered"]
                if coverage < 25:
                    ranges["0-25%"] += 1
                elif coverage < 50:
                    ranges["25-50%"] += 1
                elif coverage < 75:
                    ranges["50-75%"] += 1
                else:
                    ranges["75-100%"] += 1
            
            labels = [f"{k} ({v})" for k, v in ranges.items() if v > 0]
            sizes = [v for v in ranges.values() if v > 0]
            
            if sizes:
                plt.figure(figsize=(10, 8))
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#ffcc99','#ffff99','#ccff99'])
                plt.axis('equal')
                plt.title(f'Distribution of Files Below {DEFAULT_THRESHOLD}% Coverage')
                plt.tight_layout()
                plt.savefig(vis_dir / "coverage_distribution.png")
    
        print(f"\nVisualization saved to {vis_dir}")
    else:
        print("\nNo sufficient data to generate visualizations.")

def main():
    """Main entry point."""
    args = parse_args()
    
    print("Running coverage analysis...")
    json_file = run_coverage_analysis()
    
    if json_file is None or not os.path.exists(json_file):
        if args.mock_data:
            print("Coverage analysis failed. Generating mock data for visualization...")
            json_file = generate_mock_coverage_data(args.threshold)
        else:
            print("Coverage analysis failed and --mock-data not specified. Cannot continue.")
            return 1
    
    print("Analyzing coverage data...")
    analysis = analyze_coverage_data(json_file, args.threshold)
    
    print_coverage_report(analysis, args.threshold)
    
    if args.visualize:
        print("\nGenerating visualizations...")
        visualize_coverage(analysis)
    
    # Return non-zero if coverage is below threshold
    if analysis["total_coverage"] < args.threshold:
        print(f"\nWARNING: Overall coverage ({analysis['total_coverage']:.2f}%) is below threshold ({args.threshold}%)")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 