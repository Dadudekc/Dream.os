from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from interfaces.web.dependencies import get_memory_manager, get_current_user

class MemoryStats(BaseModel):
    total_episodes: int
    total_size: int
    last_updated: str

class MemoryStatsResponse(BaseModel):
    status: str = "success"
    stats: MemoryStats

class Episode(BaseModel):
    id: str
    timestamp: str
    content: Dict[str, Any]

class RecentEpisodesResponse(BaseModel):
    status: str = "success"
    episodes: List[Episode]
    count: int

router = APIRouter()

@router.get(
    "/stats",
    response_model=MemoryStatsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def memory_stats(
    memory = Depends(get_memory_manager)
) -> MemoryStatsResponse:
    """
    Get memory system statistics.
    
    Args:
        memory: Injected MemoryManager instance
    
    Returns:
        MemoryStatsResponse with system stats
    """
    try:
        stats = await memory.get_stats()
        return MemoryStatsResponse(stats=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory stats: {str(e)}"
        )

@router.get(
    "/recent",
    response_model=RecentEpisodesResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def recent_episodes(
    count: int = Field(default=5, ge=1, le=100),
    memory = Depends(get_memory_manager)
) -> RecentEpisodesResponse:
    """
    Get recent memory episodes.
    
    Args:
        count: Number of recent episodes to retrieve
        memory: Injected MemoryManager instance
    
    Returns:
        RecentEpisodesResponse with episodes list
    """
    try:
        episodes = await memory.get_recent_episodes(count=count)
        return RecentEpisodesResponse(
            episodes=episodes,
            count=len(episodes)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent episodes: {str(e)}"
        ) 
