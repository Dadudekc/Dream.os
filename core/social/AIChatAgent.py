import logging
import requests
import openai
from typing import Optional, Dict, Any
from datetime import datetime
from core.memory import MemoryManager
from core.PromptEngine import PromptEngine

# Constants
PLATFORM = "AIChatAgent"

logger = logging.getLogger(__name__)

class AIChatAgent:
    """
    AIChatAgent: Unified AI assistant optimized for context-rich, personalized interactions in Victor's voice.
    Supports OpenAI, local LLMs (Ollama), automatic ChatGPT thread creation, persistent memory logging, and fine-tuning dataset preparation.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        tone: str = "Victor",
        temperature: float = 0.7,
        max_tokens: int = 400,
        provider: str = "openai",
        reinforcement_engine: Optional[Any] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.model = model
        self.tone = tone
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider.lower()
        self.reinforcement_engine = reinforcement_engine
        self.memory_manager = memory_manager or MemoryManager()

        # Lazy import social config
        from social.social_config_wrapper import get_social_config
        social_config = get_social_config()
        self.ollama_host = social_config.get_env("OLLAMA_HOST") or "http://127.0.0.1:11434"

        if self.provider == "openai":
            openai.api_key = social_config.get_env("OPENAI_API_KEY")

        logger.info(f" AIChatAgent initialized with model: {self.model}, provider: {self.provider}")

    def ask(
        self,
        prompt: str,
        additional_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        create_new_chat_thread: bool = False,
        interaction_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Generates a personalized response. Optionally creates and logs a new ChatGPT thread.
        If `create_new_chat_thread` is True and an `interaction_id` is provided,
        a new conversation thread is initialized. Subsequent interactions with the same ID will be appended.
        """
        full_prompt = self._build_prompt(prompt, additional_context, metadata)

        if create_new_chat_thread and interaction_id:
            self._initialize_chat_thread(interaction_id, full_prompt)

        logger.info(f"🧠 Sending prompt to [{self.provider.upper()}] model [{self.model}]")
        try:
            response = (
                self._ask_openai(full_prompt)
                if self.provider == "openai"
                else self._ask_ollama(full_prompt)
            )
            self._log_interaction(prompt, response, metadata, interaction_id)
            if self.reinforcement_engine:
                self.reinforcement_engine.record_interaction(
                    input_context=full_prompt,
                    response=response,
                    metadata=metadata
                )
            return response
        except Exception as e:
            logger.error(f" AIChatAgent error ({self.provider}): {e}")
            # Lazy import log_writer
            from social.log_writer import write_json_log
            write_json_log(
                platform=PLATFORM,
                status="failed",
                tags=["ai_response", "error", self.provider],
                ai_output=str(e)
            )
            return None

    def _ask_openai(self, prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are {self.tone}. Respond introspectively, clearly, and strategically in Victor's style."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        content = response['choices'][0]['message']['content'].strip()
        logger.info(" OpenAI response received")
        return content

    def _ask_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        content = response.json().get("response", "").strip()
        if not content:
            raise ValueError("No content received from Ollama.")
        logger.info(" Ollama response received")
        return content

    def _build_prompt(self, user_prompt: str, additional_context: Optional[str], metadata: Optional[Dict[str, Any]]) -> str:
        context_segments = [user_prompt]
        if additional_context:
            context_segments.append(f"Additional context:\n{additional_context}")
        if metadata:
            context_segments.append("Metadata insights:")
            context_segments.extend([f"- {k}: {v}" for k, v in metadata.items()])
        return "\n\n".join(context_segments)

    def _initialize_chat_thread(self, interaction_id: str, initial_prompt: str):
        """
        Initializes a new conversation thread by recording the initial prompt.
        This creates a dedicated log entry in persistent memory for future message appending.
        """
        self.memory_manager.record_interaction(
            platform="ChatThread",
            username=interaction_id,
            response=f"Initial prompt: {initial_prompt}",
            sentiment="n/a",
            success=True,
            interaction_id=interaction_id,
            chatgpt_url=None
        )
        logger.info(f" New ChatGPT thread initialized for interaction_id: {interaction_id}")

    def append_to_chat_thread(self, interaction_id: str, message: str, role: str = "assistant"):
        """
        Appends a new message to an existing conversation thread in memory.
        This helps create a complete interaction history that can be referenced later.
        """
        appended_message = f"{role.upper()} message: {message}"
        self.memory_manager.record_interaction(
            platform="ChatThread",
            username=interaction_id,
            response=appended_message,
            sentiment="n/a",
            success=True,
            interaction_id=interaction_id,
            chatgpt_url=None
        )
        logger.info(f" Appended message to chat thread {interaction_id}")

    def _log_interaction(self, prompt: str, response: str, metadata: Optional[Dict[str, Any]], interaction_id: Optional[str]):
        """
        Logs interactions persistently and prepares datasets for future fine-tuning.
        """
        log_data = {
            "provider": self.provider,
            "model": self.model,
            "prompt": prompt,
            "response": response,
            "metadata": metadata or {},
            "interaction_id": interaction_id
        }
        self.memory_manager.record_interaction(
            platform="ChatThread",
            username=interaction_id or "general",
            response=response,
            sentiment="n/a",
            success=True,
            interaction_id=interaction_id,
            chatgpt_url=None
        )
        # Lazy import log_writer
        from social.log_writer import write_json_log
        write_json_log(
            platform=PLATFORM,
            status="successful",
            tags=["ai_response", self.provider],
            ai_output=log_data
        )
        logger.info(" Interaction logged successfully for fine-tuning & memory updates.") 