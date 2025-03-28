from dependency_injector import containers, providers

# Core Services
from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.AletheiaPromptManager import AletheiaPromptManager
from core.PromptResponseHandler import PromptResponseHandler
from config.ConfigManager import ConfigManager
from core.DiscordQueueProcessor import DiscordQueueProcessor

# Local LLM Backends
from core.llm_backends.huggingface_backend import HuggingFaceBackend
from core.llm_backends.ollama_backend import OllamaBackend

class ServiceContainer(containers.DeclarativeContainer):
    """Container for service dependencies."""

    config = providers.Configuration()

    # Core services
    config_manager = providers.Singleton(ConfigManager)
    prompt_manager = providers.Singleton(AletheiaPromptManager)
    orchestrator = providers.Singleton(PromptCycleOrchestrator, config=config_manager)
    response_handler = providers.Singleton(PromptResponseHandler, config=config_manager)
    discord_processor = providers.Singleton(DiscordQueueProcessor, config=config_manager)

    # LLM Backends
    huggingface_backend = providers.Singleton(HuggingFaceBackend, model_name="EleutherAI/gpt-neo-1.3B")
    ollama_backend = providers.Singleton(OllamaBackend, default_model="mistral")

    # Dynamic selector (string-based toggle: "huggingface" or "ollama")
    llm_backend_selector = providers.Selector(
        config.local_llm_backend,
        huggingface=huggingface_backend,
        ollama=ollama_backend,
    )

# Global container instance
container = ServiceContainer()

class ServiceContainer:
    def __init__(self):
        self.services = {}

    def register(self, name, service):
        self.services[name] = service

    def get(self, name):
        return self.services.get(name)
