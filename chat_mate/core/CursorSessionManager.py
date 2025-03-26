import time
import platform
import pyautogui
import pygetwindow as gw
import pyperclip
import logging

logging.basicConfig(level=logging.INFO)

class CursorSessionManager:
    VALID_MODES = ["full_sync", "tdd", "async", "repl"]

    DEFAULT_HOTKEYS = {
        "open_prompt": ['ctrl', 'shift', 'p'],
        "paste": ['ctrl', 'v'],
        "select_all": ['ctrl', 'a'],
        "copy": ['ctrl', 'c']
    }

    def __init__(self, config, memory_manager=None):
        self.execution_mode = config.get("execution_mode", "full_sync")
        self.cursor_window_title = config.get("cursor_window_title", "Cursor")
        self.prompt_delay = config.get("prompt_delay", 5)
        self.hotkeys = config.get("hotkeys", self.DEFAULT_HOTKEYS)
        self.logger = logging.getLogger(__name__)
        self.memory_manager = memory_manager

    def focus_cursor_window(self):
        windows = gw.getWindowsWithTitle(self.cursor_window_title)
        if not windows:
            self.logger.error(f"No window found with title '{self.cursor_window_title}'")
            raise RuntimeError("Cursor window not found.")

        cursor_window = windows[0]
        cursor_window.activate()
        self.logger.info(f"Focused Cursor window: '{cursor_window.title}'")
        time.sleep(1)

    def generate_prompt(self, task, context=None):
        prompt_parts = [f"# TASK: {task}\n"]

        if context:
            prompt_parts.append("## CONTEXT\n" + "\n".join(context))

        instructions = {
            "full_sync": "- Rapid, comprehensive solution with error handling.",
            "tdd": "- Write tests first, follow Red-Green-Refactor.",
            "async": "- Asynchronous implementation (async/await).",
            "repl": "- REPL-friendly immediate execution."
        }

        prompt_parts.append(
            f"## MODE: {self.execution_mode.upper()}\n{instructions[self.execution_mode]}"
        )

        prompt = "\n\n".join(prompt_parts)
        self.logger.debug(f"Generated prompt:\n{prompt}")
        return prompt

    def safe_copy_to_clipboard(self, text, retries=3, delay=0.5):
        for attempt in range(retries):
            try:
                pyperclip.copy(text)
                if pyperclip.paste() == text:
                    return True
            except pyperclip.PyperclipException as e:
                self.logger.warning(f"Clipboard copy attempt {attempt+1} failed: {e}")
                time.sleep(delay)
        raise RuntimeError("Failed to copy text to clipboard after retries.")

    def execute_prompt(self, prompt):
        self.focus_cursor_window()

        self.safe_copy_to_clipboard(prompt)
        time.sleep(0.5)

        pyautogui.hotkey(*self.hotkeys["open_prompt"])
        time.sleep(1)

        pyautogui.hotkey(*self.hotkeys["paste"])
        time.sleep(0.5)

        pyautogui.press('enter')
        self.logger.info("Prompt submitted to Cursor IDE.")

        self.logger.info(f"Waiting {self.prompt_delay} seconds for response...")
        time.sleep(self.prompt_delay)

        pyautogui.hotkey(*self.hotkeys["select_all"])
        time.sleep(0.5)
        pyautogui.hotkey(*self.hotkeys["copy"])
        time.sleep(0.5)

        try:
            generated_code = pyperclip.paste()
            if not generated_code.strip():
                raise ValueError("Retrieved empty content from Clipboard.")
        except pyperclip.PyperclipException as e:
            self.logger.error(f"Failed to retrieve generated code from Clipboard: {e}")
            raise RuntimeError("Clipboard paste failed.")

        self.logger.info("Generated code successfully retrieved.")
        return generated_code

    def switch_mode(self, mode):
        if mode not in self.VALID_MODES:
            self.logger.error(f"Invalid mode '{mode}'. Valid modes: {self.VALID_MODES}")
            raise ValueError(f"Invalid mode '{mode}'.")
        self.execution_mode = mode
        self.logger.info(f"Switched execution mode to: {mode}")
