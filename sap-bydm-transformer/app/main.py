from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_config
from app.core.logging_config import setup_logging
from app.api.endpoints import transform, config

# Setup logging
logger = setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="SAP IDoc to BYDM JSON Transformation API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",  # Frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    transform.router,
    prefix=f"{settings.API_PREFIX}/transform",
    tags=["Transformation"]
)

app.include_router(
    config.router,
    prefix=f"{settings.API_PREFIX}/config",
    tags=["Configuration"]
)

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint for health check."""
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running"
    }

@app.on_event("startup")
async def startup_event():
    """
    Validate configuration on startup.
    """
    try:
        validate_config()
        logger.info("Application started with valid configuration")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)

    # uvicorn main:app
    # python main.py