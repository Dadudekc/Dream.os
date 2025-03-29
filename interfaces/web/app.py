from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from interfaces.web.routes import chat_router, memory_router, system_router
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Digital Dreamscape API",
        description="Web interface for strategy automation",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(system_router, tags=["System"])
    app.include_router(chat_router, prefix="/chat", tags=["ChatAgent"])
    app.include_router(memory_router, prefix="/memory", tags=["MemoryManager"])

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize resources on startup."""
        logger.info("Starting up Digital Dreamscape API...")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Cleanup resources on shutdown."""
        logger.info("Shutting down Digital Dreamscape API...")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc) -> Dict[str, Any]:
        """Handle HTTP exceptions gracefully."""
        return {
            "status": "error",
            "code": exc.status_code,
            "message": str(exc.detail)
        }

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc) -> Dict[str, Any]:
        """Handle unexpected exceptions gracefully."""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return {
            "status": "error",
            "code": 500,
            "message": "Internal server error"
        }

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("interfaces.web.app:app", host="0.0.0.0", port=8000, reload=True)
