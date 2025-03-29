#!/usr/bin/env python3
"""
Dream.OS Runner Script
======================

A simple runner script that starts the Dream.OS system with various options.
This is a lightweight wrapper around the main.py script.
"""

import sys
import logging
import argparse
import subprocess

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("Dream.OS Runner")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Runner")
    parser.add_argument("--test", action="store_true", help="Run system boot test only")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--web", action="store_true", help="Start web interface")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument("--agent", action="store_true", help="Run agent mode")
    parser.add_argument("--config", type=str, help="Path to config file")
    return parser.parse_args()

def run_test_mode():
    """Run the system boot test."""
    logger.info("🧪 Running system boot test...")
    try:
        result = subprocess.run([sys.executable, "test_system_boot.py"], 
                               check=True, 
                               capture_output=True, 
                               text=True)
        logger.info(result.stdout)
        logger.info("✅ System boot test completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ System boot test failed: {e}")
        logger.error(e.stdout)
        logger.error(e.stderr)
        return False

def run_main_app(args):
    """Run the main application with the specified arguments."""
    cmd = [sys.executable, "main.py"]
    
    if args.headless:
        cmd.append("--headless")
    if args.web:
        cmd.append("--web")
    if args.port != 5000:
        cmd.extend(["--port", str(args.port)])
    if args.agent:
        cmd.append("--agent")
    if args.config:
        cmd.extend(["--config", args.config])
    
    logger.info(f"🚀 Starting Dream.OS with command: {' '.join(cmd)}")
    
    try:
        # Run the command and forward all output to the console
        process = subprocess.Popen(cmd)
        return_code = process.wait()
        
        if return_code != 0:
            logger.error(f"❌ Dream.OS exited with code {return_code}")
            return False
        
        logger.info("✅ Dream.OS exited successfully")
        return True
    except KeyboardInterrupt:
        logger.info("⏱️ Interrupted by user")
        return True
    except Exception as e:
        logger.error(f"❌ Error running Dream.OS: {e}")
        return False

if __name__ == "__main__":
    logger = setup_logging()
    args = parse_args()
    
    logger.info("🌟 Dream.OS Runner starting")
    
    if args.test:
        success = run_test_mode()
    else:
        success = run_main_app(args)
    
    sys.exit(0 if success else 1) 