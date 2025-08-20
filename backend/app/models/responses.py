"""
API Response Models for Cloud Explorer
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Resource not found",
                "detail": "The requested AWS profile does not exist",
                "timestamp": "2025-08-20T10:30:00Z"
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response model"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "data": {"id": "12345", "status": "active"},
                "timestamp": "2025-08-20T10:30:00Z"
            }
        }


class RootResponse(BaseModel):
    """Root endpoint response model"""
    message: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    environment: str = Field(..., description="Current environment")
    docs: Optional[str] = Field(None, description="Documentation URL")
    health: str = Field(..., description="Health check endpoint")
    enabled_services: List[str] = Field(..., description="List of enabled AWS services")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Cloud Explorer API",
                "version": "1.0.0",
                "description": "Multi-account AWS resource explorer and management tool",
                "environment": "development",
                "docs": "/docs",
                "health": "/api/health",
                "enabled_services": ["ec2", "rds", "s3", "lambda", "vpc"]
            }
        }


class ConfigResponse(BaseModel):
    """Configuration endpoint response model"""
    project_name: str = Field(..., description="Project name")
    version: str = Field(..., description="API version")
    debug: bool = Field(..., description="Debug mode status")
    environment: str = Field(..., description="Current environment")
    aws_region: str = Field(..., description="Default AWS region")
    enabled_services: List[str] = Field(..., description="Enabled AWS services")
    cors_origins: List[str] = Field(..., description="Allowed CORS origins")
    log_level: str = Field(..., description="Current log level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Cloud Explorer API",
                "version": "1.0.0",
                "debug": True,
                "environment": "development",
                "aws_region": "us-east-1",
                "enabled_services": ["ec2", "rds", "s3", "lambda", "vpc"],
                "cors_origins": ["http://localhost:3000"],
                "log_level": "DEBUG"
            }
        }


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model"""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")
    api: Dict[str, Any] = Field(..., description="API information")
    configuration: Dict[str, Any] = Field(..., description="Configuration details")
    
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
