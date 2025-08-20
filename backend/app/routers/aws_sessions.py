"""
AWS Session Management API endpoints
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.aws.session_manager import get_session_manager, AWSSessionManager
from app.models.aws import AWSSessionError, AWSProfileNotFoundError
from app.core.security import rate_limit_default

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/aws/sessions",
    tags=["AWS Sessions"],
    responses={
        404: {"description": "Profile not found"},
        500: {"description": "Session management error"}
    }
)


@router.get("/validate", 
           summary="Validate AWS credentials",
           description="Validate AWS credentials for a specific profile and region")
@rate_limit_default()
async def validate_credentials(
    request,
    profile_name: Optional[str] = Query(None, description="AWS profile name"),
    region: Optional[str] = Query(None, description="AWS region"),
    session_manager: AWSSessionManager = Depends(get_session_manager)
) -> Dict[str, Any]:
    """
    Validate AWS credentials for a profile
    
    Args:
        profile_name: AWS profile name (defaults to 'default')
        region: AWS region (defaults to profile region)
        
    Returns:
        Validation results with account information
    """
    try:
        result = await session_manager.validate_credentials(profile_name, region)
        
        if result['valid']:
            logger.info(f"Credentials validated for profile: {profile_name}")
        else:
            logger.warning(f"Credential validation failed for profile: {profile_name}")
            
        return result
        
    except AWSProfileNotFoundError as e:
        logger.error(f"Profile not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Credential validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/refresh",
            summary="Refresh AWS credentials", 
            description="Force refresh of cached credentials for a profile")
@rate_limit_default()
async def refresh_credentials(
    request,
    profile_name: Optional[str] = Query(None, description="AWS profile name"),
    session_manager: AWSSessionManager = Depends(get_session_manager)
) -> Dict[str, Any]:
    """
    Refresh cached credentials for a profile
    
    Args:
        profile_name: AWS profile name (defaults to 'default')
        
    Returns:
        Refresh operation result
    """
    try:
        success = await session_manager.refresh_credentials(profile_name)
        
        if success:
            logger.info(f"Credentials refreshed for profile: {profile_name}")
            return {
                "success": True,
                "message": f"Credentials refreshed for profile: {profile_name or 'default'}",
                "profile": profile_name or 'default'
            }
        else:
            logger.warning(f"Failed to refresh credentials for profile: {profile_name}")
            return {
                "success": False,
                "message": f"Failed to refresh credentials for profile: {profile_name or 'default'}",
                "profile": profile_name or 'default'
            }
            
    except AWSProfileNotFoundError as e:
        logger.error(f"Profile not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Credential refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@router.post("/assume-role",
            summary="Assume IAM role",
            description="Assume an IAM role and create a temporary session")
@rate_limit_default()
async def assume_role(
    request,
    role_arn: str = Query(..., description="IAM role ARN to assume"),
    session_name: Optional[str] = Query(None, description="Role session name"),
    duration_seconds: Optional[int] = Query(3600, description="Session duration in seconds"),
    external_id: Optional[str] = Query(None, description="External ID for role assumption"),
    mfa_serial: Optional[str] = Query(None, description="MFA device ARN"),
    mfa_token: Optional[str] = Query(None, description="MFA token code"),
    source_profile: Optional[str] = Query(None, description="Source profile for role assumption"),
    region: Optional[str] = Query(None, description="AWS region"),
    session_manager: AWSSessionManager = Depends(get_session_manager)
) -> Dict[str, Any]:
    """
    Assume an IAM role and create a temporary session
    
    Args:
        role_arn: IAM role ARN to assume
        session_name: Optional role session name
        duration_seconds: Session duration (default: 3600 seconds)
        external_id: Optional external ID
        mfa_serial: Optional MFA device ARN
        mfa_token: Optional MFA token code
        source_profile: Source profile for role assumption
        region: AWS region
        
    Returns:
        Role assumption result
    """
    try:
        # Validate duration
        if duration_seconds and (duration_seconds < 900 or duration_seconds > 43200):
            raise HTTPException(
                status_code=400, 
                detail="Duration must be between 900 and 43200 seconds (15 minutes to 12 hours)"
            )
        
        # Validate MFA parameters
        if mfa_serial and not mfa_token:
            raise HTTPException(
                status_code=400,
                detail="MFA token required when MFA serial is provided"
            )
        
        session = await session_manager.assume_role(
            role_arn=role_arn,
            session_name=session_name,
            duration_seconds=duration_seconds,
            external_id=external_id,
            mfa_serial=mfa_serial,
            mfa_token=mfa_token,
            source_profile=source_profile,
            region=region
        )
        
        # Get credentials from session for response
        credentials = session.get_credentials()
        
        logger.info(f"Successfully assumed role: {role_arn}")
        
        return {
            "success": True,
            "message": f"Successfully assumed role: {role_arn}",
            "role_arn": role_arn,
            "session_name": session_name,
            "region": region or "us-east-1",
            "expires_at": (session.get_credentials().token_expires_at if hasattr(session.get_credentials(), 'token_expires_at') else None),
            "credentials": {
                "access_key_id": credentials.access_key,
                "secret_access_key": "***REDACTED***",  # Never expose secret in response
                "session_token": "***REDACTED***"  # Never expose token in response
            }
        }
        
    except AWSSessionError as e:
        logger.error(f"Role assumption failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Role assumption error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Role assumption failed: {str(e)}")


@router.get("/info",
           summary="Get session manager information",
           description="Get session manager statistics and information")
@rate_limit_default()
async def get_session_info(
    request,
    session_manager: AWSSessionManager = Depends(get_session_manager)
) -> Dict[str, Any]:
    """
    Get session manager information and statistics
    
    Returns:
        Session manager information
    """
    try:
        info = session_manager.get_session_info()
        
        return {
            "session_manager": info,
            "endpoints": {
                "validate": "/api/aws/sessions/validate",
                "refresh": "/api/aws/sessions/refresh",
                "assume_role": "/api/aws/sessions/assume-role",
                "cleanup": "/api/aws/sessions/cleanup"
            },
            "features": [
                "Credential validation",
                "Session caching",
                "Automatic credential refresh", 
                "Role assumption",
                "Cross-account access",
                "Session expiration management"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get session info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")


@router.post("/cleanup",
            summary="Clean up expired sessions",
            description="Manually trigger cleanup of expired sessions")
@rate_limit_default()
async def cleanup_sessions(
    request,
    session_manager: AWSSessionManager = Depends(get_session_manager)
) -> Dict[str, Any]:
    """
    Manually trigger cleanup of expired sessions
    
    Returns:
        Cleanup operation result
    """
    try:
        cleaned_count = session_manager.cleanup_expired_sessions()
        
        logger.info(f"Session cleanup completed: {cleaned_count} sessions removed")
        
        return {
            "success": True,
            "message": "Session cleanup completed",
            "cleaned_sessions": cleaned_count,
            "remaining_sessions": session_manager.session_cache.active_session_count
        }
        
    except Exception as e:
        logger.error(f"Session cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
