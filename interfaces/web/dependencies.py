from typing import Optional
from fastapi import Depends, HTTPException, status
from social.AIChatAgent import AIChatAgent
from core.memory import MemoryManager
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class Dependencies:
    _chat_agent: Optional[AIChatAgent] = None
    _memory_manager: Optional[MemoryManager] = None

    @classmethod
    @lru_cache()
    def get_chat_agent(cls) -> AIChatAgent:
        """Get or create ChatAgent singleton instance."""
        if cls._chat_agent is None:
            try:
                cls._chat_agent = AIChatAgent()
                logger.info("AIChatAgent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AIChatAgent: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize AIChatAgent"
                )
        return cls._chat_agent

    @classmethod
    @lru_cache()
    def get_memory_manager(cls) -> MemoryManager:
        """Get or create MemoryManager singleton instance."""
        if cls._memory_manager is None:
            try:
                cls._memory_manager = MemoryManager()
                logger.info("MemoryManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MemoryManager: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize MemoryManager"
                )
        return cls._memory_manager

# Dependency injection functions
async def get_chat_agent() -> AIChatAgent:
    """Async dependency for ChatAgent."""
    return Dependencies.get_chat_agent()

async def get_memory_manager() -> MemoryManager:
    """Async dependency for MemoryManager."""
    return Dependencies.get_memory_manager()

# Optional: JWT Authentication dependency
async def get_current_user(authorization: str = Depends(lambda: None)):
    """
    JWT authentication dependency - placeholder.
    In production, implement proper JWT validation here.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return True 
