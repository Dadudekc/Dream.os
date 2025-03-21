from fastapi import APIRouter, Depends
from app.schemas.user_schema import UserResponse
from app.services.user_service import get_all_users

router = APIRouter()

@router.get("/", response_model=list[UserResponse])
async def read_users():
    return get_all_users()
