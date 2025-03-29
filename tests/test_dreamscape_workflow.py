import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator

@pytest.fixture
def mock_chat_manager():
    chat_manager = Mock()
    chat_manager.get_all_chat_titles.return_value = [
        {"title": "Project Alpha", "link": "https://chat.openai.com/1"},
        {"title": "System Beta", "link": "https://chat.openai.com/2"},
        {"title": "ChatGPT", "link": "https://chat.openai.com/3"},  # Should be excluded
    ]
    return chat_manager

@pytest.fixture
def mock_response_handler():
    return Mock()

@pytest.fixture
def mock_discord_manager():
    return Mock()

@pytest.fixture
def dreamscape_generator(mock_chat_manager, mock_response_handler, tmp_path):
    return DreamscapeEpisodeGenerator(
        chat_manager=mock_chat_manager,
        response_handler=mock_response_handler,
        output_dir=str(tmp_path),
        discord_manager=None,
        template_dir="dreamscape/templates/"
    )

class TestModelSelection:
    @pytest.mark.parametrize("model", ["gpt-4o", "gpt-3.5-turbo", "gpt-4.5", "gpt-3.5-high"])
    def test_model_availability(self, dreamscape_generator, model):
        url = f"https://chat.openai.com/c/123?model={model}"
        assert model in dreamscape_generator.ensure_model_in_url(url)

    def test_model_append_to_url(self, dreamscape_generator):
        url = "https://chat.openai.com/c/123"
        assert "model=gpt-4o" in dreamscape_generator.ensure_model_in_url(url)

    def test_model_no_duplicate_param(self, dreamscape_generator):
        url = "https://chat.openai.com/c/123?model=gpt-4o"
        result = dreamscape_generator.ensure_model_in_url(url)
        assert result.count("model=gpt-4o") == 1

class TestTemplateDirectory:
    def test_default_template_dir(self, dreamscape_generator):
        assert dreamscape_generator.jinja_env.loader.searchpath[0].endswith("dreamscape/templates/")

    def test_custom_template_dir(self, mock_chat_manager, mock_response_handler, tmp_path):
        custom_dir = "custom/templates"
        generator = DreamscapeEpisodeGenerator(
            chat_manager=mock_chat_manager,
            response_handler=mock_response_handler,
            output_dir=str(tmp_path),
            template_dir=custom_dir
        )
        assert generator.jinja_env.loader.searchpath[0].endswith(custom_dir)

class TestTargetChatSelection:
    def test_chat_titles_population(self, dreamscape_generator, mock_chat_manager):
        titles = [chat["title"] for chat in mock_chat_manager.get_all_chat_titles()]
        assert "Project Alpha" in titles
        assert "System Beta" in titles
        assert len(titles) == 3  # Including excluded chat

    def test_excluded_chat_filtering(self, dreamscape_generator):
        filtered_chats = [
            chat for chat in dreamscape_generator.chat_manager.get_all_chat_titles()
            if not any(ex.lower() in chat["title"].lower() for ex in dreamscape_generator.excluded_chats)
        ]
        assert len(filtered_chats) == 2  # Excluding "ChatGPT"
        assert all("ChatGPT" not in chat["title"] for chat in filtered_chats)

    @pytest.mark.asyncio
    async def test_target_chat_scope(self, dreamscape_generator):
        with patch.object(dreamscape_generator, '_send_prompt_to_chat') as mock_send:
            with patch.object(dreamscape_generator, '_get_latest_response') as mock_response:
                mock_send.return_value = True
                mock_response.return_value = "Test response"
                
                # Test with specific target chat
                entries = dreamscape_generator.generate_dreamscape_episodes(
                    target_chat="Project Alpha"
                )
                assert len(entries) == 1
                assert mock_send.call_count == 2  # Context + Episode generation

class TestGenerateEpisodesLogic:
    @pytest.mark.asyncio
    async def test_headless_mode(self, dreamscape_generator):
        with patch.object(dreamscape_generator.chat_manager, 'driver_manager') as mock_driver:
            mock_driver.get_driver.return_value = MagicMock()
            entries = dreamscape_generator.generate_dreamscape_episodes(headless=True)
            assert mock_driver.get_driver.called_with(headless=True)

    @pytest.mark.asyncio
    async def test_reverse_order(self, dreamscape_generator):
        with patch.object(dreamscape_generator, '_send_prompt_to_chat') as mock_send:
            with patch.object(dreamscape_generator, '_get_latest_response') as mock_response:
                mock_send.return_value = True
                mock_response.return_value = "Test response"
                
                entries = dreamscape_generator.generate_dreamscape_episodes(reverse_order=True)
                
                # Verify chat processing order
                chat_order = [call.args[1] for call in mock_send.call_args_list]
                assert chat_order == sorted(chat_order, reverse=True)

    def test_no_chats_available(self, dreamscape_generator):
        dreamscape_generator.chat_manager.get_all_chat_titles.return_value = []
        entries = dreamscape_generator.generate_dreamscape_episodes()
        assert entries == []

    def test_context_memory_updates(self, dreamscape_generator, tmp_path):
        with patch.object(dreamscape_generator, '_send_prompt_to_chat') as mock_send:
            with patch.object(dreamscape_generator, '_get_latest_response') as mock_response:
                mock_send.return_value = True
                mock_response.return_value = "Test episode content with new protocols"
                
                initial_count = dreamscape_generator.context_memory["episode_count"]
                entries = dreamscape_generator.generate_dreamscape_episodes()
                
                assert dreamscape_generator.context_memory["episode_count"] > initial_count
                assert len(entries) == 2  # Two valid chats processed

    @pytest.mark.parametrize("headless,reverse_order", [
        (True, True),
        (True, False),
        (False, True),
        (False, False)
    ])
    def test_toggle_combinations(self, dreamscape_generator, headless, reverse_order):
        with patch.object(dreamscape_generator, '_send_prompt_to_chat') as mock_send:
            with patch.object(dreamscape_generator, '_get_latest_response') as mock_response:
                mock_send.return_value = True
                mock_response.return_value = "Test response"
                
                entries = dreamscape_generator.generate_dreamscape_episodes(
                    headless=headless,
                    reverse_order=reverse_order
                )
                
                assert isinstance(entries, list)
                if reverse_order:
                    # Verify reverse order processing
                    chat_order = [call.args[1] for call in mock_send.call_args_list]
                    assert chat_order == sorted(chat_order, reverse=True) 