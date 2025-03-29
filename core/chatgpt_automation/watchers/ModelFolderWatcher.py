import time
import threading
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class ModelFolderWatcher(FileSystemEventHandler):
    """
    Watches the models directory for changes and triggers a model registry reload,
    debouncing rapid events to avoid redundant reloads.
    
    Improvements:
      - Configurable file extensions (defaults to .py).
      - Robust error handling when reloading models.
      - Ready for beta/production with clear logging and thread management.
    """
    def __init__(self, model_registry, watch_interval=1, debounce_delay=1, file_extensions=None):
        """
        :param model_registry: Instance of your ModelRegistry.
        :param watch_interval: Time (in seconds) between event checks (default: 1s).
        :param debounce_delay: Delay (in seconds) to debounce events (default: 1s).
        :param file_extensions: Iterable of file extensions to watch (default: ['.py']).
        """
        self.model_registry = model_registry
        self.models_dir = Path(model_registry.models_dir)
        self.watch_interval = watch_interval
        self.debounce_delay = debounce_delay
        self.debounce_timer = None
        self.file_extensions = file_extensions or ['.py']

        self.observer = Observer()
        self.thread = None

    def _debounced_reload(self):
        """
        Debounce mechanism: cancel any pending reload and schedule a new one after debounce_delay.
        """
        if self.debounce_timer and self.debounce_timer.is_alive():
            self.debounce_timer.cancel()
        # Wrap the reload call in a try/except for robustness.
        def reload_wrapper():
            try:
                logger.info("🔄 Reloading models...")
                self.model_registry.reload_models()
                logger.info("✅ Model registry reloaded successfully.")
            except Exception as e:
                logger.error(f"❌ Model registry reload failed: {e}")
        self.debounce_timer = threading.Timer(self.debounce_delay, reload_wrapper)
        self.debounce_timer.start()
        logger.info("🔄 Scheduled model reload (debounced).")

    def _should_handle(self, event_src_path):
        """
        Check if the event's source file has one of the configured extensions.
        """
        return any(event_src_path.endswith(ext) for ext in self.file_extensions)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_handle(event.src_path):
            logger.info(f"🔄 Detected modified model: {event.src_path}")
            self._debounced_reload()

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_handle(event.src_path):
            logger.info(f"➕ Detected new model: {event.src_path}")
            self._debounced_reload()

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._should_handle(event.src_path):
            logger.info(f"❌ Detected deleted model: {event.src_path}")
            self._debounced_reload()

    def start(self):
        """
        Starts the watchdog observer in a separate thread to avoid blocking the main application.
        """
        logger.info(f"👀 Starting ModelFolderWatcher on: {self.models_dir}")
        self.observer.schedule(self, str(self.models_dir), recursive=False)
        self.observer.start()
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

    def _watch_loop(self):
        try:
            while self.observer.is_alive():
                time.sleep(self.watch_interval)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Stops the watchdog observer and waits for the watch thread to finish.
        """
        logger.info("🛑 Stopping ModelFolderWatcher...")
        self.observer.stop()
        self.observer.join()
        if self.debounce_timer:
            self.debounce_timer.cancel()
        logger.info("✅ ModelFolderWatcher stopped.")
