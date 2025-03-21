from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class PromptRequest(BaseModel):
    prompt_text: str = Field(..., description="The prompt text to execute")
    context: Optional[Dict] = Field(default=None, description="Additional context for the prompt")
    model: str = Field(default="gpt-4", description="The model to use for execution")
    temperature: float = Field(default=0.7, ge=0, le=1, description="Temperature for response generation")

class PromptResponse(BaseModel):
    response_text: str = Field(..., description="The generated response")
    execution_time: float = Field(..., description="Time taken to execute the prompt")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(default=None, description="Number of tokens used")

class CycleRequest(BaseModel):
    initial_prompt: str = Field(..., description="The initial prompt to start the cycle")
    max_iterations: int = Field(default=5, ge=1, le=20, description="Maximum number of iterations")
    stop_condition: Optional[str] = Field(default=None, description="Condition to stop the cycle")
    cycle_config: Optional[Dict] = Field(default=None, description="Additional cycle configuration") 