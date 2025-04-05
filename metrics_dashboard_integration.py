#!/usr/bin/env python3
"""
Metrics Dashboard and Priority Weighting Integration

This script integrates the metrics dashboard and priority weighting system with
the StatefulCursorManager, making it easy to run both components together.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/metrics_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MetricsIntegration")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import integration modules
from priority_weighting_config import PriorityWeightingConfig
import metrics_dashboard

# Try to import auto queue improvements
try:
    from auto_queue_improvements import AutoImprovementQueue
    auto_queue_available = True
except ImportError:
    logger.warning("AutoImprovementQueue not available, auto-queue functionality disabled")
    auto_queue_available = False

# Integration function for the dashboard and weighting system
def run_integration(args):
    """Run the integration of dashboard and weighting system."""
    logger.info("Starting metrics dashboard and priority weighting integration")
    
    # Create necessary directories
    Path("memory").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize priority weighting config
    priority_config = PriorityWeightingConfig()
    
    # Get current weighting values
    current_weights = priority_config.get_all_weights()
    
    logger.info("Current priority weights:")
    for key, value in current_weights.items():
        logger.info(f"  {key}: {value}")
    
    # Update weighting system if needed
    if args.update_weights:
        for weight_str in args.update_weights:
            try:
                key, value = weight_str.split('=')
                priority_config.update_weight(key.strip(), float(value.strip()))
                logger.info(f"Updated weight {key} to {value}")
            except ValueError:
                logger.error(f"Invalid weight format: {weight_str}. Use key=value format.")
    
    # Start dashboard if requested
    dashboard_thread = None
    if args.dashboard:
        logger.info(f"Starting metrics dashboard on port {args.port}")
        
        # Create dashboard process
        import threading
        
        def run_dashboard():
            """Run the dashboard in a separate thread."""
            # Set up the dashboard
            metrics_dashboard.DASHBOARD_PORT = args.port
            metrics_dashboard.STATE_FILE = Path(args.state_file)
            metrics_dashboard.data_provider = metrics_dashboard.MetricsDataProvider(
                state_file_path=metrics_dashboard.STATE_FILE)
            
            # Run the dashboard
            metrics_dashboard.app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)
        
        # Start dashboard thread
        dashboard_thread = threading.Thread(target=run_dashboard)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        logger.info(f"Dashboard started on http://localhost:{args.port}")
        print(f"Dashboard is running at http://localhost:{args.port}")
        
        # If only dashboard was requested, keep running until interrupted
        if not (args.apply_weights_to_cursor or args.auto_queue):
            print("Press Ctrl+C to stop the dashboard")
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Dashboard stopped by user")
                print("Dashboard stopped")
                return
    
    # Apply weighting to cursor manager
    if args.apply_weights_to_cursor:
        try:
            # Import system modules
            from core.system_loader import initialize_system
            
            # Initialize system
            system = initialize_system(args.config)
            
            # Get cursor manager
            cursor_manager = system.get_service("stateful_cursor_manager")
            
            if cursor_manager:
                logger.info("Applying priority weights to StatefulCursorManager")
                
                # Get improvement candidates using priority config
                candidates = []
                metrics_history = cursor_manager.state.get("metrics_history", [])
                
                if metrics_history:
                    # Get most recent metrics
                    latest_metrics = metrics_history[-1].get("metrics", {})
                    
                    # Process each module
                    for module, metrics in latest_metrics.items():
                        # Skip modules currently being improved
                        if module in cursor_manager.get_active_improvements():
                            continue
                        
                        # Get improvement history
                        history = cursor_manager.get_module_history(module)
                        
                        # Calculate days since last improvement
                        days_since_improvement = 1000  # Default if never improved
                        if history:
                            import datetime
                            last_record = max(history, key=lambda x: x.get("timestamp", ""))
                            try:
                                last_date = datetime.datetime.fromisoformat(last_record.get("timestamp", ""))
                                days_since_improvement = (datetime.datetime.now() - last_date).days
                            except (ValueError, TypeError):
                                pass
                        
                        # Add days_since_improvement to metrics
                        metrics["days_since_improvement"] = days_since_improvement
                        
                        # Calculate score using priority weights
                        score = priority_config.calculate_module_score(metrics)
                        
                        candidates.append({
                            "module": module,
                            "score": score,
                            "metrics": metrics
                        })
                
                # Sort candidates by score
                candidates.sort(key=lambda x: x["score"], reverse=True)
                
                # Print top candidates
                logger.info("Top improvement candidates with custom weights:")
                print("\nTop Improvement Candidates:")
                print("===========================")
                
                for i, candidate in enumerate(candidates[:args.max_candidates]):
                    module = candidate["module"]
                    score = candidate["score"]
                    metrics = candidate["metrics"]
                    
                    print(f"{i+1}. {module}")
                    print(f"   Score: {score:.2f}")
                    print(f"   Complexity: {metrics.get('complexity', 'N/A')}")
                    print(f"   Coverage: {metrics.get('coverage_percentage', 'N/A')}%")
                    print(f"   Days since improvement: {metrics.get('days_since_improvement', 'N/A')}")
                    print()
                    
                    logger.info(f"Candidate {i+1}: {module} (Score: {score:.2f})")
            else:
                logger.error("StatefulCursorManager not found in system")
                
        except Exception as e:
            logger.error(f"Error applying weights to cursor manager: {e}")

    # Auto-queue improvements if requested
    if args.auto_queue and auto_queue_available:
        try:
            logger.info(f"Auto-queueing {args.auto_queue_count} modules for improvement")
            print(f"\nAuto-queueing {args.auto_queue_count} modules for improvement:")
            print("="*50)
            
            # Create auto improvement queue
            auto_queue = AutoImprovementQueue(config_path=args.config)
            
            if args.auto_queue_dry_run:
                # Just show the modules that would be queued
                logger.info("DRY RUN: Showing modules that would be queued without actually queueing them")
                top_modules = auto_queue.get_top_modules(args.auto_queue_count)
                
                print("\nTop Modules for Improvement (Dry Run):")
                print("=====================================")
                for i, candidate in enumerate(top_modules):
                    module = candidate["module"]
                    score = candidate.get("score", "N/A")
                    days = candidate.get("days_since_improvement", "N/A")
                    
                    print(f"{i+1}. {module}")
                    print(f"   Score: {score}")
                    print(f"   Days since last improvement: {days}")
                    print()
                    
                print(f"Found {len(top_modules)} candidate modules")
                print("Dry run completed, no modules were queued.")
                
            else:
                # Actually queue the improvements
                session_ids = auto_queue.auto_queue_improvements(
                    count=args.auto_queue_count,
                    delay_between=args.auto_queue_delay
                )
                
                print(f"\nSuccessfully queued {len(session_ids)}/{args.auto_queue_count} modules for improvement.")
                print("Check the logs for more details: logs/auto_queue.log")
                
        except Exception as e:
            logger.error(f"Error in auto-queue improvements: {e}")
            print(f"Error auto-queueing improvements: {e}")
    
    # If dashboard is running and other operations are complete, keep running until interrupted
    if dashboard_thread and (args.apply_weights_to_cursor or args.auto_queue):
        print("\nAll operations completed. Dashboard is still running.")
        print("Press Ctrl+C to stop the dashboard")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Dashboard stopped by user")
            print("Dashboard stopped")


def main():
    """Main entry point for the integration."""
    parser = argparse.ArgumentParser(
        description='Integrate metrics dashboard and priority weighting system')
    
    # Dashboard options
    parser.add_argument('--dashboard', action='store_true',
                    help='Start the metrics dashboard')
    parser.add_argument('--port', type=int, default=5050,
                    help='Port for the dashboard (default: 5050)')
    
    # Shared options
    parser.add_argument('--state-file', type=str, default='memory/cursor_state.json',
                    help='Path to the state file')
    parser.add_argument('--config', type=str, default='config/system_config.yml',
                    help='Path to system configuration')
    
    # Priority weighting options
    parser.add_argument('--update-weights', type=str, nargs='+',
                    help='Update priority weights (format: key=value)')
    parser.add_argument('--apply-weights-to-cursor', action='store_true',
                    help='Apply priority weights to cursor manager')
    parser.add_argument('--max-candidates', type=int, default=5,
                    help='Maximum number of candidates to show')
    
    # Auto-queue options
    parser.add_argument('--auto-queue', action='store_true',
                    help='Auto-queue modules for improvement')
    parser.add_argument('--auto-queue-count', type=int, default=3,
                    help='Number of modules to auto-queue (default: 3)')
    parser.add_argument('--auto-queue-delay', type=int, default=0,
                    help='Delay between queueing modules in seconds (default: 0)')
    parser.add_argument('--auto-queue-dry-run', action='store_true',
                    help='Show modules that would be queued without actually queueing them')
    
    args = parser.parse_args()
    
    try:
        run_integration(args)
        return 0
    except Exception as e:
        logger.error(f"Integration error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 