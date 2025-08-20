"""
Health check endpoints
"""
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str


router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the health status of the API"
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify API is running
    
    Returns:
        HealthResponse: API health status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        environment="development" if settings.DEBUG else "production"
    )


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Returns detailed health information"
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system information
    
    Returns:
        Dict[str, Any]: Detailed health information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "api": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs_url": "/docs",
            "redoc_url": "/redoc"
        },
        "configuration": {
            "debug": settings.DEBUG,
            "aws_default_region": settings.AWS_DEFAULT_REGION,
            "cors_origins": settings.CORS_ORIGINS
        }
    }
