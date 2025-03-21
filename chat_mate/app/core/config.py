from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "My FastAPI Project"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./test.db"
    
    class Config:
        case_sensitive = True

settings = Settings()
