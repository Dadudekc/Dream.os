"""Test script to check imports."""

import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from PyQt5.QtWidgets import QApplication
    logger.info("Successfully imported PyQt5")
except ImportError as e:
    logger.error(f"Failed to import PyQt5: {e}")
    sys.exit(1)

try:
    from core.services.service_registry import ServiceRegistry
    logger.info("Successfully imported ServiceRegistry")
except ImportError as e:
    logger.error(f"Failed to import ServiceRegistry: {e}")
    sys.exit(1)

try:
    from core.utils.path_manager import PathManager
    logger.info("Successfully imported PathManager")
except ImportError as e:
    logger.error(f"Failed to import PathManager: {e}")
    sys.exit(1)

try:
    from core.config.config_manager import ConfigManager
    logger.info("Successfully imported ConfigManager")
except ImportError as e:
    logger.error(f"Failed to import ConfigManager: {e}")
    sys.exit(1)

try:
    from core.factories import FactoryRegistry
    logger.info("Successfully imported FactoryRegistry")
except ImportError as e:
    logger.error(f"Failed to import FactoryRegistry: {e}")
    sys.exit(1)

try:
    from core.memory.utils import fix_memory_file
    logger.info("Successfully imported fix_memory_file")
except ImportError as e:
    logger.error(f"Failed to import fix_memory_file: {e}")
    sys.exit(1)

logger.info("All imports successful!") 