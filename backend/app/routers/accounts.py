"""
AWS Accounts API endpoint
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.aws.session_manager import get_session_manager, AWSSessionManager
from app.aws.client_factory import get_client_factory, AWSServiceClientFactory
from app.models.aws import AWSSessionError, AWSProfileNotFoundError, AWSProfile, AWSProfileType
from app.models.responses import (
    AccountsResponse, 
    AccountProfile, 
    ProfileValidationInfo, 
    AccountStatus,
    ErrorResponse
)
from app.core.security import rate_limit_default

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Accounts"],
    responses={
        404: {"description": "Profile not found"},
        500: {"description": "Account API error"}
    }
)

# Cache for accounts response (15-minute cache as specified)
_accounts_cache: Dict[str, Any] = {}
CACHE_DURATION_SECONDS = 900  # 15 minutes


async def _get_profile_validation(
    profile_name: str, 
    session_manager: AWSSessionManager,
    client_factory: AWSServiceClientFactory
) -> ProfileValidationInfo:
    """
    Get validation information for a specific profile
    
    Args:
        profile_name: AWS profile name
        session_manager: Session manager instance
        client_factory: Client factory instance
        
    Returns:
        ProfileValidationInfo with validation details
    """
    try:
        # Validate credentials using session manager
        validation_result = await session_manager.validate_credentials(profile_name)
        
        if validation_result['valid']:
            return ProfileValidationInfo(
                is_valid=True,
                status=AccountStatus.VALID,
                account_id=validation_result.get('account'),
                user_arn=validation_result.get('arn'),
                user_id=validation_result.get('user_id'),
                last_validated=datetime.utcnow(),
                error=None
            )
        else:
            return ProfileValidationInfo(
                is_valid=False,
                status=AccountStatus.INVALID,
                account_id=None,
                user_arn=None,
                user_id=None,
                last_validated=datetime.utcnow(),
                error=validation_result.get('error', 'Unknown validation error')
            )
            
    except AWSProfileNotFoundError as e:
        return ProfileValidationInfo(
            is_valid=False,
            status=AccountStatus.INVALID,
            account_id=None,
            user_arn=None,
            user_id=None,
            last_validated=datetime.utcnow(),
            error=f"Profile not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error validating profile {profile_name}: {str(e)}")
        return ProfileValidationInfo(
            is_valid=False,
            status=AccountStatus.UNKNOWN,
            account_id=None,
            user_arn=None,
            user_id=None,
            last_validated=datetime.utcnow(),
            error=f"Validation error: {str(e)}"
        )


async def _get_available_regions(
    profile_name: str,
    client_factory: AWSServiceClientFactory
) -> List[str]:
    """
    Get available regions for a profile
    
    Args:
        profile_name: AWS profile name
        client_factory: Client factory instance
        
    Returns:
        List of available regions
    """
    try:
        # Get all regions using EC2 (available in all regions)
        regions = await client_factory.get_all_regions()
        return regions[:10]  # Return first 10 regions to avoid overwhelming response
    except Exception as e:
        logger.warning(f"Could not get regions for profile {profile_name}: {str(e)}")
        return ['us-east-1', 'us-west-2', 'eu-west-1']  # Fallback regions


async def _get_permissions_summary(
    profile_name: str,
    validation_info: ProfileValidationInfo,
    client_factory: AWSServiceClientFactory
) -> Optional[Dict[str, Any]]:
    """
    Get basic permissions summary for a profile
    
    Args:
        profile_name: AWS profile name
        validation_info: Profile validation information
        client_factory: Client factory instance
        
    Returns:
        Permissions summary or None if cannot determine
    """
    if not validation_info.is_valid:
        return None
        
    try:
        # Test basic service access
        accessible_services = []
        
        # Test S3 access
        try:
            s3_client = await client_factory.get_client('s3', profile_name, 'us-east-1')
            await asyncio.get_event_loop().run_in_executor(
                None, s3_client.list_buckets
            )
            accessible_services.append('s3')
        except:
            pass
        
        # Test EC2 access
        try:
            ec2_client = await client_factory.get_client('ec2', profile_name, 'us-east-1')
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: ec2_client.describe_regions(MaxResults=1)
            )
            accessible_services.append('ec2')
        except:
            pass
        
        # Test IAM access (admin-like permissions)
        admin_access = False
        try:
            iam_client = await client_factory.get_client('iam', profile_name, 'us-east-1')
            await asyncio.get_event_loop().run_in_executor(
                None, iam_client.get_account_summary
            )
            admin_access = True
        except:
            pass
        
        return {
            "services": accessible_services,
            "admin_access": admin_access,
            "read_only": len(accessible_services) > 0 and not admin_access,
            "service_count": len(accessible_services)
        }
        
    except Exception as e:
        logger.warning(f"Could not determine permissions for profile {profile_name}: {str(e)}")
        return {
            "services": [],
            "admin_access": False,
            "read_only": False,
            "service_count": 0,
            "error": "Could not determine permissions"
        }


async def _build_account_profile(
    aws_profile: AWSProfile,
    session_manager: AWSSessionManager,
    client_factory: AWSServiceClientFactory,
    is_default: bool = False
) -> AccountProfile:
    """
    Build comprehensive account profile information
    
    Args:
        aws_profile: AWS profile data
        session_manager: Session manager instance
        client_factory: Client factory instance
        is_default: Whether this is the default profile
        
    Returns:
        AccountProfile with complete information
    """
    # Get validation information
    validation_info = await _get_profile_validation(
        aws_profile.name, session_manager, client_factory
    )
    
    # Get available regions
    available_regions = await _get_available_regions(
        aws_profile.name, client_factory
    )
    
    # Get permissions summary
    permissions_summary = await _get_permissions_summary(
        aws_profile.name, validation_info, client_factory
    )
    
    return AccountProfile(
        profile_name=aws_profile.name,
        profile_type=aws_profile.profile_type,
        region=aws_profile.region,
        output=aws_profile.output,
        validation=validation_info,
        role_arn=aws_profile.role_arn,
        source_profile=aws_profile.source_profile,
        sso_start_url=aws_profile.sso_start_url,
        sso_region=aws_profile.sso_region,
        sso_account_id=aws_profile.sso_account_id,
        sso_role_name=aws_profile.sso_role_name,
        sso_session=aws_profile.sso_session,
        is_default=is_default,
        available_regions=available_regions,
        permissions_summary=permissions_summary
    )


@router.get("/accounts",
           summary="List AWS accounts and profiles",
           description="Get comprehensive information about all available AWS profiles with metadata, validation status, and permissions",
           response_model=AccountsResponse,
           responses={
               200: {"description": "Successful response with accounts information"},
               500: {"description": "Internal server error", "model": ErrorResponse}
           })
@rate_limit_default()
async def list_accounts(
    request: Request,
    include_invalid: bool = Query(True, description="Include profiles with invalid credentials"),
    validate_credentials: bool = Query(True, description="Perform credential validation"),
    include_permissions: bool = Query(False, description="Include basic permissions summary (slower)"),
    use_cache: bool = Query(True, description="Use cached response if available"),
    session_manager: AWSSessionManager = Depends(get_session_manager),
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> AccountsResponse:
    """
    List all available AWS accounts and profiles with comprehensive metadata
    
    This endpoint provides detailed information about AWS profiles including:
    - Profile names, types, and configuration
    - Credential validation status and account information
    - Available regions and basic permissions summary
    - Role and SSO configuration details
    
    Args:
        include_invalid: Whether to include profiles with invalid credentials
        validate_credentials: Whether to validate credentials (set to False for faster response)
        include_permissions: Whether to include permissions summary (slower but more detailed)
        use_cache: Whether to use cached response (15-minute cache)
        
    Returns:
        AccountsResponse with comprehensive profile information
    """
    try:
        # Check cache first
        cache_key = f"accounts:{include_invalid}:{validate_credentials}:{include_permissions}"
        
        if use_cache and cache_key in _accounts_cache:
            cache_entry = _accounts_cache[cache_key]
            cache_age = (datetime.utcnow() - cache_entry['timestamp']).total_seconds()
            
            if cache_age < CACHE_DURATION_SECONDS:
                logger.info(f"Returning cached accounts response (age: {cache_age:.1f}s)")
                response = cache_entry['data']
                response.cache_info = {
                    "cached": True,
                    "cache_age_seconds": int(cache_age),
                    "expires_in_seconds": int(CACHE_DURATION_SECONDS - cache_age)
                }
                return response
        
        logger.info("Generating fresh accounts response...")
        
        # Get all profiles from credentials reader
        profiles_data = session_manager.credentials_reader.read_all_profiles()
        profile_list = []
        
        # Process each profile
        for profile_name, aws_profile in profiles_data.profiles.items():
            try:
                # Skip credential validation if requested
                if not validate_credentials:
                    validation_info = ProfileValidationInfo(
                        is_valid=True,
                        status=AccountStatus.UNKNOWN,
                        account_id=None,
                        user_arn=None,
                        user_id=None,
                        last_validated=None,
                        error="Validation skipped"
                    )
                    
                    account_profile = AccountProfile(
                        profile_name=aws_profile.name,
                        profile_type=aws_profile.profile_type,
                        region=aws_profile.region,
                        output=aws_profile.output,
                        validation=validation_info,
                        role_arn=aws_profile.role_arn,
                        source_profile=aws_profile.source_profile,
                        sso_start_url=aws_profile.sso_start_url,
                        sso_region=aws_profile.sso_region,
                        sso_account_id=aws_profile.sso_account_id,
                        sso_role_name=aws_profile.sso_role_name,
                        sso_session=aws_profile.sso_session,
                        is_default=(profile_name == "default"),
                        available_regions=['us-east-1', 'us-west-2', 'eu-west-1'],
                        permissions_summary=None
                    )
                else:
                    # Build comprehensive profile with validation
                    account_profile = await _build_account_profile(
                        aws_profile, 
                        session_manager, 
                        client_factory if include_permissions else None,
                        is_default=(profile_name == "default")
                    )
                
                # Include invalid profiles if requested
                if include_invalid or account_profile.validation.is_valid:
                    profile_list.append(account_profile)
                    
            except Exception as e:
                logger.error(f"Error processing profile {profile_name}: {str(e)}")
                if include_invalid:
                    # Create minimal profile entry for errored profiles
                    error_profile = AccountProfile(
                        profile_name=profile_name,
                        profile_type=aws_profile.profile_type,
                        region=aws_profile.region,
                        output=aws_profile.output,
                        validation=ProfileValidationInfo(
                            is_valid=False,
                            status=AccountStatus.UNKNOWN,
                            account_id=None,
                            user_arn=None,
                            user_id=None,
                            last_validated=datetime.utcnow(),
                            error=f"Processing error: {str(e)}"
                        ),
                        is_default=(profile_name == "default"),
                        available_regions=[],
                        permissions_summary=None
                    )
                    profile_list.append(error_profile)
        
        # Calculate statistics
        valid_profiles = len([p for p in profile_list if p.validation.is_valid])
        invalid_profiles = len(profile_list) - valid_profiles
        default_profile = next((p.profile_name for p in profile_list if p.is_default), None)
        
        # Create response
        response = AccountsResponse(
            profiles=profile_list,
            total_profiles=len(profile_list),
            valid_profiles=valid_profiles,
            invalid_profiles=invalid_profiles,
            default_profile=default_profile,
            cache_info={
                "cached": False,
                "cache_age_seconds": 0,
                "expires_in_seconds": CACHE_DURATION_SECONDS
            },
            generated_at=datetime.utcnow()
        )
        
        # Cache the response
        _accounts_cache[cache_key] = {
            'data': response,
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"Generated accounts response: {len(profile_list)} profiles ({valid_profiles} valid, {invalid_profiles} invalid)")
        return response
        
    except Exception as e:
        logger.error(f"Error in accounts endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve accounts information: {str(e)}"
        )


@router.delete("/accounts/cache",
              summary="Clear accounts cache",
              description="Manually clear the accounts response cache")
@rate_limit_default()
async def clear_accounts_cache(request: Request) -> Dict[str, Any]:
    """
    Clear the accounts response cache
    
    Returns:
        Cache clearing results
    """
    try:
        cleared_entries = len(_accounts_cache)
        _accounts_cache.clear()
        
        return {
            "message": f"Successfully cleared {cleared_entries} cache entries",
            "cleared_entries": cleared_entries,
            "cache_duration_seconds": CACHE_DURATION_SECONDS
        }
        
    except Exception as e:
        logger.error(f"Error clearing accounts cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")
