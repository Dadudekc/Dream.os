from datetime import datetime
from typing import Optional
from app.schemas.prompt_schema import CycleRequest, PromptResponse
from app.core.dreamscape import DreamscapeService

class CycleManager:
    def __init__(self, dreamscape_service: DreamscapeService):
        self.dreamscape = dreamscape_service

    async def start_cycle(self, request: CycleRequest) -> PromptResponse:
        start_time = datetime.utcnow()
        
        cycle_response = await self.dreamscape.execute_cycle(
            initial_prompt=request.initial_prompt,
            max_iterations=request.max_iterations,
            stop_condition=request.stop_condition,
            config=request.cycle_config
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return PromptResponse(
            response_text=cycle_response.final_response,
            execution_time=execution_time,
            model_used="gpt-4",  # Update based on your configuration
            tokens_used=cycle_response.total_tokens if hasattr(cycle_response, 'total_tokens') else None
        ) 