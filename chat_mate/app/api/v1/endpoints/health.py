from fastapi import APIRouter
from app.schemas.health_schema import HealthCheck
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
    Returns basic system health metrics
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "uptime": "TODO: implement uptime tracking"
    }
