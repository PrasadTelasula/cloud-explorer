"""
Health check endpoints
"""
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, status, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import rate_limit_health
from app.models.responses import ErrorResponse


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Health status indicator")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-20T10:30:00Z",
                "version": "1.0.0",
                "environment": "development"
            }
        }


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model"""
    status: str = Field(..., description="Health status indicator")
    timestamp: str = Field(..., description="ISO formatted timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")
    api: Dict[str, Any] = Field(..., description="API information")
    configuration: Dict[str, Any] = Field(..., description="Configuration summary")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-20T10:30:00Z",
                "version": "1.0.0",
                "environment": "development",
                "api": {
                    "name": "Cloud Explorer API",
                    "version": "1.0.0",
                    "docs_url": "/docs",
                    "redoc_url": "/redoc"
                },
                "configuration": {
                    "debug": True,
                    "aws_default_region": "us-east-1",
                    "cors_origins": ["http://localhost:3000"]
                }
            }
        }


router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic Health Check",
    description="Returns the basic health status of the API",
    tags=["health"],
    responses={
        200: {
            "description": "API is healthy and responding",
            "model": HealthResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        503: {
            "description": "API is unhealthy or experiencing issues",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_health()
async def health_check(request: Request) -> HealthResponse:
    """
    Basic health check endpoint to verify API is operational.
    
    This endpoint provides a quick way to verify that the API is running and responsive.
    It returns basic information about the service status, version, and environment.
    
    Returns:
        HealthResponse: Basic health status information
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        environment="development" if settings.DEBUG else "production"
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Returns comprehensive health information including system details",
    tags=["health"],
    responses={
        200: {
            "description": "Detailed health information retrieved successfully",
            "model": DetailedHealthResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        503: {
            "description": "API is unhealthy or experiencing issues",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_health()
async def detailed_health_check(request: Request) -> DetailedHealthResponse:
    """
    Comprehensive health check with detailed system information.
    
    This endpoint provides extensive health information including API details,
    configuration summary, and system status. Useful for monitoring and debugging.
    
    Returns:
        DetailedHealthResponse: Comprehensive health and system information
    """
    return DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.VERSION,
        environment="development" if settings.DEBUG else "production",
        api={
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs_url": "/docs",
            "redoc_url": "/redoc"
        },
        configuration={
            "debug": settings.DEBUG,
            "aws_default_region": settings.AWS_DEFAULT_REGION,
            "cors_origins": settings.CORS_ORIGINS
        }
    )
