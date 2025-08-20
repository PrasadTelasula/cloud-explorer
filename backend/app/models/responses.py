"""
API Response Models for Cloud Explorer
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

from app.models.aws import AWSProfileType


class AccountStatus(str, Enum):
    """Account validation status"""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class ProfileValidationInfo(BaseModel):
    """Profile validation information"""
    is_valid: bool = Field(..., description="Whether the profile credentials are valid")
    status: AccountStatus = Field(..., description="Account validation status")
    account_id: Optional[str] = Field(None, description="AWS account ID")
    user_arn: Optional[str] = Field(None, description="User or role ARN")
    user_id: Optional[str] = Field(None, description="User ID")
    last_validated: Optional[datetime] = Field(None, description="Last validation timestamp")
    error: Optional[str] = Field(None, description="Validation error message if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "status": "valid",
                "account_id": "123456789012",
                "user_arn": "arn:aws:sts::123456789012:assumed-role/MyRole/session",
                "user_id": "AROABC123DEFGHIJKLMN:session",
                "last_validated": "2025-08-20T10:30:00Z",
                "error": None
            }
        }


class AccountProfile(BaseModel):
    """AWS account profile information"""
    profile_name: str = Field(..., description="AWS profile name")
    profile_type: AWSProfileType = Field(..., description="Type of AWS profile")
    region: Optional[str] = Field(None, description="Default region for this profile")
    output: Optional[str] = Field(None, description="Default output format")
    validation: ProfileValidationInfo = Field(..., description="Profile validation information")
    
    # Role-specific information
    role_arn: Optional[str] = Field(None, description="IAM role ARN (for role profiles)")
    source_profile: Optional[str] = Field(None, description="Source profile for role assumption")
    
    # SSO-specific information
    sso_start_url: Optional[str] = Field(None, description="SSO start URL")
    sso_region: Optional[str] = Field(None, description="SSO region")
    sso_account_id: Optional[str] = Field(None, description="SSO account ID")
    sso_role_name: Optional[str] = Field(None, description="SSO role name")
    sso_session: Optional[str] = Field(None, description="SSO session name")
    
    # Additional metadata
    is_default: bool = Field(False, description="Whether this is the default profile")
    available_regions: List[str] = Field(default_factory=list, description="Available regions for this profile")
    permissions_summary: Optional[Dict[str, Any]] = Field(None, description="High-level permissions summary")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_name": "production",
                "profile_type": "IAM_ROLE",
                "region": "us-east-1",
                "output": "json",
                "validation": {
                    "is_valid": True,
                    "status": "valid",
                    "account_id": "123456789012",
                    "user_arn": "arn:aws:sts::123456789012:assumed-role/ProductionRole/session",
                    "last_validated": "2025-08-20T10:30:00Z"
                },
                "role_arn": "arn:aws:iam::123456789012:role/ProductionRole",
                "source_profile": "default",
                "is_default": False,
                "available_regions": ["us-east-1", "us-west-2", "eu-west-1"],
                "permissions_summary": {
                    "services": ["ec2", "s3", "rds"],
                    "admin_access": False,
                    "read_only": False
                }
            }
        }


class AccountsResponse(BaseModel):
    """Response model for accounts API endpoint"""
    profiles: List[AccountProfile] = Field(..., description="List of AWS profiles with metadata")
    total_profiles: int = Field(..., description="Total number of profiles")
    valid_profiles: int = Field(..., description="Number of profiles with valid credentials")
    invalid_profiles: int = Field(..., description="Number of profiles with invalid credentials")
    default_profile: Optional[str] = Field(None, description="Name of the default profile")
    cache_info: Dict[str, Any] = Field(..., description="Response cache information")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Response generation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profiles": [
                    {
                        "profile_name": "default",
                        "profile_type": "IAM_USER",
                        "region": "us-east-1",
                        "validation": {
                            "is_valid": True,
                            "status": "valid",
                            "account_id": "123456789012"
                        },
                        "is_default": True
                    }
                ],
                "total_profiles": 3,
                "valid_profiles": 2,
                "invalid_profiles": 1,
                "default_profile": "default",
                "cache_info": {
                    "cached": True,
                    "cache_age_seconds": 120,
                    "expires_in_seconds": 780
                },
                "generated_at": "2025-08-20T10:30:00Z"
            }
        }


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
