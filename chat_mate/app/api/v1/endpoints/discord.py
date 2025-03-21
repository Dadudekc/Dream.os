from fastapi import APIRouter, HTTPException
from app.schemas.discord_schema import BotConfig, BotStatus
from app.services.discord import discord_service

router = APIRouter()

@router.post("/launch", response_model=BotStatus)
async def launch_bot(config: BotConfig):
    """Launch Discord bot"""
    try:
        await discord_service.bot_manager.launch(config)
        return await discord_service.status_monitor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop", response_model=BotStatus)
async def stop_bot():
    """Stop Discord bot"""
    try:
        await discord_service.bot_manager.stop()
        return await discord_service.status_monitor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=BotStatus)
async def get_bot_status():
    """Get Discord bot status"""
    try:
        return await discord_service.status_monitor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 