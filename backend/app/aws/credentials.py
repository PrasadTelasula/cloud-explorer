"""
AWS Credentials Reader - Enhanced AWS credential and configuration file parser
"""
import os
import logging
from pathlib import Path
from configparser import ConfigParser, Error as ConfigParserError
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from app.models.aws import (
    AWSProfile, 
    AWSCredential, 
    AWSProfileCollection,
    AWSProfileType,
    AWSCredentialError,
    AWSProfileNotFoundError,
    AWSCredentialFileError,
    AWSProfileValidationError
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSCredentialsReader:
    """
    Enhanced AWS credentials and configuration reader
    
    Handles reading and parsing of:
    - ~/.aws/credentials file
    - ~/.aws/config file
    - Environment variables
    - Profile inheritance and role assumptions
    - MFA and session credentials
    - SSO and federated access patterns
    """
    
    def __init__(self, aws_dir: Optional[Path] = None):
        """
        Initialize AWS credentials reader
        
        Args:
            aws_dir: Custom AWS directory path (defaults to ~/.aws)
        """
        self.aws_dir = aws_dir or self._get_aws_directory()
        self.credentials_file = self.aws_dir / "credentials"
        self.config_file = self.aws_dir / "config"
        
        # Cache for file contents
        self._credentials_cache: Optional[ConfigParser] = None
        self._config_cache: Optional[ConfigParser] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
        
        logger.debug(f"AWS credentials reader initialized with directory: {self.aws_dir}")
    
    @staticmethod
    def _get_aws_directory() -> Path:
        """Get the AWS directory path (cross-platform)"""
        aws_dir = os.environ.get("AWS_CONFIG_FILE")
        if aws_dir:
            return Path(aws_dir).parent
        
        home_dir = Path.home()
        return home_dir / ".aws"
    
    def _should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed"""
        if not self._cache_timestamp:
            return True
        
        return datetime.now() - self._cache_timestamp > self._cache_ttl
    
    def _read_ini_file(self, file_path: Path) -> ConfigParser:
        """
        Read and parse an INI file safely
        
        Args:
            file_path: Path to the INI file
            
        Returns:
            ConfigParser instance
            
        Raises:
            AWSCredentialFileError: If file cannot be read or parsed
        """
        if not file_path.exists():
            logger.debug(f"AWS file not found: {file_path}")
            return ConfigParser()
        
        try:
            config = ConfigParser()
            config.read(file_path, encoding='utf-8')
            logger.debug(f"Successfully read AWS file: {file_path}")
            return config
        except ConfigParserError as e:
            raise AWSCredentialFileError(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            raise AWSCredentialFileError(f"Failed to read {file_path}: {e}")
    
    def _load_credentials_file(self) -> ConfigParser:
        """Load and cache the credentials file"""
        if self._credentials_cache is None or self._should_refresh_cache():
            logger.debug("Loading AWS credentials file")
            self._credentials_cache = self._read_ini_file(self.credentials_file)
            self._cache_timestamp = datetime.now()
        
        return self._credentials_cache
    
    def _load_config_file(self) -> ConfigParser:
        """Load and cache the config file"""
        if self._config_cache is None or self._should_refresh_cache():
            logger.debug("Loading AWS config file")
            self._config_cache = self._read_ini_file(self.config_file)
            self._cache_timestamp = datetime.now()
        
        return self._config_cache
    
    def _parse_credentials_section(self, section_name: str, section_data: Dict[str, str]) -> Optional[AWSCredential]:
        """
        Parse credentials from a section
        
        Args:
            section_name: Name of the section
            section_data: Section data dictionary
            
        Returns:
            AWSCredential instance or None if invalid
        """
        try:
            access_key = section_data.get('aws_access_key_id')
            secret_key = section_data.get('aws_secret_access_key')
            session_token = section_data.get('aws_session_token')
            
            if not access_key or not secret_key:
                logger.debug(f"Profile {section_name} missing required credentials")
                return None
            
            return AWSCredential(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token
            )
        except Exception as e:
            logger.warning(f"Failed to parse credentials for profile {section_name}: {e}")
            return None
    
    def _parse_config_section(self, section_name: str, section_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse configuration from a section
        
        Args:
            section_name: Name of the section
            section_data: Section data dictionary
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Basic configuration
        for key in ['region', 'output']:
            if key in section_data:
                config[key] = section_data[key]
        
        # Role assumption fields
        for key in ['role_arn', 'source_profile', 'external_id', 'mfa_serial', 
                   'role_session_name', 'duration_seconds']:
            if key in section_data:
                if key == 'duration_seconds':
                    try:
                        config[key] = int(section_data[key])
                    except ValueError:
                        logger.warning(f"Invalid duration_seconds for profile {section_name}")
                else:
                    config[key] = section_data[key]
        
        # SSO fields (traditional format)
        for key in ['sso_start_url', 'sso_region', 'sso_account_id', 'sso_role_name']:
            if key in section_data:
                config[key] = section_data[key]
        
        # SSO session field (new format)
        if 'sso_session' in section_data:
            config['sso_session'] = section_data['sso_session']
        
        # Federated fields
        for key in ['web_identity_token_file', 'credential_source']:
            if key in section_data:
                config[key] = section_data[key]
        
        return config
    
    def _resolve_sso_session(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve SSO session references and merge session data
        
        Args:
            profile_data: Profile configuration data
            
        Returns:
            Profile data with resolved SSO session information
        """
        if 'sso_session' not in profile_data:
            return profile_data
        
        sso_session_name = profile_data['sso_session']
        logger.debug(f"Resolving SSO session: {sso_session_name}")
        
        try:
            aws_config = self._load_config_file()
            sso_section_name = f'sso-session {sso_session_name}'
            
            if aws_config.has_section(sso_section_name):
                sso_session_data = dict(aws_config.items(sso_section_name))
                
                # Merge SSO session data into profile data
                # SSO session fields take precedence for sso_start_url and sso_region
                for key in ['sso_start_url', 'sso_region', 'sso_registration_scopes']:
                    if key in sso_session_data:
                        profile_data[key] = sso_session_data[key]
                
                logger.debug(f"Resolved SSO session {sso_session_name}")
            else:
                logger.warning(f"SSO session '{sso_session_name}' not found in config")
        
        except AWSCredentialFileError as e:
            logger.warning(f"Could not resolve SSO session {sso_session_name}: {e}")
        
        return profile_data
    
    def get_profile_names(self) -> List[str]:
        """
        Get all available profile names
        
        Returns:
            List of profile names
        """
        profile_names = set()
        
        # Get profiles from credentials file
        try:
            credentials = self._load_credentials_file()
            profile_names.update(credentials.sections())
        except AWSCredentialFileError:
            pass
        
        # Get profiles from config file
        try:
            config = self._load_config_file()
            for section_name in config.sections():
                if section_name == 'default':
                    profile_names.add('default')
                elif section_name.startswith('profile '):
                    profile_names.add(section_name[8:])  # Remove 'profile ' prefix
        except AWSCredentialFileError:
            pass
        
        return sorted(list(profile_names))
    
    def read_profile(self, profile_name: str) -> AWSProfile:
        """
        Read a specific AWS profile
        
        Args:
            profile_name: Name of the profile to read
            
        Returns:
            AWSProfile instance
            
        Raises:
            AWSProfileNotFoundError: If profile is not found
            AWSCredentialFileError: If files cannot be read
        """
        logger.debug(f"Reading AWS profile: {profile_name}")
        
        # Initialize profile data
        profile_data = {'name': profile_name}
        credentials = None
        
        # Read credentials
        try:
            cred_config = self._load_credentials_file()
            if cred_config.has_section(profile_name):
                cred_section = dict(cred_config.items(profile_name))
                credentials = self._parse_credentials_section(profile_name, cred_section)
        except AWSCredentialFileError as e:
            logger.debug(f"Could not read credentials file: {e}")
        
        # Read configuration
        try:
            aws_config = self._load_config_file()
            
            # Look for profile in config file
            config_section_name = 'default' if profile_name == 'default' else f'profile {profile_name}'
            
            if aws_config.has_section(config_section_name):
                config_section = dict(aws_config.items(config_section_name))
                config_data = self._parse_config_section(profile_name, config_section)
                profile_data.update(config_data)
                
                # Resolve SSO session references
                profile_data = self._resolve_sso_session(profile_data)
        except AWSCredentialFileError as e:
            logger.debug(f"Could not read config file: {e}")
        
        # Check if profile exists
        if not credentials and not any(key in profile_data for key in 
                                     ['role_arn', 'sso_start_url', 'sso_session', 'web_identity_token_file']):
            available_profiles = self.get_profile_names()
            raise AWSProfileNotFoundError(
                f"Profile '{profile_name}' not found. Available profiles: {available_profiles}"
            )
        
        # Add credentials to profile data
        if credentials:
            profile_data['credentials'] = credentials
        
        try:
            profile = AWSProfile(**profile_data)
            logger.debug(f"Successfully parsed profile {profile_name} (type: {profile.profile_type})")
            return profile
        except Exception as e:
            raise AWSProfileValidationError(f"Failed to validate profile {profile_name}: {e}")
    
    def read_all_profiles(self) -> AWSProfileCollection:
        """
        Read all AWS profiles
        
        Returns:
            AWSProfileCollection with all profiles
        """
        logger.info("Reading all AWS profiles")
        collection = AWSProfileCollection()
        
        profile_names = self.get_profile_names()
        logger.debug(f"Found {len(profile_names)} profiles: {profile_names}")
        
        for profile_name in profile_names:
            try:
                profile = self.read_profile(profile_name)
                collection.add_profile(profile)
                logger.debug(f"Added profile {profile_name} to collection")
            except (AWSProfileNotFoundError, AWSProfileValidationError) as e:
                logger.warning(f"Skipping invalid profile {profile_name}: {e}")
                continue
        
        logger.info(f"Successfully loaded {collection.profile_count} profiles "
                   f"({collection.valid_profile_count} valid)")
        return collection
    
    def validate_profile(self, profile_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a specific profile
        
        Args:
            profile_name: Name of the profile to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            profile = self.read_profile(profile_name)
            if profile.is_valid:
                return True, None
            else:
                return False, f"Profile {profile_name} is missing required configuration"
        except AWSProfileNotFoundError as e:
            return False, str(e)
        except (AWSCredentialFileError, AWSProfileValidationError) as e:
            return False, f"Profile validation failed: {e}"
    
    def resolve_profile_chain(self, profile_name: str) -> List[str]:
        """
        Resolve the profile chain for role assumptions
        
        Args:
            profile_name: Starting profile name
            
        Returns:
            List of profile names in the chain
            
        Raises:
            AWSCredentialError: If circular reference detected
        """
        chain = []
        current_profile = profile_name
        visited = set()
        
        while current_profile:
            if current_profile in visited:
                raise AWSCredentialError(f"Circular profile reference detected: {' -> '.join(chain)}")
            
            visited.add(current_profile)
            chain.append(current_profile)
            
            try:
                profile = self.read_profile(current_profile)
                current_profile = profile.source_profile
            except AWSProfileNotFoundError:
                break
        
        return chain
    
    def get_effective_region(self, profile_name: str) -> Optional[str]:
        """
        Get the effective region for a profile (with inheritance)
        
        Args:
            profile_name: Profile name
            
        Returns:
            Region string or None
        """
        try:
            profile_chain = self.resolve_profile_chain(profile_name)
            
            for profile_name in profile_chain:
                profile = self.read_profile(profile_name)
                if profile.region:
                    return profile.region
            
            # Fall back to default region from settings
            return settings.AWS_DEFAULT_REGION
        except Exception as e:
            logger.warning(f"Could not determine region for profile {profile_name}: {e}")
            return settings.AWS_DEFAULT_REGION
    
    def clear_cache(self) -> None:
        """Clear the file cache"""
        self._credentials_cache = None
        self._config_cache = None
        self._cache_timestamp = None
        logger.debug("AWS credentials cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information for debugging"""
        return {
            "cache_enabled": True,
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60,
            "last_cached": self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            "credentials_file_exists": self.credentials_file.exists(),
            "config_file_exists": self.config_file.exists(),
            "aws_directory": str(self.aws_dir)
        }
