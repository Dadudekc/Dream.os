import os
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger("PathManager")

BASE_DIR = os.getenv('CHAT_MATE_BASE_DIR', PROJECT_ROOT)

class PathManager:
    """
    Centralized Path Manager for ChatMate.
    Defines and ensures consistent folder structures across the system.
    """

    # === Base Directories ===
    base_dir = BASE_DIR
    outputs_dir = os.path.join(base_dir, "outputs")
    memory_dir = os.path.join(base_dir, "memory")
    templates_dir = os.path.join(base_dir, "templates")
    drivers_dir = os.path.join(base_dir, "drivers")
    configs_dir = os.path.join(base_dir, "configs")

    # === Output Subdirectories ===
    logs_dir = os.path.join(outputs_dir, "logs")
    cycles_dir = os.path.join(outputs_dir, "cycles")
    dreamscape_dir = os.path.join(cycles_dir, "dreamscape")
    workflow_audit_dir = os.path.join(cycles_dir, "workflow_audits")
    discord_exports_dir = os.path.join(outputs_dir, "discord_exports")
    reinforcement_logs_dir = os.path.join(outputs_dir, "reinforcement_logs")

    # === Template Subdirectories ===
    discord_templates_dir = os.path.join(templates_dir, "discord_templates")
    message_templates_dir = os.path.join(templates_dir, "message_templates")
    engagement_templates_dir = os.path.join(templates_dir, "engagement_templates")
    report_templates_dir = os.path.join(templates_dir, "report_templates")

    # === Strategies and Context DB ===
    strategies_dir = os.path.join(base_dir, "chat_mate", "social", "strategies")
    context_db_path = os.path.join(strategies_dir, "context_db.json")

    # === Dynamic path registry ===
    _paths_registry = {
        "base": base_dir,
        "outputs": outputs_dir,
        "memory": memory_dir,
        "templates": templates_dir,
        "drivers": drivers_dir,
        "configs": configs_dir,
        "logs": logs_dir,
        "cycles": cycles_dir,
        "dreamscape": dreamscape_dir,
        "workflow_audits": workflow_audit_dir,
        "discord_exports": discord_exports_dir,
        "reinforcement_logs": reinforcement_logs_dir,
        "discord_templates": discord_templates_dir,
        "message_templates": message_templates_dir,
        "engagement_templates": engagement_templates_dir,
        "report_templates": report_templates_dir,
        "strategies": strategies_dir,
        "context_db": context_db_path  # <-- 🔥 now registered
    }

    @classmethod
    def ensure_directories(cls, verbose: bool = False):
        """
        Ensure all required directories exist (files are skipped).
        """
        for key, path in cls._paths_registry.items():
            # Skip files (like context_db.json), only ensure directories
            if path.endswith('.json'):
                continue
            try:
                os.makedirs(path, exist_ok=True)
                if verbose:
                    logger.info(f"📁 Ensured directory exists: {path}")
            except Exception as e:
                logger.error(f"❌ Failed to create directory '{path}': {e}")

    @classmethod
    def get_path(cls, key: str) -> str:
        path = cls._paths_registry.get(key)
        if path:
            logger.debug(f"🔑 Retrieved path for '{key}': {path}")
        else:
            logger.warning(f"⚠️ Path key '{key}' not found.")
        return path

    @classmethod
    def register_path(cls, key: str, path: str):
        abs_path = os.path.abspath(path)
        cls._paths_registry[key] = abs_path
        if not abs_path.endswith('.json'):  # Avoid trying to create files as directories
            os.makedirs(abs_path, exist_ok=True)
        logger.info(f"✅ Registered custom path: {key} -> {abs_path}")

    @classmethod
    def list_paths(cls) -> dict:
        return cls._paths_registry.copy()

# === Bootstrap Directories on Load ===
if __name__ == "__main__":
    PathManager.ensure_directories(verbose=True)
