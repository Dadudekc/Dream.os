from dependency_injector import containers, providers

# Standard services
from core.PromptResponseHandler import PromptResponseHandler
from config.ConfigManager import ConfigManager
from core.services.discord.DiscordQueueProcessor import DiscordQueueProcessor

# Import factories
from core.micro_factories.prompt_factory import PromptFactory
from core.micro_factories.orchestrator_factory import OrchestratorFactory

# Local LLM Backends
from core.llm_backends.huggingface_backend import HuggingFaceBackend
from core.llm_backends.ollama_backend import OllamaBackend

class ServiceContainer(containers.DeclarativeContainer):
    """Container for service dependencies."""

    config = providers.Configuration()

    # Core services
    config_manager = providers.Singleton(ConfigManager)
    
    # Use factories to create services and avoid circular dependencies
    prompt_manager = providers.Singleton(
        PromptFactory.create_prompt_manager
    )
    
    orchestrator = providers.Singleton(
        OrchestratorFactory.create_orchestrator,
        config_manager=config_manager,
        prompt_service=prompt_manager
    )
    
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
