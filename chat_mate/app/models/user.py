from pydantic_settings import BaseSettings

class UserInDB(BaseSettings):
    id: int
    username: str
