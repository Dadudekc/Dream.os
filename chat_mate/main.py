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
from core.logging.factories.LoggerFactory import LoggerFactory

# GUI and Web imports
from gui.DreamscapeMainWindow import DreamscapeMainWindow
from gui.dreamscape_ui_logic import DreamscapeUILogic
from gui.IntegratedMainWindow import IntegratedMainWindow
from gui.components.prompt_panel import PromptPanel
from gui.components.logs_panel import LogsPanel
from gui.tabs.MainTabs import MainTabs
from gui.tabs.PromptExecutionTab import PromptExecutionTab
from gui.tabs.LogsTab import LogsTab
from gui.tabs.ConfigurationTab import ConfigurationTab
from gui.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from web.app import start_flask_app
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

    # Now pass all dependencies to MainTabs
    main_tabs = MainTabs(
        ui_logic=ui_logic,
        prompt_manager=prompt_manager,
        config_manager=config_manager,
        logger=logger,
        discord_manager=discord_manager,
        memory_manager=memory_manager
    )

    # Create your main window and set its central widget
    main_window = DreamscapeMainWindow(ui_logic)
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
