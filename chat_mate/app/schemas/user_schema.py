from pydantic_settings import BaseSettings

class UserResponse(BaseSettings):
    id: int
    username: str
