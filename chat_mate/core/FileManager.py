import os
import json
import yaml
import logging
import threading

logger = logging.getLogger("dreamscape_file_manager")


class FileManager:
    """
    Manages file saving, loading, and organizing for Digital Dreamscape.
    Supports plain text, JSON, and YAML formats.
    """

    def __init__(self, base_folder="Digital_DreamScape"):
        self.base_folder = base_folder
        self.ensure_directory(self.base_folder)
        self.lock = threading.Lock()

    def ensure_directory(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Directory created: {path}")

    @staticmethod
    def sanitize_filename(name):
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_"))
        return safe_name.strip().replace(" ", "_").lower()

    def save_entry(self, content, title, subfolder=None, extension=".txt"):
        folder = self.base_folder
        if subfolder:
            folder = os.path.join(self.base_folder, subfolder)
            self.ensure_directory(folder)

        filename = f"{self.sanitize_filename(title)}{extension}"
        filepath = os.path.join(folder, filename)

        with self.lock:
            try:
                if extension == ".json":
                    with open(filepath, "w", encoding="utf-8") as file:
                        json.dump(content, file, indent=4)
                elif extension in [".yaml", ".yml"]:
                    with open(filepath, "w", encoding="utf-8") as file:
                        yaml.dump(content, file, default_flow_style=False, allow_unicode=True)
                else:
                    with open(filepath, "w", encoding="utf-8") as file:
                        file.write(content)

                logger.info(f"Entry saved: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Failed to save entry: {filepath}. Error: {e}")
                return None

    def load_entry(self, title, subfolder=None, extension=".txt"):
        folder = self.base_folder
        if subfolder:
            folder = os.path.join(self.base_folder, subfolder)

        filename = f"{self.sanitize_filename(title)}{extension}"
        filepath = os.path.join(folder, filename)

        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return None

        with self.lock:
            try:
                if extension == ".json":
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        if not isinstance(data, (dict, list)):
                            logger.warning(f"Unexpected JSON structure in file: {filepath}")
                            return None
                        return data

                elif extension in [".yaml", ".yml"]:
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = yaml.safe_load(file)
                        if not isinstance(data, (dict, list)):
                            logger.warning(f"Unexpected YAML structure in file: {filepath}")
                            return None
                        if isinstance(data, dict) and all(v is None for v in data.values()):
                            logger.warning(f"YAML has keys but no meaningful values: {filepath}")
                            return None
                        return data

                else:
                    with open(filepath, "r", encoding="utf-8") as file:
                        return file.read()

            except Exception as e:
                logger.error(f"Failed to load entry: {filepath}. Error: {e}")
                return None

    def archive_entry(self, content, title, subfolder="archive", extension=".txt"):
        """
        Archives an entry by saving it in a dedicated archive subfolder.
        """
        folder = os.path.join(self.base_folder, subfolder)
        self.ensure_directory(folder)

        filename = f"{self.sanitize_filename(title)}{extension}"
        filepath = os.path.join(folder, filename)

        with self.lock:
            try:
                if extension == ".json":
                    with open(filepath, "w", encoding="utf-8") as file:
                        json.dump(content, file, indent=4)
                elif extension in [".yaml", ".yml"]:
                    with open(filepath, "w", encoding="utf-8") as file:
                        yaml.dump(content, file, default_flow_style=False, allow_unicode=True)
                else:
                    with open(filepath, "w", encoding="utf-8") as file:
                        file.write(content)

                logger.info(f"Entry archived: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Failed to archive entry: {filepath}. Error: {e}")
                return None
