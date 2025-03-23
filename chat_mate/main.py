import logging
import argparse
import threading
import sys
import time
from PyQt5.QtWidgets import QApplication, QMessageBox

# Bootstrap paths early
from core.bootstrap import get_bootstrap_paths
from core.AgentDispatcher import AgentDispatcher
from core.ConfigManager import ConfigManager
from core.DriverManager import DriverManager
from core.logger_factory import LoggerFactory

# GUI and Web imports
from gui.DreamscapeMainWindow import DreamscapeMainWindow
from gui.dreamscape_ui_logic import DreamscapeUILogic
from web.app import start_flask_app
from gui.splash_screen import show_splash_screen
from services.config_service import ConfigService
from services.prompt_service import PromptService


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def initialize_services():
    """Initialize application services."""
    services = {}
    
    # Initialize config service
    config_service = ConfigService()
    services['config'] = config_service
    
    # Initialize prompt service
    prompt_service = PromptService(config_service)
    services['prompt'] = prompt_service
    
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


def run_pyqt_gui():
    """Run the PyQt GUI application."""
    # Initialize services
    services = initialize_services()
    
    # Create UI logic instance
    ui_logic = DreamscapeUILogic()
    ui_logic.service = services['prompt']  # Pass the prompt service
    
    # Create and show main window
    app = QApplication(sys.argv)
    main_window = DreamscapeMainWindow(ui_logic)
    main_window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


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


def execute_mode(mode, services):
    """Execute the selected mode."""
    if mode == "agent":
        run_agent_dispatcher(services)
    elif mode == "gui":
        run_pyqt_gui()
    elif mode == "web":
        # Start Flask in a separate thread
        flask_thread = run_flask_app(services)
        # Keep the main thread alive
        try:
            while flask_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down Flask server...")
    elif mode == "all":
        logging.info("Launching all systems concurrently...")
        # Start Flask in a separate thread
        flask_thread = run_flask_app(services)
        
        # Start other components in separate threads
        threads = [
            threading.Thread(target=run_agent_dispatcher, args=(services,), daemon=True),
            threading.Thread(target=run_pyqt_gui, daemon=True),
        ]
        
        for t in threads:
            t.start()
            
        # Wait for all threads
        for t in threads + [flask_thread]:
            t.join()


def main():
    """Main entry point of the Dreamscape Execution System."""
    setup_logging()

    # Initialize core services
    config_manager = ConfigManager()
    logger = LoggerFactory.create_logger(config_manager)
    config_manager.set_logger(logger)

    # Initialize application services
    services = initialize_services()
    services['config_manager'] = config_manager
    services['logger'] = logger

    # Track initialization errors
    errors = []

    try:
        # Initialize driver manager if needed
        driver_manager = DriverManager(config_manager)
        services['driver_manager'] = driver_manager
    except Exception as e:
        errors.append(f"Failed to initialize DriverManager: {str(e)}")
        logger.log_error(str(e))

    parser = argparse.ArgumentParser(description="Dreamscape Execution System")
    parser.add_argument(
        "--mode",
        choices=["agent", "gui", "web", "all"],
        default=None,
        help="Execution mode selection."
    )
    args = parser.parse_args()

    # Handle errors if present
    if errors and args.mode != "agent":
        if not show_error_dialog(errors):
            logging.info("User aborted execution due to initialization errors.")
            return

    # Direct execution if mode is set
    if args.mode:
        execute_mode(args.mode, services)
    else:
        # Show splash screen if no mode is given
        app = QApplication(sys.argv)
        splash = show_splash_screen()

        def on_mode_selected(mode):
            splash.close()
            execute_mode(mode, services)

        splash.mode_selected.connect(on_mode_selected)
        # Only call exec_() once here
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
