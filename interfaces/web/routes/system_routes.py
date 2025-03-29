from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str = "0.1.0"

router = APIRouter()

@router.get(
    "/",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"]
)
async def healthcheck() -> HealthResponse:
    """Check system health status."""
    return HealthResponse(
        status="ok",
        message="Digital Dreamscape API is live"
    ) 