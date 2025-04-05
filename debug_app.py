#!/usr/bin/env python3
"""
Debug App - Run and debug the metrics dashboard and auto-queue system.

This script provides a simplified way to run the dashboard and auto-queue system
with detailed logging for debugging purposes.
"""

import os
import sys
import logging
import argparse
import tempfile
import json
import threading
import time
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/debug.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DebugApp")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        import plotly
        import pandas
        logger.info("All required dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print(f"Error: Missing dependency: {e}")
        print("Please install required dependencies with: pip install flask plotly pandas")
        return False

def check_directories():
    """Check if required directories exist and create them if needed."""
    for dir_name in ["logs", "memory", "config", "metrics_dashboard_static"]:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            logger.info(f"Creating directory: {dir_name}")
            dir_path.mkdir(exist_ok=True)
    
    logger.info("All required directories exist")
    return True

def check_config_files():
    """Check if config files exist, create them if needed."""
    # Check for system config
    system_config_path = Path("config/system_config.yml")
    if not system_config_path.exists():
        logger.warning("System config file not found, creating a default one")
        print("Creating default system configuration file...")
        
        # Create basic system config
        with open(system_config_path, 'w') as f:
            f.write("""# System Configuration for StatefulCursorManager

# Service registry settings
services:
  stateful_cursor_manager:
    class: core.StatefulCursorManager.StatefulCursorManager
    params:
      state_file_path: memory/cursor_state.json
    register_as: stateful_cursor_manager

# Directory paths
paths:
  metrics_dir: memory/metrics
  logs_dir: logs
  state_dir: memory

# Logging configuration
logging:
  level: DEBUG
  file: logs/system.log
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Default values
defaults:
  metrics_snapshot_frequency: 6  # hours
  auto_save_frequency: 300  # seconds
  max_session_lifetime: 3600  # seconds
""")
    
    # Check for state file
    state_file_path = Path("memory/cursor_state.json")
    if not state_file_path.exists():
        logger.warning("Cursor state file not found, creating a sample one")
        print("Creating sample cursor state file...")
        
        # Create a basic state file with minimal content
        with open(state_file_path, 'w') as f:
            json.dump({
                "last_session_time": "2025-04-04T12:00:00.000000",
                "session_count": 1,
                "improvement_history": [],
                "context": {},
                "metrics_history": [{
                    "timestamp": "2025-04-04T12:00:00.000000",
                    "metrics": {
                        "core/StatefulCursorManager.py": {
                            "complexity": 25,
                            "coverage_percentage": 60,
                            "maintainability_index": 70,
                            "lines_of_code": 400
                        },
                        "metrics_dashboard.py": {
                            "complexity": 18,
                            "coverage_percentage": 65,
                            "maintainability_index": 75,
                            "lines_of_code": 350
                        }
                    }
                }],
                "module_stats": {},
                "active_improvements": {}
            }, f, indent=2)
    
    # Check for CSS file
    css_file_path = Path("metrics_dashboard_static/dashboard.css")
    if not css_file_path.exists():
        logger.warning("Dashboard CSS file not found, creating a default one")
        
        # Ensure directory exists
        css_file_path.parent.mkdir(exist_ok=True)
        
        # Create default CSS
        with open(css_file_path, 'w') as f:
            f.write("""
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background-color: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); padding: 20px; margin-bottom: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .chart-container { height: 300px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            tr:hover { background-color: #f5f5f5; }
            .progress-bar { height: 10px; background-color: #e0e0e0; border-radius: 5px; overflow: hidden; }
            .progress-value { height: 100%; background-color: #4CAF50; }
            """)
    
    logger.info("All required config files exist")
    return True

def run_metrics_dashboard(port=5050, debug_mode=True):
    """Run the metrics dashboard with detailed logging."""
    try:
        # Run the dashboard without directly importing it
        logger.info(f"Starting metrics dashboard on port {port}")
        print(f"Starting dashboard on port {port}...")
        
        # Create a simplified test dashboard
        from flask import Flask, jsonify, render_template_string
        
        # Create a test app
        test_app = Flask(__name__)
        
        # Load metrics data
        state_file_path = Path("memory/cursor_state.json")
        
        if state_file_path.exists():
            with open(state_file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            state_data = {}
            
        @test_app.route('/')
        def index():
            """Display a simple metrics dashboard."""
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Code Metrics Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background-color: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); padding: 20px; margin-bottom: 20px; }
                    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
                    pre { background: #f8f8f8; padding: 10px; border-radius: 4px; overflow: auto; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Code Metrics Dashboard (Simplified Debug Version)</h1>
                    
                    <div class="card">
                        <h2>System Information</h2>
                        <p>This is a simplified version of the metrics dashboard for debugging purposes.</p>
                        <p>The actual dashboard implementation can be found in <code>metrics_dashboard.py</code>.</p>
                    </div>
                    
                    <div class="card">
                        <h2>State Data</h2>
                        <pre>{{ state_data }}</pre>
                    </div>
                </div>
            </body>
            </html>
            """
            return render_template_string(html, state_data=json.dumps(state_data, indent=2))
            
        @test_app.route('/api/dashboard-summary')
        def summary():
            """Get dashboard summary data."""
            return jsonify({
                "status": "ok",
                "message": "This is a simplified test API for debugging",
                "data": {
                    "session_count": state_data.get("session_count", 0),
                    "improvement_count": len(state_data.get("improvement_history", [])),
                    "metrics_snapshots": len(state_data.get("metrics_history", [])),
                    "last_updated": state_data.get("last_session_time", "")
                }
            })
        
        # Run the app
        test_app.run(host='0.0.0.0', port=port, debug=debug_mode)
        
    except Exception as e:
        logger.error(f"Error running metrics dashboard: {e}")
        traceback.print_exc()
        print(f"Error running dashboard: {e}")
        return False
    
    return True

def run_auto_queue(count=3, dry_run=True, delay=0):
    """Run auto-queue with detailed logging."""
    try:
        # Import auto queue module
        from auto_queue_improvements import AutoImprovementQueue
        
        logger.info(f"Initializing auto-queue for top {count} modules")
        print(f"Identifying top {count} modules for improvement...")
        
        # Create auto improvement queue
        auto_queue = AutoImprovementQueue(config_path="config/system_config.yml")
        
        if dry_run:
            # Just show the modules that would be queued
            logger.info("DRY RUN: Showing modules that would be queued without actually queueing them")
            top_modules = auto_queue.get_top_modules(count)
            
            print("\nTop Modules for Improvement (Dry Run):")
            print("=====================================")
            for i, candidate in enumerate(top_modules):
                module = candidate["module"]
                score = candidate.get("score", "N/A")
                days = candidate.get("days_since_improvement", "N/A")
                
                print(f"{i+1}. {module}")
                print(f"   Score: {score}")
                print(f"   Days since improvement: {days}")
                print()
                
            print(f"Found {len(top_modules)} candidate modules")
            print("Dry run completed, no modules were queued.")
            
        else:
            # Actually queue the improvements
            logger.info(f"Queueing {count} modules with {delay}s delay between each")
            
            session_ids = auto_queue.auto_queue_improvements(
                count=count,
                delay_between=delay
            )
            
            print(f"\nSuccessfully queued {len(session_ids)}/{count} modules for improvement.")
            print("Check the logs for more details: logs/auto_queue.log")
        
    except Exception as e:
        logger.error(f"Error running auto-queue: {e}")
        traceback.print_exc()
        print(f"Error running auto-queue: {e}")
        return False
    
    return True

def run_integration(dashboard=True, port=5050, auto_queue=False, count=3, 
                   dry_run=True, delay=0, apply_weights=False):
    """Run the integration script with detailed logging."""
    try:
        # Import integration module
        from metrics_dashboard_integration import run_integration
        import argparse
        
        logger.info("Starting integration script")
        print("Running integration script with detailed logging...")
        
        # Create args namespace
        args = argparse.Namespace(
            dashboard=dashboard,
            port=port,
            state_file='memory/cursor_state.json',
            config='config/system_config.yml',
            update_weights=None,
            apply_weights_to_cursor=apply_weights,
            max_candidates=count,
            auto_queue=auto_queue,
            auto_queue_count=count,
            auto_queue_delay=delay,
            auto_queue_dry_run=dry_run
        )
        
        # Run integration
        run_integration(args)
        
    except Exception as e:
        logger.error(f"Error running integration script: {e}")
        traceback.print_exc()
        print(f"Error running integration: {e}")
        return False
    
    return True

def main():
    """Main entry point for the debug app."""
    parser = argparse.ArgumentParser(description='Debug the metrics dashboard and auto-queue system')
    
    parser.add_argument('--dashboard', action='store_true',
                    help='Run the metrics dashboard')
    parser.add_argument('--port', type=int, default=5050,
                    help='Port for the dashboard (default: 5050)')
    parser.add_argument('--auto-queue', action='store_true',
                    help='Run auto-queue improvements')
    parser.add_argument('--count', type=int, default=3,
                    help='Number of modules to queue (default: 3)')
    parser.add_argument('--delay', type=int, default=0,
                    help='Delay between queuing modules in seconds (default: 0)')
    parser.add_argument('--dry-run', action='store_true',
                    help='Show modules that would be queued without actually queueing them')
    parser.add_argument('--integration', action='store_true',
                    help='Run the integration script')
    parser.add_argument('--apply-weights', action='store_true',
                    help='Apply priority weights to cursor manager')
    
    args = parser.parse_args()
    
    # If no specific component was selected, run the dashboard by default
    if not (args.dashboard or args.auto_queue or args.integration):
        args.dashboard = True
    
    # Check dependencies and directories
    if not check_dependencies():
        return 1
    
    if not check_directories():
        return 1
    
    if not check_config_files():
        return 1
    
    # Run selected components
    try:
        if args.integration:
            # Run integration script
            success = run_integration(
                dashboard=args.dashboard,
                port=args.port,
                auto_queue=args.auto_queue,
                count=args.count,
                dry_run=args.dry_run,
                delay=args.delay,
                apply_weights=args.apply_weights
            )
            
            if not success:
                return 1
                
        else:
            # Run components separately
            if args.dashboard:
                # Run in a separate thread to allow other components to run
                dashboard_thread = threading.Thread(
                    target=run_metrics_dashboard,
                    args=(args.port, True)
                )
                dashboard_thread.daemon = True
                dashboard_thread.start()
                
                # Give the dashboard time to start
                time.sleep(2)
            
            if args.auto_queue:
                # Run auto-queue
                success = run_auto_queue(
                    count=args.count,
                    dry_run=args.dry_run,
                    delay=args.delay
                )
                
                if not success:
                    return 1
            
            # If dashboard is running, keep main thread alive
            if args.dashboard:
                print("\nPress Ctrl+C to exit...")
                try:
                    while dashboard_thread.is_alive():
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nExiting debug app...")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in debug app: {e}")
        traceback.print_exc()
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 