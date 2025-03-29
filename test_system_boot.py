#!/usr/bin/env python3
"""
Test script to verify the SystemLoader boot process.
This script initializes the Dream.OS core system and reports the status of all services.
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestSystemBoot")

def test_system_boot():
    """Initialize the system and verify all core services."""
    try:
        # Import the SystemLoader
        from core.system_loader import SystemLoader
        
        # Create and boot the system
        logger.info("🚀 Creating SystemLoader...")
        loader = SystemLoader()
        
        logger.info("🚀 Booting Dream.OS core system...")
        services = loader.boot()
        
        # Report service status
        logger.info("🔍 Service initialization results:")
        for name, service in services.items():
            status = "✅ Available" if service else "⚠️ Empty implementation"
            logger.info(f"  - {name}: {status}")
        
        # Check for critical services
        critical_services = [
            "config_manager",
            "path_manager",
            "prompt_manager",
            "prompt_service",
            "openai_client",
            "feedback_engine"
        ]
        
        missing_critical = [svc for svc in critical_services if svc not in services or not services[svc]]
        
        if missing_critical:
            logger.error(f"❌ Missing critical services: {missing_critical}")
            return False
        else:
            logger.info("✅ All critical services are available")
            return True
            
    except Exception as e:
        logger.error(f"❌ System boot failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Starting Dream.OS boot test")
    success = test_system_boot()
    
    if success:
        logger.info("✅ System boot test passed successfully")
        sys.exit(0)
    else:
        logger.error("❌ System boot test failed")
        sys.exit(1) 