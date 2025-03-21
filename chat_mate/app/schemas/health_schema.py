from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class HealthCheck(BaseModel):
    status: str = Field(..., description="Current system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="API version")
    uptime: str = Field(..., description="System uptime")
    environment: Optional[str] = Field(default=None, description="Current environment")
    services: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )
    memory_usage: Optional[float] = Field(
        default=None,
        description="Current memory usage in MB"
    ) 