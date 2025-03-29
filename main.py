import logging
import argparse
import threading
import sys
import time
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# Bootstrap paths early
from core.bootstrap import get_bootstrap_paths
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


def initialize_services():
    """Initialize application services."""
    services = {}
    
    # Boot OpenAIClient if not already booted
    try:
        if not OpenAIClient.is_booted():
            logging.info("OpenAIClient not booted. Booting now...")
            # Create a default client instance with profiles from config if needed
            profile_dir = os.path.join(os.getcwd(), "chrome_profile", "openai")
            client = OpenAIClient(profile_dir=profile_dir, headless=True)
            client.boot()
            services['openai_client'] = client
            logging.info("✅ OpenAIClient booted successfully.")
        else:
            logging.info("✅ OpenAIClient already booted.")
    except Exception as e:
        logging.warning(f"❌ Failed to boot OpenAIClient: {e}")
        
    # Initialize FeedbackEngine as a singleton using factory
    try:
        # Create temporary config to pass to factory
        temp_config = {'memory_file': 'memory/persistent_memory.json', 'feedback_log_file': 'memory/feedback_log.json'}
        
        feedback_engine = FeedbackEngineFactory.create(temp_config, logger_obj=logging.getLogger())
        if feedback_engine:
            services['feedback_engine'] = feedback_engine
            logging.info("✅ FeedbackEngine initialized successfully.")
        else:
            logging.warning("⚠️ FeedbackEngine factory returned None.")
    except Exception as e:
        logging.warning(f"❌ Failed to initialize FeedbackEngine: {e}")

    # Initialize config service
    config_service = ConfigService()
    services['config'] = config_service

    # Initialize prompt service
    prompt_service = UnifiedPromptService(config_service)
    services['prompt'] = prompt_service

    # Initialize fix service
    fix_service = FixService(config_service)
    services['fix_service'] = fix_service

    # Initialize debug service
    debug_service = DebugService(config_service)
    services['debug_service'] = debug_service

    # Initialize rollback service
    rollback_service = RollbackService(config_service)
    services['rollback_service'] = rollback_service

    # Try to initialize CursorSessionManager (for debugging)
    try:
        from core.refactor.CursorSessionManager import CursorSessionManager
        cursor_manager = CursorSessionManager(config_service, {})  # Empty dict as memory_manager placeholder
        services['cursor_manager'] = cursor_manager
        logging.info("CursorSessionManager initialized successfully.")
    except Exception as e:
        logging.warning(f"Failed to initialize CursorSessionManager: {e}")
        services['cursor_manager'] = None

    return services


def show_error_dialog(errors):
    """Display an error dialog if services fail to initialize."""
    app = QApplication.instance() or QApplication([])
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Initialization Errors")
    msg.setText("Some services encountered failures:")
    msg.setDetailedText("\n".join(errors))
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    return msg.exec_() == QMessageBox.Ok


def run_agent_dispatcher(services):
    """Start the agent dispatcher in a loop."""
    dispatcher = AgentDispatcher(config=services["config"])
    dispatcher._start_workers()

    try:
        logging.info("Agent Dispatcher started.")
        dispatcher._worker_loop()
    except KeyboardInterrupt:
        logging.info("Graceful shutdown triggered.")
    finally:
        dispatcher.shutdown()
        services.get("driver_manager", {}).quit_driver()
        services.get("logger", {}).log_system_event("System shutdown complete.")


def run_pyqt_gui(app, services):
    """Run the PyQt GUI application."""
    # Initialize UI logic
    ui_logic = DreamscapeUILogic()
    ui_logic.service = services['prompt']  # Example: assign the prompt service

    # Extract required dependencies from the services dictionary
    prompt_manager = services.get('prompt_manager')
    config_manager = services.get('config_manager')
    logger = services.get('logger')
    discord_manager = services.get('discord_manager')  # Optional, if available
    memory_manager = services.get('memory_manager')      # Optional, if available

    # Initialize the dispatcher
    dispatcher = SignalDispatcher()
    
    # Add dispatcher to services
    services['dispatcher'] = dispatcher

    # Now pass all dependencies to MainTabs
    main_tabs = MainTabs(
        dispatcher=dispatcher,
        ui_logic=ui_logic,
        config_manager=config_manager,
        logger=logger,
        prompt_manager=prompt_manager,
        chat_manager=services.get('chat_manager'),
        memory_manager=memory_manager,
        discord_manager=discord_manager,
        cursor_manager=services.get('cursor_manager'),
        **services.get('extra_dependencies', {})
    )

    # Create your main window and set its central widget
    main_window = DreamscapeMainWindow(ui_logic, dispatcher, services)
    main_window.setCentralWidget(main_tabs)
    main_window.show()
    
    return main_window


def run_flask_app(services):
    """Launch the Flask web application in a separate thread."""
    def flask_thread():
        try:
            logging.info("Starting Flask Dashboard...")
            start_flask_app(services)
        except Exception as e:
            logging.error(f"Flask app error: {str(e)}")

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=flask_thread, daemon=True)
    flask_thread.start()
    return flask_thread


def execute_mode(mode, services, app=None):
    """Execute the selected mode."""
    if mode == "agent":
        run_agent_dispatcher(services)

    elif mode == "gui":
        if not app:
            app = QApplication(sys.argv)
        run_pyqt_gui(app, services)
        sys.exit(app.exec_())

    elif mode == "web":
        flask_thread = run_flask_app(services)
        try:
            while flask_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down Flask server...")

    elif mode == "all":
        logging.info("Launching all systems concurrently...")

        # Start Flask in a separate thread
        flask_thread = run_flask_app(services)

        # Start Agent Dispatcher in another thread
        agent_thread = threading.Thread(target=run_agent_dispatcher, args=(services,), daemon=True)
        agent_thread.start()

        # Start PyQt GUI in main thread
        if not app:
            app = QApplication(sys.argv)
        run_pyqt_gui(app, services)
        sys.exit(app.exec_())

def main():
    """Main entry point of the Dreamscape Execution System."""
    setup_logging()

    # Initialize core services
    config_manager = ConfigManager()
    logger = LoggerFactory.create_standard_logger("Dreamscape", level=logging.INFO)
    config_manager.set_logger(logger)

    # Initialize application services
    services = initialize_services()
    services['config_manager'] = config_manager
    services['logger'] = logger

    # ✅ Inject ChatManager using factory
    from core.micro_factories.chat_factory import create_chat_manager
    chat_manager = create_chat_manager(config_manager, logger=logger)
    services['chat_manager'] = chat_manager

    # Track initialization errors
    errors = []

    try:
        driver_manager = DriverManager(config_manager)
        services['driver_manager'] = driver_manager
    except Exception as e:
        error_msg = f"Failed to initialize DriverManager: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)

    parser = argparse.ArgumentParser(description="Dreamscape Execution System")
    parser.add_argument(
        "--mode",
        choices=["agent", "gui", "web", "all"],
        default="gui",
        help="Execution mode selection. Defaults to 'gui' if not specified."
    )
    args = parser.parse_args()

    # If there are errors and mode is not agent, show error dialog
    if errors and args.mode != "agent":
        app = QApplication(sys.argv)
        if not show_error_dialog(errors):
            logging.info("User aborted execution due to initialization errors.")
            return

    # Execute the chosen mode
    app = QApplication(sys.argv) if args.mode in ["gui", "all"] else None
    execute_mode(args.mode, services, app=app)
    
if __name__ == "__main__":
    main()