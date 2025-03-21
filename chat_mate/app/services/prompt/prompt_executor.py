from datetime import datetime
from typing import Optional
from app.schemas.prompt_schema import PromptRequest, PromptResponse
from app.core.dreamscape import DreamscapeService

class PromptExecutor:
    def __init__(self, dreamscape_service: DreamscapeService):
        self.dreamscape = dreamscape_service

    async def execute(self, request: PromptRequest) -> PromptResponse:
        start_time = datetime.utcnow()
        
        response = await self.dreamscape.execute_prompt(
            prompt=request.prompt_text,
            context=request.context,
            model=request.model,
            temperature=request.temperature
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return PromptResponse(
            response_text=response.text,
            execution_time=execution_time,
            model_used=request.model,
            tokens_used=response.tokens_used if hasattr(response, 'tokens_used') else None
        ) 