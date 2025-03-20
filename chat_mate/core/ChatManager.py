import os
import time
import logging
import threading
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# New modularized imports
from utils.DriverManager import DriverManager
from core.PromptEngine import PromptEngine
from core.DiscordManager import DiscordManager
from core.AletheiaPromptManager import AletheiaPromptManager
from chat_mate_config import Config, get_logger

logger = get_logger("chat_manager")


def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be safe for filenames."""
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    return filename.strip().replace(" ", "_")[:50]


class ChatManager:
    ALLOWED_MODELS = [
        "gpt-4o-mini",  # default
        "gpt-4o",
        "gpt-4o-jawbone",
        "gpt-4-5",
        "o3-mini-high",
        "o1"
    ]

    def __init__(self,
                 driver_manager: Optional[DriverManager] = None,
                 prompt_manager: Optional[AletheiaPromptManager] = None,
                 excluded_chats: Optional[List[str]] = None,
                 scroll_pause: float = 1.5,
                 model: str = "gpt-4o-mini",
                 scroll_multiplier: float = 1.0,
                 timeout: int = 180,
                 stable_period: int = 10,
                 poll_interval: int = 5,
                 headless: bool = False,
                 reinforcement_engine: Optional[Any] = None,
                 discord_manager: Optional[DiscordManager] = None) -> None:

        if model not in self.ALLOWED_MODELS:
            raise ValueError(f"Invalid model '{model}'. Must be one of {self.ALLOWED_MODELS}")
        self.excluded_chats = excluded_chats or []
        self.model = model
        self.scroll_pause = scroll_pause
        self.scroll_multiplier = scroll_multiplier
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval
        self.headless = headless
        self.reinforcement_engine = reinforcement_engine

        # GUI placeholders (set externally if needed)
        self.prompt_editor = None
        self.exclusion_list = None
        self.model_selector = None
        self.archive_checkbox = None
        self.reverse_checkbox = None
        self.output_dir = None

        # Injected managers; create if not provided.
        self.driver_manager = driver_manager or DriverManager(profile_dir=Config.PROFILE_DIR, headless=self.headless)
        self.prompt_manager = prompt_manager or AletheiaPromptManager()
        self.discord_manager = discord_manager  # Set externally if available

        # Create a PromptEngine using the driver.
        self.prompt_engine = PromptEngine(
            self.driver_manager.get_driver(),
            timeout=self.timeout,
            stable_period=self.stable_period,
            poll_interval=self.poll_interval,
            reinforcement_engine=self.reinforcement_engine
        )

    @property
    def driver(self) -> Any:
        return self.driver_manager.get_driver()

    def shutdown_driver(self) -> None:
        self.driver_manager.quit_driver()

    def set_model(self, new_model: str) -> None:
        if new_model not in self.ALLOWED_MODELS:
            raise ValueError(f"Invalid model '{new_model}'. Must be one of {self.ALLOWED_MODELS}")
        self.model = new_model
        logger.info(f"Model updated to: {new_model}")

    def ensure_model_in_url(self, url: str) -> str:
        if f"model={self.model}" not in url:
            sep = "&" if "?" in url else "?"
            new_url = f"{url}{sep}model={self.model}"
            logger.info(f"Updated URL with model param: {new_url}")
            return new_url
        return url

    # ------------------------------
    # LOGIN CHECK
    # ------------------------------
    def is_logged_in(self, chatgpt_url: str = Config.CHATGPT_URL) -> bool:
        driver = self.driver
        driver.get(chatgpt_url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Chat history"]'))
            )
            logger.info("Login confirmed. Sidebar detected.")
            return True
        except Exception as e:
            logger.warning(f"Login check failed: {e}")
            return False

    # ------------------------------
    # RETRIEVING CHAT TITLES
    # ------------------------------
    def get_all_chat_titles(self, chatgpt_url: str = Config.CHATGPT_URL) -> List[Dict[str, str]]:
        logger.info("Retrieving all chat titles with pagination...")
        driver = self.driver
        driver.get(chatgpt_url)
        sidebar_selector = "div.flex-col.flex-1.transition-opacity.duration-500.relative.pr-3.overflow-y-auto"
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sidebar_selector))
            )
        except Exception as e:
            logger.error(f"Failed to locate chat sidebar: {e}")
            return []

        chat_links: Dict[str, str] = {}
        same_height_count = 0
        max_same_height = 3
        last_height = driver.execute_script("return document.querySelector(arguments[0]).scrollHeight", sidebar_selector)

        while same_height_count < max_same_height:
            chats = driver.find_elements(By.CSS_SELECTOR, 'nav[aria-label="Chat history"] a')
            for chat in chats:
                try:
                    title = chat.text.strip()
                except StaleElementReferenceException:
                    logger.warning("Stale element encountered for chat title; skipping.")
                    continue

                if not title or any(title.lower() == ex.lower() for ex in self.excluded_chats):
                    continue

                try:
                    href = chat.get_attribute("href")
                except StaleElementReferenceException:
                    logger.warning("Stale element encountered for chat href; skipping.")
                    continue

                if title not in chat_links and href:
                    chat_links[title] = self.ensure_model_in_url(href)

            try:
                driver.execute_script(
                    "document.querySelector(arguments[0]).scrollTop = document.querySelector(arguments[0]).scrollHeight",
                    sidebar_selector
                )
            except Exception as e:
                logger.error(f"Error scrolling: {e}")
                break

            time.sleep(self.scroll_pause)
            new_height = driver.execute_script("return document.querySelector(arguments[0]).scrollHeight", sidebar_selector)
            if new_height == last_height:
                same_height_count += 1
            else:
                same_height_count = 0
            last_height = new_height

        logger.info(f"Total chats collected: {len(chat_links)}")
        return [{"title": t, "link": link} for t, link in chat_links.items()]

    # ------------------------------
    # PROMPT EXECUTION METHODS
    # ------------------------------
    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int = 0) -> List[str]:
        responses: List[str] = []
        if not self.is_logged_in():
            logger.warning("Login required for single-chat mode. Please log in via your browser.")
            return responses
        for idx, prompt_text in enumerate(prompts, start=1):
            logger.info(f"[Single-Chat Mode] Prompt #{idx}: {prompt_text[:60]}...")
            self.driver.get(f"{Config.CHATGPT_URL}?model={self.model}")
            time.sleep(3)
            if not self.prompt_engine.send_prompt(prompt_text):
                logger.error("Prompt submission failed. Skipping this prompt.")
                responses.append("")
                continue
            stable_response = self.prompt_engine.wait_for_stable_response()
            responses.append(stable_response)
            time.sleep(cycle_speed)
        return responses

    def execute_prompt_cycle(self, prompt: str) -> str:
        if not self.is_logged_in():
            logger.warning("Login required. Please log in via your browser.")
            return ""
        self.driver.get(f"{Config.CHATGPT_URL}?model={self.model}")
        time.sleep(3)
        if not self.prompt_engine.send_prompt(prompt):
            logger.error("Prompt submission failed. Aborting cycle.")
            return ""
        stable_response = self.prompt_engine.wait_for_stable_response()
        return stable_response

    def execute_prompt_to_chat(self, prompt: str, chat_info: Dict[str, str]) -> str:
        if not self.is_logged_in():
            logger.warning("Login required. Please log in via your browser.")
            return ""
        title = chat_info.get("title", "Untitled")
        link = chat_info.get("link")
        if not link:
            logger.warning(f"Chat '{title}' has no valid link. Skipping.")
            return ""
        logger.info(f"Opening chat '{title}' and sending prompt...")
        self.driver.get(link)
        time.sleep(3)
        if not self.prompt_engine.send_prompt(prompt):
            logger.error(f"Failed to send prompt to chat '{title}'.")
            return ""
        stable_response = self.prompt_engine.wait_for_stable_response()
        return stable_response

    def execute_prompts_on_all_chats(self, prompts: List[str], chat_list: List[Dict[str, str]]) -> Dict[str, List[str]]:
        if not self.is_logged_in():
            logger.warning("Login required. Please log in via your browser.")
            return {}
        results: Dict[str, List[str]] = {}
        for chat_info in chat_list:
            title = chat_info.get("title", "Untitled")
            link = chat_info.get("link")
            if not link:
                logger.warning(f"Chat '{title}' has no valid link. Skipping.")
                results[title] = []
                continue
            logger.info(f"Opening existing chat: {title}")
            self.driver.get(link)
            time.sleep(3)
            chat_responses: List[str] = []
            for idx, prompt_text in enumerate(prompts, start=1):
                logger.info(f"Sending prompt #{idx} to '{title}': {prompt_text[:60]}...")
                if not self.prompt_engine.send_prompt(prompt_text):
                    logger.error(f"Failed to send prompt #{idx} to chat '{title}'.")
                    chat_responses.append("")
                    continue
                stable_response = self.prompt_engine.wait_for_stable_response()
                chat_responses.append(stable_response)
            results[title] = chat_responses
        return results

    def cycle_prompts_through_all_chats(self, prompts: List[str], cycle_speed: int = 0, output_dir: str = "output") -> None:
        if not self.is_logged_in():
            logger.warning("Login required. Please log in via your browser.")
            return
        all_chats = self.get_all_chat_titles()
        logger.info(f"Found {len(all_chats)} chats.")
        if self.reverse_checkbox and self.reverse_checkbox.isChecked():
            all_chats.reverse()
            logger.info("Processing chats in reverse order.")
        os.makedirs(output_dir, exist_ok=True)
        for prompt_text in prompts:
            prompt_dir_name = sanitize_filename(prompt_text)
            prompt_dir = os.path.join(output_dir, prompt_dir_name)
            os.makedirs(prompt_dir, exist_ok=True)
            logger.info(f"Processing prompt '{prompt_text}' in directory '{prompt_dir}'")
            for chat in all_chats:
                chat_title = chat.get("title", "Untitled")
                chat_link = chat.get("link")
                if not chat_link:
                    logger.warning(f"Skipping chat '{chat_title}' (no link).")
                    continue
                logger.info(f"Opening chat '{chat_title}' for prompt '{prompt_dir_name}'")
                self.driver.get(chat_link)
                time.sleep(3)
                if not self.prompt_engine.send_prompt(prompt_text):
                    logger.error(f"Failed to send prompt '{prompt_text}' to chat '{chat_title}'")
                    continue
                response = self.prompt_engine.wait_for_stable_response()
                chat_filename = sanitize_filename(chat_title) + ".txt"
                chat_file_path = os.path.join(prompt_dir, chat_filename)
                try:
                    with open(chat_file_path, 'w', encoding='utf-8') as f:
                        f.write(response)
                    logger.info(f"✅ Saved response for chat '{chat_title}' in '{chat_file_path}'")
                except Exception as e:
                    logger.error(f"❌ Error saving chat '{chat_title}' response: {e}")
                time.sleep(cycle_speed)
        logger.info("✅ Completed full prompt cycle across all chats.")

    def analyze_execution_response(self, response: str, prompt_text: str) -> Dict[str, Any]:
        return {
            "victor_tactics_used": ["Pattern recognition", "Automation scaling"],
            "adaptive_executions": ["Refined pipeline sequence"],
            "identified_efficiencies": ["Reduced manual intervention by 20%"],
            "suggested_next_steps": ["Test deeper AI-integrated market scans"]
        }

    # ------------------------------
    # DREAMSCAPE EPISODE GENERATION
    # ------------------------------
    def generate_dreamscape_episodes(self, output_dir: str = "dreamscape_episodes", cycle_speed: int = 0) -> None:
        if not self.is_logged_in():
            logger.warning("Login required. Please log in via your browser.")
            return
        all_chats = self.get_all_chat_titles()
        logger.info(f"Found {len(all_chats)} chats for Dreamscape episode generation.")
        os.makedirs(output_dir, exist_ok=True)
        if not self.prompt_manager:
            logger.error("Prompt manager not set. Cannot retrieve 'dreamscape' prompt.")
            return
        base_dreamscape_prompt = self.prompt_manager.get_prompt("dreamscape")
        episode_counter = self.prompt_manager.prompts.get("dreamscape", {}).get("episode_counter", 1)
        for chat in all_chats:
            chat_title = chat.get("title", "Untitled")
            chat_link = chat.get("link")
            if not chat_link:
                logger.warning(f"Skipping chat '{chat_title}' (no link).")
                continue
            logger.info(f"Processing Dreamscape episode for chat: {chat_title}")
            self.driver.get(chat_link)
            time.sleep(3)
            previous_episode = ""
            episode_file_prefix = f"episode_{episode_counter - 1}_" if episode_counter > 1 else ""
            previous_episode_path = os.path.join(output_dir, f"{episode_file_prefix}{sanitize_filename(chat_title)}.txt")
            if os.path.exists(previous_episode_path):
                try:
                    with open(previous_episode_path, 'r', encoding='utf-8') as f:
                        previous_episode = f.read().strip()
                    logger.info(f"Including previous episode for chat '{chat_title}'.")
                except Exception as e:
                    logger.error(f"Error reading previous episode for chat '{chat_title}': {e}")
            episode_prompt = base_dreamscape_prompt + f"\nEpisode {episode_counter}:"
            if previous_episode:
                episode_prompt += f"\nContinue from:\n{previous_episode}\n"
            if not self.prompt_engine.send_prompt(episode_prompt):
                logger.error(f"Failed to send Dreamscape prompt to chat '{chat_title}'")
                continue
            episode_response = self.prompt_engine.wait_for_stable_response()
            if not episode_response:
                logger.warning(f"No stable response for Dreamscape episode for chat '{chat_title}'")
                continue
            episode_filename = f"episode_{episode_counter}_{sanitize_filename(chat_title)}.txt"
            episode_file_path = os.path.join(output_dir, episode_filename)
            try:
                with open(episode_file_path, 'w', encoding='utf-8') as f:
                    f.write(episode_response)
                logger.info(f"✅ Saved Dreamscape episode for chat '{chat_title}' as '{episode_file_path}'")
            except Exception as e:
                logger.error(f"Error saving Dreamscape episode for chat '{chat_title}': {e}")
            if self.discord_manager:
                episode_msg = f"New Dreamscape Episode {episode_counter} generated for chat '{chat_title}'."
                try:
                    self.discord_manager.send_message("dreamscape", episode_msg)
                    logger.info(f"Posted Discord update: {episode_msg}")
                except Exception as e:
                    logger.error(f"Error posting Discord update: {e}")
            episode_counter += 1
            time.sleep(cycle_speed)
        logger.info("✅ Completed Dreamscape episode generation.")

    # ------------------------------
    # GUI / UTILITY METHODS
    # ------------------------------
    def run_single_chat_mode(self) -> None:
        prompt_text = self.prompt_editor.toPlainText().strip() if self.prompt_editor else ""
        if not prompt_text:
            self.append_output("No prompt text provided. Aborting single-chat execution.")
            return
        self.append_output("Launching single-chat execution.")
        def single_chat_thread() -> None:
            prompts = [prompt_text]
            responses = self.execute_prompts_single_chat(prompts, cycle_speed=1)
            for i, resp in enumerate(responses, start=1):
                self.append_output(f"Prompt #{i} => {resp}")
            self.append_output("Single-chat execution complete.")
        threading.Thread(target=single_chat_thread, daemon=True).start()

    def run_multi_chat_mode(self) -> None:
        raw_prompt_text = self.prompt_editor.toPlainText().strip() if self.prompt_editor else ""
        if not raw_prompt_text:
            self.append_output("No prompt text provided. Aborting multi-chat execution.")
            return
        prompts = [line.strip() for line in raw_prompt_text.splitlines() if line.strip()]
        if not prompts:
            self.append_output("No valid prompts extracted from the editor.")
            return
        self.append_output("Launching multi-chat sequential execution.")
        def multi_chat_thread() -> None:
            all_chats = self.get_all_chat_titles()
            if self.reverse_checkbox and self.reverse_checkbox.isChecked():
                all_chats.reverse()
            if not all_chats:
                self.append_output("No chats found. Aborting multi-chat execution.")
                return
            for chat in all_chats:
                chat_title = chat.get("title", "Untitled")
                self.append_output(f"\n--- Processing Chat: {chat_title} ---")
                for idx, prompt in enumerate(prompts, start=1):
                    self.append_output(f"Sending Prompt #{idx} to {chat_title}: {prompt}")
                    response = self.execute_prompt_cycle(prompt)
                    self.append_output(f"Response for Prompt #{idx} in {chat_title}: {response}")
                if self.archive_checkbox and self.archive_checkbox.isChecked():
                    self.append_output(f"Archiving chat: {chat_title}")
                    self.archive_chat(chat)
            self.append_output("Multi-chat sequential execution complete.")
        threading.Thread(target=multi_chat_thread, daemon=True).start()

    def start_scraping(self, keep_driver_open: bool = False) -> None:
        self.append_output("Initializing scraping session...")
        exclusions = [item.text() for item in self.exclusion_list.selectedItems()] if self.exclusion_list else []
        self.excluded_chats = exclusions
        if self.is_logged_in():
            self.append_output("Login detected. Proceeding with scraping.")
        else:
            self.append_output("Not logged in. Please complete login in the browser.")
            self.driver.get("https://chat.openai.com/auth/login")
            return
        self.append_output("Starting chat scraping process...")
        all_chats = self.get_all_chat_titles()
        self.append_output(f"Found {len(all_chats)} chats to process.")
        if self.reverse_checkbox and self.reverse_checkbox.isChecked():
            all_chats.reverse()
            self.append_output("Processing chats in reverse order.")
        for chat in all_chats:
            self.append_output(f"Scrape found chat: {chat['title']} => {chat['link']}")
        self.append_output("Scraping session complete!")
        if not keep_driver_open:
            self.shutdown_driver()

    def load_selected_prompt(self, prompt_type: str) -> None:
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)
            self.prompt_editor.setPlainText(prompt_text)
            idx = self.model_selector.findText(model)
            if idx != -1:
                self.model_selector.setCurrentIndex(idx)
        except ValueError as e:
            print(f"Prompt Error: {e}")

    def save_prompt(self) -> None:
        prompt_type = self.prompt_selector.currentText()
        new_prompt = self.prompt_editor.toPlainText()
        selected_model = self.model_selector.currentText()
        self.prompt_manager.add_prompt(prompt_type, new_prompt, selected_model)
        print(f"Prompt for '{prompt_type}' saved successfully with model '{selected_model}'.")

    def reset_prompts(self) -> None:
        confirm = input("Are you sure you want to reset all prompts to default values? (y/n): ")
        if confirm.lower() == "y":
            self.prompt_manager.reset_to_defaults()
            self.prompt_selector.clear()
            self.prompt_selector.addItems(self.prompt_manager.list_available_prompts())
            self.load_selected_prompt(self.prompt_selector.currentText())
            print("Prompts have been reset to defaults.")

    def add_exclusion(self, title: str) -> None:
        if title and self.exclusion_list:
            from PyQt5.QtWidgets import QListWidgetItem
            self.exclusion_list.addItem(QListWidgetItem(title))
            self.exclusion_input.clear()

    def remove_exclusion(self) -> None:
        if self.exclusion_list:
            for item in self.exclusion_list.selectedItems():
                self.exclusion_list.takeItem(self.exclusion_list.row(item))
            self.append_output("Selected exclusions removed.")

    def browse_output_dir(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir.setText(directory)
            self.append_output(f"Output directory set to: {directory}")

    def append_output(self, text: str) -> None:
        if hasattr(self, 'output_widget') and self.output_widget:
            # Replace with actual GUI output code if needed.
            pass
        else:
            print(text)

    def archive_chat(self, chat: Dict[str, str]) -> None:
        try:
            title = chat.get('title', 'Untitled')
            link = chat.get('link')
            if not link:
                logger.warning(f"⚠️ No valid link for chat '{title}'. Skipping archive.")
                return
            logger.info(f"📂 Opening chat '{title}' for archiving: {link}")
            self.driver.get(link)
            WebDriverWait(self.driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            retries = 3
            for attempt in range(retries):
                try:
                    logger.debug("🔎 Looking for delete button...")
                    delete_button_selector = "button[aria-label='Delete chat']"
                    delete_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, delete_button_selector))
                    )
                    delete_button.click()
                    logger.debug("🗑️ Delete button clicked.")
                    break
                except StaleElementReferenceException as e:
                    logger.warning(f"StaleElementReference on delete button (attempt {attempt + 1}). Retrying...")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Failed to find or click delete button on '{title}': {e}")
                    return
            time.sleep(1)
            for attempt in range(retries):
                try:
                    logger.debug("🔎 Looking for confirm button...")
                    confirm_button_selector = "button.confirm"
                    confirm_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_button_selector))
                    )
                    confirm_button.click()
                    logger.info(f"✅ Chat '{title}' archived successfully.")
                    break
                except StaleElementReferenceException as e:
                    logger.warning(f"StaleElementReference on confirm button (attempt {attempt + 1}). Retrying...")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Failed to confirm deletion on '{title}': {e}")
                    return
            time.sleep(1)
        except Exception as e:
            logger.error(f"💥 Error archiving chat '{title}': {e}")
            self.append_output(f"💥 Error archiving chat '{title}': {e}")

    def open_discord_settings(self) -> None:
        from core.discord_manager import DiscordSettingsDialog
        dialog = DiscordSettingsDialog(parent=self)
        dialog.exec_()

    def launch_discord_bot(self, bot_token: str, channel_id: int) -> None:
        self.append_output("Launching Discord bot...")
        self.discord_manager = DiscordManager(bot_token, channel_id)
        def run_bot() -> None:
            self.discord_manager.run_bot()
        self.discord_thread = threading.Thread(target=run_bot, daemon=True)
        self.discord_thread.start()
        self.append_output("Discord bot launched in background.")

    def open_reinforcement_tools(self) -> None:
        from core.reinforcement_tools import ReinforcementToolsDialog
        dialog = ReinforcementToolsDialog(parent=self)
        dialog.exec_()

    def run_prompt_tuning(self) -> None:
        self.prompt_manager.auto_tune_prompts()
        self.append_output("🔄 Auto-Tuning Completed: Prompts optimized using feedback data.")

    def launch_dashboard(self) -> None:
        self.append_output("Launching feedback dashboard... (stub)")

    def show_log_analysis(self) -> None:
        self.append_output("Showing log analysis... (stub)")


# --------------------------------------------------------------------
# Main Entry Point - Launch the GUI
# --------------------------------------------------------------------
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    from gui.dreamscape_gui import DreamscapeGUI
    app = QApplication(sys.argv)
    window = DreamscapeGUI()
    window.show()
    sys.exit(app.exec_())
