import pytest
from unittest.mock import MagicMock, patch
from core.AIOutputLogAnalyzer import AIOutputLogAnalyzer

# Fixtures to mock dependencies
@pytest.fixture
def mock_unified_logger():
    return MagicMock()

@pytest.fixture
def mock_file_manager():
    return MagicMock()

@pytest.fixture
def mock_discord_manager():
    return MagicMock()

@pytest.fixture
def analyzer(mock_unified_logger, mock_file_manager, mock_discord_manager):
    with patch("core.AIOutputLogAnalyzer.UnifiedLoggingAgent", return_value=mock_unified_logger), \
         patch("core.AIOutputLogAnalyzer.FileManager", return_value=mock_file_manager):

        mock_file_manager.load_file.return_value = {
            "recent_responses": [],
            "user_profiles": {},
            "platform_memories": {},
            "trending_tags": []
        }

        return AIOutputLogAnalyzer(
            log_dir="dummy_logs",
            verbose=True,
            discord_manager=mock_discord_manager
        )

# -------------------------
# TEST: Initialization
# -------------------------
def test_init(analyzer):
    assert analyzer.verbose is True
    assert isinstance(analyzer.discord_manager, MagicMock)
    assert analyzer.context_memory == {
        "recent_responses": [],
        "user_profiles": {},
        "platform_memories": {},
        "trending_tags": []
    }

# -------------------------
# TEST: _validate_log
# -------------------------
def test_validate_log_valid_entry(analyzer):
    entry = {
        "timestamp": "2025-03-21T12:00:00",
        "message": "Sample AI output",
        "metadata": {
            "result": "successful",
            "user": "user1",
            "platform": "discord"
        },
        "tags": ["tag1", "tag2"]
    }

    result = analyzer._validate_log(entry)

    assert result == {
        "timestamp": "2025-03-21T12:00:00",
        "result": "successful",
        "tags": ["tag1", "tag2"],
        "ai_output": "Sample AI output",
        "user": "user1",
        "platform": "discord"
    }

def test_validate_log_invalid_entry(analyzer):
    result = analyzer._validate_log("invalid_entry")
    assert result is None

# -------------------------
# TEST: iterate_logs
# -------------------------
def test_iterate_logs(analyzer, mock_unified_logger):
    mock_unified_logger.get_logs.return_value = [
        {
            "timestamp": "2025-03-21T12:00:00",
            "message": "Valid output",
            "metadata": {"result": "successful", "user": "user1", "platform": "discord"},
            "tags": ["tagA"]
        },
        "invalid_log"
    ]

    logs = list(analyzer.iterate_logs())

    assert len(logs) == 1
    assert logs[0]["result"] == "successful"
    assert logs[0]["ai_output"] == "Valid output"

# -------------------------
# TEST: extract_context_from_logs
# -------------------------
def test_extract_context_from_logs(analyzer, mock_unified_logger):
    # Mock the log data
    mock_unified_logger.get_logs.return_value = [
        {
            "timestamp": "2025-03-21T12:00:00",
            "message": "Response 1",
            "metadata": {"result": "successful", "user": "userA", "platform": "discord"},
            "tags": ["tag1"]
        }
    ]

    analyzer.extract_context_from_logs(max_entries=10)

    context = analyzer.context_memory

    assert len(context["recent_responses"]) == 1
    assert context["user_profiles"]["userA"]["last_interactions"][0]["text"] == "Response 1"
    assert context["platform_memories"]["discord"][0] == "Response 1"
    assert context["trending_tags"][0][0] == "tag1"

# -------------------------
# TEST: get_recent_context
# -------------------------
def test_get_recent_context(analyzer):
    analyzer.context_memory["recent_responses"] = [
        {"text": "First Response", "timestamp": "2025-03-21T10:00:00"},
        {"text": "Second Response", "timestamp": "2025-03-21T12:00:00"}
    ]

    result = analyzer.get_recent_context(limit=1)
    assert "- Second Response..." in result

# -------------------------
# TEST: get_user_context
# -------------------------
def test_get_user_context(analyzer):
    analyzer.context_memory["user_profiles"] = {
        "userX": {
            "last_interactions": [
                {"text": "UserX Response", "timestamp": "2025-03-21T10:00:00"}
            ]
        }
    }

    result = analyzer.get_user_context("userX")
    assert "- UserX Response..." in result

# -------------------------
# TEST: summarize
# -------------------------
def test_summarize(analyzer, mock_unified_logger):
    mock_unified_logger.get_logs.return_value = [
        {
            "timestamp": "2025-03-21T12:00:00",
            "message": "AI response",
            "metadata": {"result": "successful", "user": "userA", "platform": "discord"},
            "tags": ["tag1"]
        }
    ]

    summary = analyzer.summarize()
    assert summary["total_entries"] == 1
    assert summary["successful"] == 1
    assert summary["avg_response_length"] > 0
    assert summary["top_users"]["userA"] == 1
    assert summary["tag_distribution"]["tag1"] == 1

# -------------------------
# TEST: export_summary_report
# -------------------------
def test_export_summary_report(analyzer, mock_unified_logger):
    report_data = {"total_entries": 1}

    mock_unified_logger.log.return_value = "/path/to/summary.json"

    filepath = analyzer.export_summary_report(report_data)

    assert filepath == "/path/to/summary.json"
    mock_unified_logger.log.assert_called_once()

# -------------------------
# TEST: send_discord_report (async)
# -------------------------
@pytest.mark.asyncio
async def test_send_discord_report(analyzer, mock_discord_manager):
    analyzer.summarize = MagicMock(return_value={"total_entries": 1})
    mock_discord_manager.render_message.return_value = "Report Message"
    mock_discord_manager.send_message = MagicMock()

    await analyzer.send_discord_report()

    mock_discord_manager.render_message.assert_called_once()
    mock_discord_manager.send_message.assert_called_once()

# -------------------------
# TEST: send_discord_report_sync
# -------------------------
def test_send_discord_report_sync(analyzer):
    analyzer.send_discord_report = MagicMock()

    analyzer.send_discord_report_sync()

    analyzer.send_discord_report.assert_called_once()
