"""
AWS Session Manager - Robust AWS session management with caching and credential refresh
"""
import os
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import boto3
import botocore.exceptions
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session

from app.models.aws import (
    AWSProfile, 
    AWSSession,
    AWSSessionCache,
    AWSProfileType,
    AWSSessionError,
    AWSSessionExpiredError,
    AWSCredentialError,
    AWSProfileNotFoundError
)
from app.aws.credentials import AWSCredentialsReader
from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSSessionManager:
    """
    Robust AWS session manager with caching and credential refresh
    
    Features:
    - Multiple profile support
    - Credential validation and refresh
    - Session caching with expiration
    - Role assumption support
    - Cross-account access
    - MFA handling
    - SSO support
    - Automatic credential refresh
    """
    
    def __init__(self, credentials_reader: Optional[AWSCredentialsReader] = None):
        """
        Initialize AWS session manager
        
        Args:
            credentials_reader: Optional custom credentials reader
        """
        self.credentials_reader = credentials_reader or AWSCredentialsReader()
        self.session_cache = AWSSessionCache()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self._default_session_duration = 3600  # 1 hour
        
        logger.info("AWS Session Manager initialized")
    
    async def get_session(
        self, 
        profile_name: Optional[str] = None, 
        region: Optional[str] = None,
        force_refresh: bool = False
    ) -> boto3.Session:
        """
        Get or create AWS session for profile
        
        Args:
            profile_name: AWS profile name (defaults to 'default')
            region: AWS region (defaults to profile region or us-east-1)
            force_refresh: Force creation of new session
            
        Returns:
            boto3.Session: Configured AWS session
            
        Raises:
            AWSProfileNotFoundError: If profile doesn't exist
            AWSSessionError: If session creation fails
        """
        profile_name = profile_name or "default"
        
        try:
            # Get profile configuration
            profile = await self._get_profile(profile_name)
            region = region or profile.region or "us-east-1"
            
            # Check cache for existing session
            if not force_refresh:
                cached_session = self.session_cache.get_session_by_profile(profile_name, region)
                if cached_session and not cached_session.should_refresh():
                    logger.debug(f"Using cached session for profile: {profile_name}")
                    return await self._create_boto3_session_from_cached(cached_session)
            
            # Create new session
            logger.info(f"Creating new AWS session for profile: {profile_name}, region: {region}")
            session = await self._create_new_session(profile, region)
            
            # Cache the session
            self.session_cache.add_session(session)
            
            # Create boto3 session
            boto3_session = await self._create_boto3_session_from_cached(session)
            
            # Validate session
            await self._validate_session(boto3_session)
            
            return boto3_session
            
        except Exception as e:
            logger.error(f"Failed to get session for profile {profile_name}: {str(e)}")
            if isinstance(e, (AWSProfileNotFoundError, AWSSessionError)):
                raise
            raise AWSSessionError(f"Session creation failed: {str(e)}") from e
    
    async def get_client(
        self, 
        service_name: str, 
        profile_name: Optional[str] = None, 
        region: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Get AWS service client with session management
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 's3', 'rds')
            profile_name: AWS profile name
            region: AWS region
            **kwargs: Additional client configuration
            
        Returns:
            AWS service client
        """
        session = await self.get_session(profile_name, region)
        return session.client(service_name, **kwargs)
    
    async def get_resource(
        self, 
        service_name: str, 
        profile_name: Optional[str] = None, 
        region: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Get AWS service resource with session management
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 's3', 'rds')
            profile_name: AWS profile name
            region: AWS region
            **kwargs: Additional resource configuration
            
        Returns:
            AWS service resource
        """
        session = await self.get_session(profile_name, region)
        return session.resource(service_name, **kwargs)
    
    async def assume_role(
        self,
        role_arn: str,
        session_name: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        external_id: Optional[str] = None,
        mfa_serial: Optional[str] = None,
        mfa_token: Optional[str] = None,
        source_profile: Optional[str] = None,
        region: Optional[str] = None
    ) -> boto3.Session:
        """
        Assume IAM role and create session
        
        Args:
            role_arn: IAM role ARN to assume
            session_name: Role session name
            duration_seconds: Session duration (default: 3600)
            external_id: External ID for role assumption
            mfa_serial: MFA device ARN
            mfa_token: MFA token code
            source_profile: Source profile for role assumption
            region: AWS region
            
        Returns:
            boto3.Session: Session with assumed role credentials
        """
        session_name = session_name or f"CloudExplorer-{uuid.uuid4().hex[:8]}"
        duration_seconds = duration_seconds or self._default_session_duration
        region = region or "us-east-1"
        
        try:
            # Get source session
            source_session = await self.get_session(source_profile, region)
            sts_client = source_session.client('sts')
            
            # Prepare assume role parameters
            assume_role_params = {
                'RoleArn': role_arn,
                'RoleSessionName': session_name,
                'DurationSeconds': duration_seconds
            }
            
            if external_id:
                assume_role_params['ExternalId'] = external_id
            
            if mfa_serial and mfa_token:
                assume_role_params['SerialNumber'] = mfa_serial
                assume_role_params['TokenCode'] = mfa_token
            
            # Assume role
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: sts_client.assume_role(**assume_role_params)
            )
            
            credentials = response['Credentials']
            
            # Create session with temporary credentials
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=region
            )
            
            # Cache the role session
            aws_session = AWSSession(
                profile_name=f"role-{role_arn.split('/')[-1]}",
                region=region,
                session_id=str(uuid.uuid4()),
                expires_at=credentials['Expiration'].replace(tzinfo=None),
                credentials={
                    'aws_access_key_id': credentials['AccessKeyId'],
                    'aws_secret_access_key': credentials['SecretAccessKey'],
                    'aws_session_token': credentials['SessionToken']
                },
                is_role_session=True,
                role_arn=role_arn
            )
            
            self.session_cache.add_session(aws_session)
            
            logger.info(f"Successfully assumed role: {role_arn}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to assume role {role_arn}: {str(e)}")
            raise AWSSessionError(f"Role assumption failed: {str(e)}") from e
    
    async def validate_credentials(
        self, 
        profile_name: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate AWS credentials for profile
        
        Args:
            profile_name: AWS profile name
            region: AWS region
            
        Returns:
            Dict with validation results
        """
        try:
            session = await self.get_session(profile_name, region)
            sts_client = session.client('sts')
            
            # Get caller identity to validate credentials
            identity = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                sts_client.get_caller_identity
            )
            
            return {
                'valid': True,
                'user_id': identity.get('UserId'),
                'account': identity.get('Account'),
                'arn': identity.get('Arn'),
                'profile': profile_name or 'default',
                'region': region
            }
            
        except Exception as e:
            logger.warning(f"Credential validation failed for {profile_name}: {str(e)}")
            return {
                'valid': False,
                'error': str(e),
                'profile': profile_name or 'default',
                'region': region
            }
    
    async def refresh_credentials(self, profile_name: Optional[str] = None) -> bool:
        """
        Refresh credentials for profile
        
        Args:
            profile_name: AWS profile name
            
        Returns:
            bool: True if refresh successful
        """
        try:
            # Force refresh by getting new session
            await self.get_session(profile_name, force_refresh=True)
            logger.info(f"Credentials refreshed for profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh credentials for {profile_name}: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from cache
        
        Returns:
            int: Number of sessions cleaned up
        """
        count = self.session_cache.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get session manager information
        
        Returns:
            Dict with session manager stats
        """
        return {
            'active_sessions': self.session_cache.active_session_count,
            'total_cached_sessions': len(self.session_cache.sessions),
            'max_sessions': self.session_cache.max_sessions,
            'default_session_duration': self._default_session_duration
        }
    
    async def _get_profile(self, profile_name: str) -> AWSProfile:
        """Get profile configuration"""
        try:
            profiles = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.credentials_reader.read_all_profiles
            )
            
            if profile_name not in profiles.profiles:
                raise AWSProfileNotFoundError(f"Profile '{profile_name}' not found")
            
            return profiles.profiles[profile_name]
            
        except Exception as e:
            if isinstance(e, AWSProfileNotFoundError):
                raise
            raise AWSSessionError(f"Failed to get profile {profile_name}: {str(e)}") from e
    
    async def _create_new_session(self, profile: AWSProfile, region: str) -> AWSSession:
        """Create new AWS session based on profile type"""
        session_id = str(uuid.uuid4())
        
        try:
            if profile.profile_type == AWSProfileType.IAM_ROLE:
                return await self._create_role_session(profile, region, session_id)
            elif profile.profile_type == AWSProfileType.SSO:
                logger.warning(f"⚠️  Creating SSO session for {profile.name} - credentials will NOT be cached for security")
                return await self._create_sso_session(profile, region, session_id)
            else:
                return await self._create_standard_session(profile, region, session_id)
                
        except Exception as e:
            raise AWSSessionError(f"Failed to create session for {profile.name}: {str(e)}") from e
    
    async def _create_standard_session(self, profile: AWSProfile, region: str, session_id: str) -> AWSSession:
        """Create session for standard IAM user profile"""
        if not profile.credentials:
            raise AWSSessionError(f"No credentials found for profile: {profile.name}")
        
        # For standard profiles, set a default expiration of 24 hours
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        return AWSSession(
            profile_name=profile.name,
            region=region,
            session_id=session_id,
            expires_at=expires_at,
            credentials={
                'aws_access_key_id': profile.credentials.aws_access_key_id,
                'aws_secret_access_key': profile.credentials.aws_secret_access_key,
                'aws_session_token': profile.credentials.aws_session_token
            }
        )
    
    async def _create_role_session(self, profile: AWSProfile, region: str, session_id: str) -> AWSSession:
        """Create session for IAM role profile"""
        if not profile.role_arn:
            raise AWSSessionError(f"Role ARN not specified for profile: {profile.name}")
        
        # Assume the role
        session = await self.assume_role(
            role_arn=profile.role_arn,
            source_profile=profile.source_profile,
            duration_seconds=profile.duration_seconds,
            external_id=profile.external_id,
            mfa_serial=profile.mfa_serial,
            region=region
        )
        
        # Get credentials from the session
        credentials = session.get_credentials()
        expires_at = datetime.utcnow() + timedelta(seconds=profile.duration_seconds or self._default_session_duration)
        
        return AWSSession(
            profile_name=profile.name,
            region=region,
            session_id=session_id,
            expires_at=expires_at,
            credentials={
                'aws_access_key_id': credentials.access_key,
                'aws_secret_access_key': credentials.secret_key,
                'aws_session_token': credentials.token
            },
            is_role_session=True,
            role_arn=profile.role_arn
        )
    
    async def _create_sso_session(self, profile: AWSProfile, region: str, session_id: str) -> AWSSession:
        """
        Create session for SSO profile
        
        ⚠️  SECURITY: SSO sessions contain sensitive data - never cache credentials!
        """
        if not profile.sso_start_url or not profile.sso_account_id or not profile.sso_role_name:
            raise AWSSessionError(f"Missing required SSO configuration for profile: {profile.name}")
        
        # SSO sessions should use AWS CLI's cached credentials, not create our own
        # This leverages the existing SSO login session from 'aws sso login'
        try:
            # Create a session using the AWS CLI's SSO credential resolution
            session = boto3.Session(profile_name=profile.name, region_name=region)
            
            # Test the session immediately to ensure SSO login is valid
            sts_client = session.client('sts')
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                sts_client.get_caller_identity
            )
            
            # For SSO sessions, we store minimal metadata only - NO CREDENTIALS
            expires_at = datetime.utcnow() + timedelta(hours=1)  # Conservative expiration
            
            return AWSSession(
                profile_name=profile.name,
                region=region,
                session_id=session_id,
                expires_at=expires_at,
                credentials=None,  # NEVER store SSO credentials
                is_role_session=True,
                role_arn=f"arn:aws:iam::{profile.sso_account_id}:role/{profile.sso_role_name}"
            )
            
        except Exception as e:
            if "SSO" in str(e) or "sso" in str(e):
                raise AWSSessionError(
                    f"SSO session failed for profile {profile.name}. "
                    f"Please run 'aws sso login --profile {profile.name}' first."
                ) from e
            raise AWSSessionError(f"Failed to create SSO session for {profile.name}: {str(e)}") from e
    
    async def _create_boto3_session_from_cached(self, session: AWSSession) -> boto3.Session:
        """
        Create boto3 session from cached session
        
        ⚠️  SECURITY: For SSO sessions, never cache credentials - use profile name instead
        """
        # For SSO sessions, use profile name to leverage AWS CLI's SSO credential cache
        if session.is_role_session and not session.credentials:
            logger.info(f"Creating SSO session using profile name: {session.profile_name}")
            return boto3.Session(
                profile_name=session.profile_name,
                region_name=session.region
            )
        
        # For standard sessions with cached credentials
        if not session.credentials:
            raise AWSSessionError(f"No credentials in cached session: {session.session_id}")
        
        # Handle None session token for standard IAM user credentials
        session_token = session.credentials.get('aws_session_token')
        if session_token == "":
            session_token = None
        
        return boto3.Session(
            aws_access_key_id=session.credentials.get('aws_access_key_id'),
            aws_secret_access_key=session.credentials.get('aws_secret_access_key'),
            aws_session_token=session_token,
            region_name=session.region
        )
    
    async def _validate_session(self, session: boto3.Session) -> None:
        """Validate that session credentials work"""
        try:
            sts_client = session.client('sts')
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                sts_client.get_caller_identity
            )
        except Exception as e:
            raise AWSSessionError(f"Session validation failed: {str(e)}") from e


# Global session manager instance
_session_manager: Optional[AWSSessionManager] = None


def get_session_manager() -> AWSSessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = AWSSessionManager()
    return _session_manager


async def cleanup_sessions_periodically():
    """Background task to clean up expired sessions"""
    while True:
        try:
            session_manager = get_session_manager()
            session_manager.cleanup_expired_sessions()
            await asyncio.sleep(300)  # Clean up every 5 minutes
        except Exception as e:
            logger.error(f"Error in session cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
