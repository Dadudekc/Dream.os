import time
import pyautogui
import subprocess
import os
import logging
import psutil

class CursorSessionManager:
    def __init__(self, project_root, cursor_exe="cursor"):
        self.project_root = project_root
        self.cursor_exe = cursor_exe
        self.logger = logging.getLogger("CursorSessionManager")

    def launch_cursor(self):
        """Launch Cursor IDE with the project directory"""
        try:
            self.logger.info("🚀 Launching Cursor IDE...")
            subprocess.Popen([self.cursor_exe, self.project_root])
            time.sleep(3)
        except Exception as e:
            self.logger.error(f"❌ Failed to launch Cursor: {e}")

    def focus_cursor_window(self):
        """Bring Cursor window into focus (platform-dependent)"""
        try:
            win = pyautogui.getWindowsWithTitle("Cursor")[0]
            win.activate()
            self.logger.info("🪟 Cursor window activated.")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not activate Cursor window: {e}")

    def trigger_prompt_execution(self):
        """Simulate Ctrl+Enter to execute prompt in Cursor"""
        try:
            self.logger.info("⌨️ Simulating Ctrl+Enter...")
            pyautogui.hotkey('ctrl', 'enter')
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"❌ Failed to simulate execution: {e}")

    def wait_for_cursor_response(self, timeout=60):
        """Poll output directory or screen region for signal of completion"""
        self.logger.info("⏳ Waiting for response (basic delay)...")
        time.sleep(timeout)

    def is_cursor_running(self):
        return any("cursor" in p.name().lower() for p in psutil.process_iter())

    def shutdown_cursor(self):
        for proc in psutil.process_iter():
            if "cursor" in proc.name().lower():
                proc.terminate()
                self.logger.info("🛑 Cursor IDE shut down.")

# === EXAMPLE USAGE ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    PROJECT_PATH = os.path.abspath(".")

    manager = CursorSessionManager(project_root=PROJECT_PATH)

    # Full Sync Simulation Flow
    if not manager.is_cursor_running():
        manager.launch_cursor()

    manager.focus_cursor_window()
    manager.trigger_prompt_execution()
    manager.wait_for_cursor_response(timeout=10)

    # Optionally shut down Cursor after test
    # manager.shutdown_cursor()

    print("✅ Example usage complete. Check logs for simulated trigger.")
