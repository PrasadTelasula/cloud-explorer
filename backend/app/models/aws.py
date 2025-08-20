"""
AWS Profile and Credential Models
"""
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator


class AWSProfileType(str, Enum):
    """AWS profile types"""
    IAM_USER = "iam_user"
    IAM_ROLE = "iam_role"
    SSO = "sso"
    FEDERATED = "federated"
    SESSION = "session"


class AWSCredential(BaseModel):
    """AWS credential information from ~/.aws/credentials"""
    aws_access_key_id: str = Field(..., description="AWS access key ID")
    aws_secret_access_key: str = Field(..., description="AWS secret access key")
    aws_session_token: Optional[str] = Field(None, description="AWS session token for temporary credentials")
    
    class Config:
        # Ensure sensitive data is not logged or serialized by default
        json_encoders = {
            str: lambda v: "***REDACTED***" if any(key in str(v).lower() for key in ["secret", "token"]) else v
        }


class AWSProfile(BaseModel):
    """AWS profile configuration from ~/.aws/config"""
    name: str = Field(..., description="Profile name")
    region: Optional[str] = Field(None, description="Default AWS region")
    output: Optional[str] = Field(None, description="Default output format")
    profile_type: AWSProfileType = Field(AWSProfileType.IAM_USER, description="Profile type")
    
    def __init__(self, **data):
        # Auto-detect profile type before calling parent constructor
        if 'profile_type' not in data or data.get('profile_type') == AWSProfileType.IAM_USER:
            # Check for SSO profile (traditional or session format)
            if data.get('sso_start_url') or data.get('sso_session'):
                data['profile_type'] = AWSProfileType.SSO
            # Check for role assumption
            elif data.get('role_arn'):
                data['profile_type'] = AWSProfileType.IAM_ROLE
            # Check for federated access
            elif data.get('web_identity_token_file'):
                data['profile_type'] = AWSProfileType.FEDERATED
            # Check for session credentials
            elif data.get('credentials') and hasattr(data['credentials'], 'aws_session_token') and data['credentials'].aws_session_token:
                data['profile_type'] = AWSProfileType.SESSION
        
        super().__init__(**data)
    
    # IAM Role fields
    role_arn: Optional[str] = Field(None, description="IAM role ARN to assume")
    source_profile: Optional[str] = Field(None, description="Source profile for role assumption")
    external_id: Optional[str] = Field(None, description="External ID for role assumption")
    mfa_serial: Optional[str] = Field(None, description="MFA device ARN")
    role_session_name: Optional[str] = Field(None, description="Role session name")
    duration_seconds: Optional[int] = Field(None, description="Session duration in seconds")
    
    # SSO fields
    sso_start_url: Optional[str] = Field(None, description="SSO start URL")
    sso_region: Optional[str] = Field(None, description="SSO region")
    sso_account_id: Optional[str] = Field(None, description="SSO account ID")
    sso_role_name: Optional[str] = Field(None, description="SSO role name")
    sso_session: Optional[str] = Field(None, description="SSO session name (new format)")
    
    # Credential fields (from credentials file)
    credentials: Optional[AWSCredential] = Field(None, description="Associated credentials")
    
    # Additional metadata
    credential_source: Optional[str] = Field(None, description="Source of credentials")
    web_identity_token_file: Optional[str] = Field(None, description="Web identity token file path")
    
    @property
    def is_valid(self) -> bool:
        """Check if profile has valid configuration"""
        if self.profile_type == AWSProfileType.IAM_USER:
            return self.credentials is not None
        elif self.profile_type == AWSProfileType.IAM_ROLE:
            return bool(self.role_arn and self.source_profile)
        elif self.profile_type == AWSProfileType.SSO:
            return bool(self.sso_start_url and self.sso_region and 
                       self.sso_account_id and self.sso_role_name)
        elif self.profile_type == AWSProfileType.FEDERATED:
            return bool(self.web_identity_token_file)
        else:
            return True
    
    @property
    def requires_mfa(self) -> bool:
        """Check if profile requires MFA"""
        return bool(self.mfa_serial)
    
    def to_dict(self, include_credentials: bool = False) -> Dict[str, Any]:
        """Convert profile to dictionary, optionally including credentials"""
        data = self.dict(exclude={'credentials'} if not include_credentials else set())
        if include_credentials and self.credentials:
            data['credentials'] = self.credentials.dict()
        return data


class AWSProfileCollection(BaseModel):
    """Collection of AWS profiles with utility methods"""
    profiles: Dict[str, AWSProfile] = Field(default_factory=dict, description="Profile dictionary")
    default_profile: str = Field(default="default", description="Default profile name")
    
    def add_profile(self, profile: AWSProfile) -> None:
        """Add a profile to the collection"""
        self.profiles[profile.name] = profile
    
    def get_profile(self, name: Optional[str] = None) -> Optional[AWSProfile]:
        """Get a profile by name, defaults to default profile"""
        profile_name = name or self.default_profile
        return self.profiles.get(profile_name)
    
    def list_profiles(self) -> List[str]:
        """List all profile names"""
        return list(self.profiles.keys())
    
    def list_valid_profiles(self) -> List[str]:
        """List only valid profiles"""
        return [name for name, profile in self.profiles.items() if profile.is_valid]
    
    def get_profiles_by_type(self, profile_type: AWSProfileType) -> List[AWSProfile]:
        """Get profiles by type"""
        return [profile for profile in self.profiles.values() 
                if profile.profile_type == profile_type]
    
    @property
    def profile_count(self) -> int:
        """Get total number of profiles"""
        return len(self.profiles)
    
    @property
    def valid_profile_count(self) -> int:
        """Get number of valid profiles"""
        return len(self.list_valid_profiles())


class AWSCredentialError(Exception):
    """Base exception for AWS credential operations"""
    pass


class AWSProfileNotFoundError(AWSCredentialError):
    """Raised when requested profile is not found"""
    pass


class AWSCredentialFileError(AWSCredentialError):
    """Raised when there are issues reading credential files"""
    pass


class AWSProfileValidationError(AWSCredentialError):
    """Raised when profile validation fails"""
    pass


class AWSSessionError(AWSCredentialError):
    """Raised when there are issues with AWS session management"""
    pass


class AWSSessionExpiredError(AWSSessionError):
    """Raised when AWS session has expired"""
    pass


class AWSSession(BaseModel):
    """
    AWS session information with caching and expiration
    
    ⚠️  SECURITY WARNING: 
    - Never store SSO credentials - use profile names instead
    - Credentials are only cached for standard IAM user sessions
    - SSO sessions rely on AWS CLI's secure credential cache
    """
    profile_name: str = Field(..., description="Profile name for this session")
    region: str = Field(..., description="AWS region")
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")
    credentials: Optional[Dict[str, Optional[str]]] = Field(None, description="Cached credentials (IAM users only - NEVER for SSO)")
    is_role_session: bool = Field(False, description="Whether this is an assumed role or SSO session")
    role_arn: Optional[str] = Field(None, description="ARN of assumed role")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            str: lambda v: "***REDACTED***" if any(key in str(v).lower() for key in ["secret", "token", "key"]) else v
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time until session expires"""
        if not self.expires_at:
            return None
        remaining = self.expires_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def should_refresh(self, threshold_minutes: int = 15) -> bool:
        """Check if session should be refreshed based on threshold"""
        if not self.expires_at:
            return False
        threshold = timedelta(minutes=threshold_minutes)
        time_remaining = self.time_until_expiry
        return time_remaining is not None and time_remaining <= threshold


class AWSSessionCache(BaseModel):
    """Cache for AWS sessions with automatic cleanup"""
    sessions: Dict[str, AWSSession] = Field(default_factory=dict, description="Active sessions")
    max_sessions: int = Field(100, description="Maximum number of cached sessions")
    
    def add_session(self, session: AWSSession) -> None:
        """Add session to cache"""
        # Clean expired sessions first
        self.cleanup_expired()
        
        # If at max capacity, remove oldest session
        if len(self.sessions) >= self.max_sessions:
            oldest_key = min(self.sessions.keys(), 
                           key=lambda k: self.sessions[k].created_at)
            del self.sessions[oldest_key]
        
        self.sessions[session.session_id] = session
    
    def get_session(self, session_id: str) -> Optional[AWSSession]:
        """Get session from cache"""
        session = self.sessions.get(session_id)
        if session and session.is_expired:
            del self.sessions[session_id]
            return None
        return session
    
    def get_session_by_profile(self, profile_name: str, region: str) -> Optional[AWSSession]:
        """Get active session for profile and region"""
        for session in self.sessions.values():
            if (session.profile_name == profile_name and 
                session.region == region and 
                not session.is_expired):
                return session
        return None
    
    def remove_session(self, session_id: str) -> bool:
        """Remove session from cache"""
        return self.sessions.pop(session_id, None) is not None
    
    def cleanup_expired(self) -> int:
        """Remove expired sessions from cache"""
        expired_ids = [sid for sid, session in self.sessions.items() 
                      if session.is_expired]
        for sid in expired_ids:
            del self.sessions[sid]
        return len(expired_ids)
    
    @property
    def active_session_count(self) -> int:
        """Get count of active (non-expired) sessions"""
        return len([s for s in self.sessions.values() if not s.is_expired])
