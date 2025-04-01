import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from core.EngagementAgent import EngagementAgent


class TestEngagementAgent(unittest.TestCase):

    def setUp(self):
        # Patch logger to suppress logging during tests
        patcher_logger = patch('core.EngagementAgent.logger')
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # Patch write_json_log to prevent file IO
        patcher_write_json_log = patch('core.EngagementAgent.write_json_log')
        self.mock_write_json_log = patcher_write_json_log.start()
        self.addCleanup(patcher_write_json_log.stop)

        # Mock platform strategies
        self.mock_platform_strategy = MagicMock()
        self.platform_strategies = {
            "twitter": self.mock_platform_strategy
        }

        # Mock Jinja2 env
        self.mock_env = MagicMock()

        # Patch SentimentAnalyzer to avoid running NLP
        patcher_sentiment = patch('core.EngagementAgent.SentimentAnalyzer')
        self.mock_sentiment_analyzer_class = patcher_sentiment.start()
        self.addCleanup(patcher_sentiment.stop)

        # Patch AIChatAgent
        patcher_ai_agent = patch('core.EngagementAgent.AIChatAgent')
        self.mock_ai_chat_agent_class = patcher_ai_agent.start()
        self.addCleanup(patcher_ai_agent.stop)

        # Create instance with mocks
        self.agent = EngagementAgent(
            env=self.mock_env,
            platform_strategies=self.platform_strategies,
            memory_manager=MagicMock(),
            reinforcement_engine=MagicMock(),
            task_queue_manager=MagicMock(),
            ai_chat_agent_model="gpt-4o",
        )

        # Setup AI agent and sentiment analyzer mocks
        self.agent.ai_chat_agent = MagicMock()
        self.agent.sentiment_analyzer = MagicMock()

    # --------------------------
    # INIT TEST
    # --------------------------
    def test_initialization(self):
        self.assertEqual(self.agent.platform_strategies, self.platform_strategies)
        self.assertEqual(self.agent.ai_chat_agent.model, "gpt-4o")
        self.mock_logger.info.assert_called()

    # --------------------------
    # HANDLE MENTIONS
    # --------------------------
    def test_handle_mentions_no_strategy(self):
        self.agent.handle_mentions("linkedin")
        self.mock_logger.error.assert_called_with(" No strategy found for linkedin.")

    def test_handle_mentions_with_task_queue(self):
        mention = {"id": "123", "user": "user1", "text": "Hello bot!"}
        self.mock_platform_strategy.fetch_recent_mentions.return_value = [mention]

        self.agent.handle_mentions("twitter", use_task_queue=True)

        self.agent.task_queue_manager.add_task.assert_called_once()
        self.mock_logger.info.assert_any_call(" Fetched 1 mentions from twitter.")

    def test_handle_mentions_direct_processing(self):
        mention = {"id": "123", "user": "user1", "text": "Hey there!"}
        self.mock_platform_strategy.fetch_recent_mentions.return_value = [mention]

        with patch.object(self.agent, "_process_mention") as mock_process:
            self.agent.handle_mentions("twitter", use_task_queue=False)
            mock_process.assert_called_once_with("twitter", mention)

    # --------------------------
    # PROACTIVE ENGAGEMENT
    # --------------------------
    def test_proactive_engagement_no_strategy(self):
        self.agent.proactive_engagement("linkedin", topics=["AI"])
        self.mock_logger.error.assert_called_with(" No strategy found for linkedin.")

    def test_proactive_engagement_with_task_queue(self):
        convo = {"id": "conv_1", "user": "user2", "text": "Talking about AI", "already_engaged": False}
        self.mock_platform_strategy.search_conversations.return_value = [convo]

        self.agent.proactive_engagement("twitter", topics=["AI"], use_task_queue=True)

        self.agent.task_queue_manager.add_task.assert_called_once()

    def test_proactive_engagement_direct_processing(self):
        convo = {"id": "conv_1", "user": "user2", "text": "Discussing bots", "already_engaged": False}
        self.mock_platform_strategy.search_conversations.return_value = [convo]

        with patch.object(self.agent, "_process_proactive") as mock_process:
            self.agent.proactive_engagement("twitter", topics=["bots"], use_task_queue=False)
            mock_process.assert_called_once_with("twitter", convo)

    def test_proactive_engagement_skips_already_engaged(self):
        convo = {"id": "conv_1", "user": "user2", "text": "Discussing bots", "already_engaged": True}
        self.mock_platform_strategy.search_conversations.return_value = [convo]

        self.agent.proactive_engagement("twitter", topics=["bots"], use_task_queue=False)

        self.agent.task_queue_manager.add_task.assert_not_called()

    # --------------------------
    # INTERNAL _PROCESS MENTION
    # --------------------------
    def test_process_mention(self):
        mention = {"id": "123", "user": "user1", "text": "What do you think?"}

        # Mock sentiment and memory data
        self.agent.sentiment_analyzer.analyze.return_value = {"sentiment": "positive", "confidence": 0.85}
        self.agent.memory_manager.get_user_history.return_value = "No history."

        self.agent.ai_chat_agent.ask.return_value = "Thanks for reaching out!"

        # Mock reply success
        self.mock_platform_strategy.reply_to_interaction.return_value = True

        # Act
        self.agent._process_mention("twitter", mention)

        # Assertions
        self.agent.sentiment_analyzer.analyze.assert_called_once_with("What do you think?")
        self.agent.memory_manager.get_user_history.assert_called_once_with("twitter", "user1")
        self.agent.ai_chat_agent.ask.assert_called_once()
        self.agent.memory_manager.record_interaction.assert_called_once()
        self.agent.reinforcement_engine.record_outcome.assert_called_once()
        self.mock_write_json_log.assert_called_once()
        self.mock_logger.info.assert_any_call(" Logged mention_reply interaction on twitter | Status: successful")

    # --------------------------
    # INTERNAL _PROCESS PROACTIVE
    # --------------------------
    def test_process_proactive(self):
        convo = {"id": "conv_1", "user": "user2", "text": "What about AI tools?"}

        # Mock sentiment and memory data
        self.agent.sentiment_analyzer.analyze.return_value = {"sentiment": "neutral", "confidence": 0.7}
        self.agent.memory_manager.get_user_history.return_value = "Previous engagements."

        self.agent.ai_chat_agent.ask.return_value = "Have you tried Victor's platform?"

        # Mock reply success
        self.mock_platform_strategy.reply_to_interaction.return_value = True

        # Act
        self.agent._process_proactive("twitter", convo)

        # Assertions
        self.agent.sentiment_analyzer.analyze.assert_called_once_with("What about AI tools?")
        self.agent.memory_manager.get_user_history.assert_called_once_with("twitter", "user2")
        self.agent.ai_chat_agent.ask.assert_called_once()
        self.agent.memory_manager.record_interaction.assert_called_once()
        self.agent.reinforcement_engine.record_outcome.assert_called_once()
        self.mock_write_json_log.assert_called_once()
        self.mock_logger.info.assert_any_call(" Logged proactive interaction on twitter | Status: successful")

    # --------------------------
    # LOGGING INTERACTION
    # --------------------------
    def test_log_interaction_successful(self):
        interaction = {
            "user": "user1",
            "text": "What's new with Victor?"
        }

        response = "We're building something amazing!"
        sentiment = "positive"
        confidence = 0.9

        self.agent._log_interaction(
            platform="twitter",
            interaction=interaction,
            response=response,
            sentiment=sentiment,
            confidence=confidence,
            success=True,
            proactive=False
        )

        self.mock_write_json_log.assert_called_once_with(
            platform="twitter",
            result="successful",
            tags=["mention_reply", sentiment],
            ai_output={
                "user": "user1",
                "interaction_text": "What's new with Victor?",
                "response": "We're building something amazing!",
                "sentiment": "positive",
                "confidence": 0.9,
                "timestamp": unittest.mock.ANY
            },
            event_type="engagement"
        )

        self.mock_logger.info.assert_called_with(" Logged mention_reply interaction on twitter | Status: successful")


if __name__ == "__main__":
    unittest.main()
