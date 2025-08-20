"""
AWS Profiles API endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, status, Request, HTTPException
from pydantic import BaseModel, Field

from app.aws.credentials import AWSCredentialsReader
from app.models.aws import AWSCredentialError, AWSProfileNotFoundError
from app.models.responses import ErrorResponse
from app.core.security import rate_limit_default

router = APIRouter()


class ProfileInfo(BaseModel):
    """Profile information response model"""
    name: str = Field(..., description="Profile name")
    profile_type: str = Field(..., description="Profile type")
    region: str = Field(None, description="AWS region")
    is_valid: bool = Field(..., description="Whether profile is valid")
    requires_mfa: bool = Field(..., description="Whether profile requires MFA")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "default",
                "profile_type": "iam_user",
                "region": "us-east-1",
                "is_valid": True,
                "requires_mfa": False
            }
        }


class ProfileListResponse(BaseModel):
    """Profile list response model"""
    profiles: List[ProfileInfo] = Field(..., description="List of AWS profiles")
    total_count: int = Field(..., description="Total number of profiles")
    valid_count: int = Field(..., description="Number of valid profiles")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profiles": [
                    {
                        "name": "default",
                        "profile_type": "iam_user", 
                        "region": "us-east-1",
                        "is_valid": True,
                        "requires_mfa": False
                    }
                ],
                "total_count": 1,
                "valid_count": 1
            }
        }


class ProfileDetailResponse(BaseModel):
    """Detailed profile response model"""
    name: str = Field(..., description="Profile name")
    profile_type: str = Field(..., description="Profile type")
    region: str = Field(None, description="AWS region")
    is_valid: bool = Field(..., description="Whether profile is valid")
    requires_mfa: bool = Field(..., description="Whether profile requires MFA")
    configuration: Dict[str, Any] = Field(..., description="Profile configuration (excluding sensitive data)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "production",
                "profile_type": "iam_role",
                "region": "us-west-2",
                "is_valid": True,
                "requires_mfa": True,
                "configuration": {
                    "role_arn": "arn:aws:iam::123456789012:role/ProductionRole",
                    "source_profile": "default",
                    "mfa_serial": "arn:aws:iam::123456789012:mfa/user"
                }
            }
        }


@router.get(
    "/profiles",
    response_model=ProfileListResponse,
    status_code=status.HTTP_200_OK,
    summary="List AWS Profiles",
    description="List all available AWS profiles with basic information",
    tags=["aws-profiles"],
    responses={
        200: {
            "description": "AWS profiles retrieved successfully",
            "model": ProfileListResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        500: {
            "description": "Error reading AWS profiles",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_default()
async def list_aws_profiles(request: Request) -> ProfileListResponse:
    """
    List all available AWS profiles from ~/.aws/credentials and ~/.aws/config
    
    This endpoint discovers and returns information about all configured AWS profiles
    without exposing sensitive credential information.
    
    Returns:
        ProfileListResponse: List of AWS profiles with metadata
    """
    try:
        credentials_reader = AWSCredentialsReader()
        profile_collection = credentials_reader.read_all_profiles()
        
        profiles = []
        for profile_name in profile_collection.list_profiles():
            profile = profile_collection.get_profile(profile_name)
            if profile:
                # Get effective region
                effective_region = credentials_reader.get_effective_region(profile_name)
                
                profiles.append(ProfileInfo(
                    name=profile.name,
                    profile_type=profile.profile_type.value,
                    region=effective_region,
                    is_valid=profile.is_valid,
                    requires_mfa=profile.requires_mfa
                ))
        
        return ProfileListResponse(
            profiles=profiles,
            total_count=profile_collection.profile_count,
            valid_count=profile_collection.valid_profile_count
        )
        
    except AWSCredentialError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading AWS profiles: {str(e)}"
        )


@router.get(
    "/profiles/{profile_name}",
    response_model=ProfileDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AWS Profile Details",
    description="Get detailed information about a specific AWS profile",
    tags=["aws-profiles"],
    responses={
        200: {
            "description": "AWS profile details retrieved successfully",
            "model": ProfileDetailResponse,
        },
        404: {
            "description": "AWS profile not found",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        500: {
            "description": "Error reading AWS profile",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_default()
async def get_aws_profile(request: Request, profile_name: str) -> ProfileDetailResponse:
    """
    Get detailed information about a specific AWS profile.
    
    This endpoint returns comprehensive information about an AWS profile including
    its configuration and validation status, without exposing sensitive credentials.
    
    Args:
        profile_name: Name of the AWS profile to retrieve
    
    Returns:
        ProfileDetailResponse: Detailed profile information
    """
    try:
        credentials_reader = AWSCredentialsReader()
        profile = credentials_reader.read_profile(profile_name)
        
        # Get effective region  
        effective_region = credentials_reader.get_effective_region(profile_name)
        
        # Get profile configuration without sensitive data
        config = profile.to_dict(include_credentials=False)
        
        # Remove internal fields
        config.pop('name', None)
        config.pop('credentials', None)
        
        return ProfileDetailResponse(
            name=profile.name,
            profile_type=profile.profile_type.value,
            region=effective_region,
            is_valid=profile.is_valid,
            requires_mfa=profile.requires_mfa,
            configuration=config
        )
        
    except AWSProfileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AWSCredentialError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading AWS profile: {str(e)}"
        )
