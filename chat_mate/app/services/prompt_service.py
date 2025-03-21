import asyncio
from datetime import datetime
from typing import Dict, Optional
from app.schemas.prompt_schema import PromptRequest, PromptResponse, CycleRequest
from app.core.dreamscape import DreamscapeService  # Your existing service

class PromptService:
    def __init__(self):
        self.dreamscape = DreamscapeService()

    async def execute_prompt(self, request: PromptRequest) -> PromptResponse:
        start_time = datetime.utcnow()
        
        # Execute prompt using your existing DreamscapeService
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

    async def start_prompt_cycle(self, request: CycleRequest) -> PromptResponse:
        start_time = datetime.utcnow()
        
        # Execute prompt cycle using your existing DreamscapeService
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

# Create a singleton instance
prompt_service = PromptService() 