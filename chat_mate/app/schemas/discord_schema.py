from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class BotConfig(BaseModel):
    token: str = Field(..., description="Discord bot token")
    channel_id: str = Field(..., description="Target channel ID")
    prefix: str = Field(default="!", description="Command prefix")
    allowed_roles: Optional[List[str]] = Field(default=None, description="Allowed role IDs")
    auto_responses: bool = Field(default=True, description="Enable automatic responses")

class BotStatus(BaseModel):
    status: str = Field(..., description="Current bot status")
    message: str = Field(..., description="Status message")
    uptime: Optional[float] = Field(default=None, description="Bot uptime in seconds")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat timestamp")
    connected_servers: Optional[int] = Field(default=None, description="Number of connected servers")
    active_channels: Optional[List[str]] = Field(default=None, description="Active channel IDs") 