from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from interfaces.web.dependencies import get_chat_agent, get_current_user

class ChatProcessingResponse(BaseModel):
    processed_chats: int
    details: List[Dict[str, Any]]
    status: str = "success"

class ChatProcessingRequest(BaseModel):
    max_chats: int = Field(default=5, ge=1, le=100, description="Maximum number of chats to process")

router = APIRouter()

@router.post(
    "/process-chats",
    response_model=ChatProcessingResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def process_chats(
    request: ChatProcessingRequest,
    agent = Depends(get_chat_agent)
) -> ChatProcessingResponse:
    """
    Process a batch of chats using the ChatAgent.
    
    Args:
        request: Contains processing parameters
        agent: Injected ChatAgent instance
    
    Returns:
        ChatProcessingResponse with results
    """
    try:
        result = await agent.process_all_chats(max_chats=request.max_chats)
        return ChatProcessingResponse(
            processed_chats=len(result),
            details=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        ) 
