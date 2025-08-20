"""
Cloud Explorer Backend - Main FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.validation import validate_configuration, setup_logging
from app.routers import health


# Setup logging
setup_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Cloud Explorer API...")
    
    # Validate configuration
    if not validate_configuration(settings):
        logger.error("Configuration validation failed")
        raise SystemExit(1)
    
    logger.info(f"Environment: {'development' if settings.is_development else 'production'}")
    logger.info(f"Enabled services: {', '.join(settings.enabled_services)}")
    logger.info(f"API documentation: {'/docs' if settings.ENABLE_OPENAPI_DOCS else 'disabled'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cloud Explorer API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs" if settings.ENABLE_OPENAPI_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_OPENAPI_DOCS else None,
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint with API information"""
    return JSONResponse({
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "environment": "development" if settings.is_development else "production",
        "docs": "/docs" if settings.ENABLE_OPENAPI_DOCS else None,
        "health": "/api/health",
        "enabled_services": settings.enabled_services
    })


@app.get("/config")
async def get_config() -> JSONResponse:
    """Get non-sensitive configuration information"""
    if not settings.is_development:
        return JSONResponse(
            {"error": "Configuration endpoint only available in development"},
            status_code=404
        )
    
    return JSONResponse(settings.to_dict())


if __name__ == "__main__":
    import uvicorn
    
    # Hot-reload configuration in development
    reload_dirs = ["./app"] if settings.is_development else None
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        reload_dirs=reload_dirs,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.is_development
    )
