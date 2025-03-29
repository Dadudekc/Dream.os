import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from jinja2 import Environment
import requests
import openai

# Replace direct import with wrapper
from social.social_config_wrapper import get_social_config
from social.log_writer import logger, write_json_log
from social.TaskQueueManager import TaskQueueManager
from utils.SentimentAnalyzer import SentimentAnalyzer
from core.MemoryManager import MemoryManager
from core.AletheiaFeedbackLoopManager import AletheiaFeedbackLoopManager
from core.ReinforcementEngine import ReinforcementEngine

# Constants
PLATFORM = "EngagementAgent"

class EngagementAgent:
    """
    Manages intelligent, automated interactions leveraging AIChatAgent 
    for personalized, context-aware community engagement.
    """

    def __init__(
        self,
        env: Environment,
        platform_strategies: Dict[str, Any],
        memory_manager: Optional[Any] = None,
        reinforcement_engine: Optional[ReinforcementEngine] = None,
        task_queue_manager: Optional[TaskQueueManager] = None,
        ai_chat_agent_model: str = "gpt-4o",
        ai_provider: str = "openai",
        tone: str = "Victor",
        temperature: float = 0.7,
        max_tokens: int = 400,
    ):
        self.env = env
        self.platform_strategies = platform_strategies
        self.task_queue_manager = task_queue_manager
        self.sentiment_analyzer = SentimentAnalyzer()

        # Integrate persistent memory manager
        self.memory_manager = MemoryManager(memory_file="memory/engagement_memory.json")

        # Setup Reinforcement and Sentiment Analysis Engines
        self.reinforcement_engine = ReinforcementEngine() if not reinforcement_engine else reinforcement_engine
        self.sentiment_analyzer = SentimentAnalyzer()

        # Initialize AI Chat Agent
        self.ai_chat_agent = AIChatAgent(
            model=ai_chat_agent,
            provider=ai_provider,
            tone=tone,
            temperature=temperature,
            max_tokens=max_tokens,
            reinforcement_engine=self.reinforcement_engine
        )

        # Setup logging
        self.logger = logging.getLogger("EngagementAgent")
        logger.info(f" EngagementAgent initialized using model '{ai_chat_agent}' via {ai_provider}.")

    # ----------------------------------------
    # Core Methods
    # ----------------------------------------

    def handle_mentions(self, platform: str, use_task_queue: bool = True):
        strategy = self.platform_strategies.get(platform)
        if not strategy:
            logger.error(f" No strategy found for {platform}.")
            return

        mentions = strategy.fetch_recent_mentions()
        logger.info(f" Fetched {len(mentions)} mentions from {platform}.")

        for mention in mentions:
            task_func = lambda m=mention: self._process_mention(platform, m)
            if use_task_queue and self.task_queue_manager:
                self.task_queue_manager.add_task(
                    task_callable=task_func,
                    task_data={"mention_id": mention["id"], "platform": platform},
                    priority=5
                )
            else:
                task_func()

    def proactive_engagement(self, platform: str, topics: List[str], use_task_queue: bool = True):
        strategy = self.platform_strategies.get(platform)
        if not strategy:
            logger.error(f" No strategy found for {platform}.")
            return

        conversations = strategy.search_conversations(topics)
        for convo in conversations:
            if convo.get('already_engaged'):
                continue
            task_func = lambda c=convo: self._process_proactive(platform, c)
            if use_task_queue and self.task_queue_manager:
                self.task_queue_manager.add_task(
                    task_callable=task_func,
                    task_data={"conversation_id": convo["id"], "platform": platform},
                    priority=10
                )
            else:
                task_func()

    # ----------------------------------------
    # Internal Engagement Processing
    # ----------------------------------------

    def _process_mention(self, platform: str, mention: Dict[str, Any]):
        sentiment_data = self.sentiment_analyzer.analyze(mention["text"])
        sentiment = sentiment_data["sentiment"]
        confidence = sentiment_data["confidence"]

        user_history = self.memory_manager.get_user_history(platform, mention['user'])

        reply_content = self.ai_chat_agent.ask(
            prompt=f"Reply to this mention from {mention['user']}: {mention['text']}",
            additional_context=f"User sentiment: {sentiment} ({confidence:.2f}). Previous history: {user_history}",
            metadata={"platform": platform, "type": "mention_reply"}
        )

        success = self.platform_strategies[platform].reply_to_interaction(mention, reply_content)
        self._log_interaction(platform, mention, reply_content, sentiment, confidence, success, proactive=False)

        self.memory_manager.record_interaction(platform, mention['user'], reply_content, sentiment, success)
        self.reinforcement_engine.record_outcome("reply", platform, mention['text'], reply_content, success)

    def _process_proactive(self, platform: str, convo: Dict[str, Any]):
        sentiment_result = self.sentiment_analyzer.analyze(convo['text'])
        sentiment = sentiment_result["sentiment"]
        confidence = sentiment_result["confidence"]

        user_history = self.memory_manager.get_user_history(platform, convo['user'])

        engagement_content = self.ai_chat_agent.ask(
            prompt=f"Engage proactively with user {convo['user']} on topic: {convo['text']}",
            additional_context=f"User sentiment: {sentiment}, confidence: {confidence:.2f}. Interaction history available.",
            metadata={"type": "proactive", "platform": platform}
        )

        success = self.platform_strategies[platform].reply_to_interaction(convo, engagement_content)
        self._log_interaction(platform, convo, engagement_content, sentiment, confidence, success, proactive=True)

        self.memory_manager.record_interaction(platform, convo['user'], engagement_content, sentiment, success)
        self.reinforcement_engine.record_outcome("proactive_engagement", platform, convo['text'], engagement_content, success)

    # ----------------------------------------
    # Logging & Sentiment Analysis
    # ----------------------------------------

    def _log_interaction(
        self,
        platform: str,
        interaction: Dict[str, Any],
        response: str,
        sentiment: str,
        confidence: float,
        success: bool,
        proactive: bool = False
    ):
        interaction_type = "proactive" if proactive else "mention_reply"
        status = "successful" if success else "failed"

        log_payload = {
            "user": interaction.get("user"),
            "interaction_text": interaction.get("text"),
            "response": response,
            "sentiment": sentiment,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }

        write_json_log(
            platform=platform,
            result=status,
            tags=[interaction_type, sentiment],
            ai_output=log_payload,
            event_type="engagement"
        )

        logger.info(f" Logged {interaction_type} interaction on {platform} | Status: {status}")

