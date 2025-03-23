import os
import json
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import subprocess
import openai
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import logging

from social.strategies.config_loader import get_env_or_config
from core.AletheiaPromptManager import AletheiaPromptManager

logger = logging.getLogger("UnifiedDreamscapeGenerator")
logger.setLevel(logging.INFO)

class OpenAIPromptEngine:
    def __init__(self, template_dir="chat_mate/templates/prompt_templates"):
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info(f"OpenAIPromptEngine initialized at {template_dir}")

    def render_prompt(self, template_name, context):
        try:
            template = self.jinja_env.get_template(template_name)
            rendered_prompt = template.render(context)
            logger.info(f"Rendered prompt: {template_name}")
            return rendered_prompt
        except TemplateNotFound as e:
            logger.error(f"Template not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Prompt rendering failed: {e}")
            raise

    def send_prompt(self, prompt, model="gpt-4o", temperature=0.7, max_tokens=1500):
        logger.info("Sending prompt to OpenAI...")
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        content = response['choices'][0]['message']['content'].strip()
        logger.info("OpenAI response received.")
        return content

class DreamscapeEpisodeGenerator:
    def __init__(self, chat_manager, response_handler, output_dir,
                 discord_manager=None, ollama_model="mistral", prompt_engine=None):
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.output_dir = output_dir
        self.discord_manager = discord_manager
        self.ollama_model = ollama_model
        self.prompt_engine = prompt_engine or OpenAIPromptEngine()
        self.aletheia = AletheiaPromptManager()

        self.episode_lock = threading.Lock()
        self.memory_lock = threading.Lock()

        self.episode_file = os.path.join(output_dir, "dreamscape_episodes.json")
        self.memory_update_file = os.path.join(output_dir, "memory_updates.json")
        self.index_file = os.path.join(output_dir, "episode_index.json")

        self.episodes = self._load_file(self.episode_file)
        self.memory_updates = self._load_file(self.memory_update_file)
        self.episode_index = self._load_file(self.index_file)

    def _load_file(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_file(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def generate_dreamscape_episodes(self, max_workers=3):
        logger.info(" Starting Dreamscape episode generation cycle...")
        chats = self.chat_manager.get_all_chat_titles()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_chat, chat): chat for chat in chats}
            for future in tqdm(as_completed(futures), total=len(chats), desc="Episodes Generation"):
                chat = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Failed to process chat {chat['title']}: {e}")

        logger.info(" Dreamscape episode generation complete.")

    def _process_chat(self, chat):
        chat_title = chat.get("title", "Untitled")
        chat_link = chat.get("link")
        if not chat_link:
            logger.warning(f"No link for chat '{chat_title}'. Skipping.")
            return

        self.response_handler.driver.get(chat_link)
        time.sleep(2)
        chat_messages = self.response_handler.scrape_current_chat_messages()

        memory_state = self.aletheia.memory_state
        context = {
            "CHAT_TITLE": chat_title,
            "CHAT_MESSAGES": "\n".join(chat_messages),
            "CURRENT_MEMORY_STATE": json.dumps(memory_state, indent=2)
        }

        prompt = self.prompt_engine.render_prompt("dreamscape_prompt.j2", context)
        episode_text = self.prompt_engine.send_prompt(prompt)

        enhanced_episode, memory_update = self._enhance_with_ollama(episode_text)

        episode_number = self._get_next_episode_number()
        timestamp = datetime.utcnow().isoformat() + "Z"
        sanitized_title = self._sanitize(chat_title)
        episode_record = {
            "episode_number": episode_number,
            "title": f"Episode {episode_number}: {chat_title}",
            "description": enhanced_episode,
            "timestamp": timestamp,
            "actions": ["Generated via OpenAI & Ollama"],
            "memory_update": memory_update or {}
        }

        episode_filename = f"episode_{episode_number}_{sanitized_title}.txt"
        episode_filepath = os.path.join(self.output_dir, episode_filename)
        with open(episode_filepath, "w", encoding="utf-8") as f:
            f.write(enhanced_episode)

        self._save_episode_data(episode_record, episode_filepath)

        if memory_update:
            self._save_memory_update(episode_number, memory_update, chat_title, timestamp)
            self.aletheia.parse_memory_updates(memory_update)

        if self.discord_manager:
            message = f"📜 **{episode_record['title']}**:\n{enhanced_episode[:1500]}..."
            self.discord_manager.send_message(message)

        logger.info(f" Episode {episode_number} '{chat_title}' processed successfully.")

    def _enhance_with_ollama(self, episode_text):
        prompt = (
            f"Improve and clarify this Dreamscape episode. Provide the narrative first, then clearly "
            f"include a JSON-formatted MEMORY_UPDATE.\n\n{episode_text}"
        )
        try:
            process = subprocess.run(
                ['ollama', 'run', self.ollama_model],
                input=prompt, text=True, capture_output=True, timeout=120
            )
            enhanced_output = process.stdout.strip()

            if "MEMORY_UPDATE:" in enhanced_output:
                narrative, memory_json = enhanced_output.split("MEMORY_UPDATE:", 1)
                memory_update = json.loads(memory_json.strip())
                return narrative.strip(), memory_update
            else:
                logger.warning("No MEMORY_UPDATE found in Ollama output.")
                return enhanced_output, None

        except Exception as e:
            logger.error(f"Ollama enhancement failed: {e}")
            return episode_text, None

    def _save_episode_data(self, episode, filepath):
        with self.episode_lock:
            self.episodes.append(episode)
            self.episode_index.append({
                "episode_number": episode["episode_number"],
                "title": episode["title"],
                "file_path": filepath,
                "timestamp": episode["timestamp"]
            })
            self._save_file(self.episode_file, self.episodes)
            self._save_file(self.index_file, self.episode_index)
            logger.info(f"️ Episode data saved: {filepath}")

    def _save_memory_update(self, episode_number, update, title, timestamp):
        with self.memory_lock:
            record = {
                "episode_number": episode_number,
                "chat_title": title,
                "timestamp": timestamp,
                "memory_update": update
            }
            self.memory_updates.append(record)
            self._save_file(self.memory_update_file, self.memory_updates)
            logger.info(f"🧠 MEMORY_UPDATE recorded for episode {episode_number}")

    def _get_next_episode_number(self):
        with self.episode_lock:
            return len(self.episodes) + 1

    @staticmethod
    def _sanitize(text):
        return "".join(c if c.isalnum() or c in '_-' else '_' for c in text).rstrip('_')

__all__ = ["DreamscapeEpisodeGenerator", "OpenAIPromptEngine"]
