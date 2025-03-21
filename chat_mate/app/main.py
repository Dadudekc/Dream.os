from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import users, prompts, discord, health

app = FastAPI(
    title="Dreamscape API",
    description="API for Dreamscape Beta",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(discord.router, prefix="/api/v1/discord", tags=["discord"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
