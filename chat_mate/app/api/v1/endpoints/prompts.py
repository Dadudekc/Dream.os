from fastapi import APIRouter, HTTPException
from app.schemas.prompt_schema import PromptRequest, PromptResponse, CycleRequest
from app.services.prompt_service import prompt_service

router = APIRouter()

@router.post("/execute", response_model=PromptResponse)
async def execute_prompt(request: PromptRequest):
    """Execute a single prompt"""
    try:
        return await prompt_service.execute_prompt(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cycle", response_model=PromptResponse)
async def start_cycle(request: CycleRequest):
    """Start a prompt cycle"""
    try:
        return await prompt_service.start_prompt_cycle(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 