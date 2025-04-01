import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    # Stop the loop before closing it
    if loop.is_running():
        loop.call_soon_threadsafe(loop.stop)
    
    # Only close if not running
    if not loop.is_running():
        loop.close()

@pytest.fixture
async def mock_client():
    client = MagicMock(spec=discord.Client)
    client.user = MagicMock(spec=discord.ClientUser)
    client.user.id = 123456789
    return client

@pytest.mark.asyncio
async def test_simple_setup(mock_client):
    """Simple test to verify our test environment is working."""
    assert mock_client.user.id == 123456789 
