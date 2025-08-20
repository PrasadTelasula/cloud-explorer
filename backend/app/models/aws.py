"""
AWS Profile and Credential Models
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
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
    
    # Credential fields (from credentials file)
    credentials: Optional[AWSCredential] = Field(None, description="Associated credentials")
    
    # Additional metadata
    credential_source: Optional[str] = Field(None, description="Source of credentials")
    web_identity_token_file: Optional[str] = Field(None, description="Web identity token file path")
    
    @validator('profile_type', pre=True, always=True)
    def determine_profile_type(cls, v, values):
        """Automatically determine profile type based on fields"""
        if v != AWSProfileType.IAM_USER:
            return v
        
        # Check for SSO profile
        if values.get('sso_start_url'):
            return AWSProfileType.SSO
        
        # Check for role assumption
        if values.get('role_arn'):
            return AWSProfileType.IAM_ROLE
        
        # Check for federated access
        if values.get('web_identity_token_file'):
            return AWSProfileType.FEDERATED
        
        # Check for session credentials
        credentials = values.get('credentials')
        if credentials and hasattr(credentials, 'aws_session_token') and credentials.aws_session_token:
            return AWSProfileType.SESSION
        
        return AWSProfileType.IAM_USER
    
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
