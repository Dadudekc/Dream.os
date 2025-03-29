import logging
import argparse
import threading
import sys
import time
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# Bootstrap paths early
from core.bootstrap import get_bootstrap_paths
from core.system_loader import SystemLoader, initialize_system
from core.services.service_registry import ServiceRegistry
from core.PathManager import PathManager
from core.AgentDispatcher import AgentDispatcher
from config.ConfigManager import ConfigManager
from core.DriverManager import DriverManager
from core.logging.factories.LoggerFactory import LoggerFactory
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.factories.feedback_engine_factory import FeedbackEngineFactory

# GUI and Web imports
from interfaces.pyqt.DreamOsMainWindow import DreamscapeMainWindow
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic
from interfaces.pyqt.IntegratedMainWindow import IntegratedMainWindow
from interfaces.pyqt.components.prompt_panel import PromptPanel
from interfaces.pyqt.components.logs_panel import LogsPanel
from interfaces.pyqt.tabs.MainTabs import MainTabs
from interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
from interfaces.pyqt.tabs.LogsTab import LogsTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from web.app import start_flask_app
from core.services.config_service import ConfigService
from core.services.prompt_execution_service import UnifiedPromptService
from utils.signal_dispatcher import SignalDispatcher
from core.services.fix_service import FixService
from core.services.debug_service import DebugService
from core.services.rollback_service import RollbackService

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Dream.OS Command Line Interface')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--web', action='store_true', help='Start web interface')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--port', type=int, default=5000, help='Web server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--agent', action='store_true', help='Run in agent mode')
    return parser.parse_args()

def start_web_server(port, services):
    """Start the web server in a separate thread."""
    try:
        web_thread = threading.Thread(
            target=start_flask_app,
            args=(port, services),
            daemon=True
        )
        web_thread.start()
        logging.info(f"Web server started on port {port}")
        return web_thread
    except Exception as e:
        logging.error(f"Failed to start web server: {e}")
        return None

def start_agent(services):
    """Start the agent dispatcher in a separate thread."""
    try:
        agent_thread = threading.Thread(
            target=run_agent_dispatcher,
            args=(services,),
            daemon=True
        )
        agent_thread.start()
        logging.info("Agent dispatcher started")
        return agent_thread
    except Exception as e:
        logging.error(f"Failed to start agent dispatcher: {e}")
        return None

def run_agent_dispatcher(services):
    """Run the agent dispatcher."""
    try:
        agent_dispatcher = AgentDispatcher(services)
        agent_dispatcher.start()
    except Exception as e:
        logging.error(f"Agent dispatcher error: {e}")

def show_error_message(message):
    """Show an error message box."""
    app = QApplication.instance() or QApplication(sys.argv)
    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle("Dream.OS Error")
    error_box.setText(message)
    error_box.setStandardButtons(QMessageBox.Ok)
    return error_box.exec_()

def main():
    """Main entry point for the application."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("🚀 Starting Dream.OS application")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize core system with proper dependency injection
    try:
        system_loader = SystemLoader(args.config)
        services = system_loader.boot()
        logger.info("✅ Core system initialized successfully with SystemLoader")
    except Exception as e:
        logger.critical(f"❌ Failed to initialize core system: {e}")
        show_error_message(f"Failed to initialize system: {e}")
        return 1
    
    # Get essential services
    config_manager = ServiceRegistry.get("config_manager")
    openai_client = ServiceRegistry.get("openai_client")
    prompt_service = ServiceRegistry.get("prompt_service")
    
    # Start web server if requested
    if args.web:
        web_thread = start_web_server(args.port, services)
        if not web_thread:
            logger.warning("⚠️ Web server failed to start")
    
    # Start agent if requested
    if args.headless or args.agent:
        agent_thread = start_agent(services)
        if not agent_thread:
            logger.warning("⚠️ Agent failed to start")
        
        # If running in headless mode, just keep the main thread alive
        if args.headless:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                return 0
    
    # Start GUI if not in headless mode
    if not args.headless:
        try:
            # Create QApplication
            app = QApplication(sys.argv)
            
            # Create and configure event loop
            from utils.qasync_event_loop_manager import QAsyncEventLoopManager
            event_loop_manager = QAsyncEventLoopManager(app, logger=logging.getLogger("QAsyncEventLoop"))
            logger.info("✅ Async event loop initialized")
            
            # Create signal dispatcher
            dispatcher = SignalDispatcher()
            
            # Create UI logic
            ui_logic = DreamscapeUILogic()
            ui_logic.service = services.get("dreamscape_service")
            logger.info("✅ UI logic initialized")
            
            # Create and show main window
            window = DreamscapeMainWindow(
                ui_logic=ui_logic,
                dispatcher=dispatcher,
                services=services,
                event_loop_manager=event_loop_manager
            )
            window.show()
            window.raise_()
            window.activateWindow()
            logger.info("✅ Main window initialized and displayed")
            
            # Start event loop
            event_loop_manager.start()
            logger.info("✅ Application event loop started")
            
            # Run main application loop
            return app.exec_()
            
        except Exception as e:
            logger.critical(f"❌ Failed to start GUI: {e}")
            show_error_message(f"Failed to start GUI: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())