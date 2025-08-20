"""
AWS Service Client Factory - Reusable AWS service client factory with regional management and retry logic
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List, Set, Union, TypeVar, Generic
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import boto3
import botocore.exceptions
from botocore.config import Config
from botocore.retries import adaptive
from botocore.exceptions import (
    ClientError, 
    NoCredentialsError, 
    TokenRetrievalError,
    EndpointConnectionError,
    ConnectionError as BotocoreConnectionError
)

from app.models.aws import AWSSessionError, AWSProfileNotFoundError
from app.aws.session_manager import AWSSessionManager, get_session_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Type variable for boto3 clients
ClientType = TypeVar('ClientType')


class AWSServiceType(str, Enum):
    """Supported AWS service types"""
    # Compute services
    EC2 = "ec2"
    LAMBDA = "lambda"
    ECS = "ecs"
    EKS = "eks"
    BATCH = "batch"
    
    # Storage services
    S3 = "s3"
    EBS = "ebs"
    EFS = "efs"
    FSX = "fsx"
    
    # Database services
    RDS = "rds"
    DYNAMODB = "dynamodb"
    REDSHIFT = "redshift"
    DOCUMENTDB = "docdb"
    NEPTUNE = "neptune"
    
    # Networking services
    VPC = "ec2"  # VPC is part of EC2
    ELB = "elbv2"
    ROUTE53 = "route53"
    CLOUDFRONT = "cloudfront"
    
    # Security & Identity
    IAM = "iam"
    STS = "sts"
    SECRETS_MANAGER = "secretsmanager"
    KMS = "kms"
    
    # Monitoring & Logging
    CLOUDWATCH = "cloudwatch"
    CLOUDTRAIL = "cloudtrail"
    X_RAY = "xray"
    
    # Application services
    SNS = "sns"
    SQS = "sqs"
    SES = "ses"
    
    # Analytics
    ATHENA = "athena"
    GLUE = "glue"
    KINESIS = "kinesis"
    
    # Machine Learning
    SAGEMAKER = "sagemaker"
    COMPREHEND = "comprehend"
    
    # Management & Governance
    CLOUDFORMATION = "cloudformation"
    CONFIG = "config"
    ORGANIZATIONS = "organizations"
    
    # Cost Management
    COST_EXPLORER = "ce"
    BUDGETS = "budgets"


class RegionAvailability(str, Enum):
    """Region availability status for services"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class AWSClientCacheEntry:
    """Cache entry for AWS clients"""
    
    def __init__(
        self,
        client: Any,
        created_at: datetime,
        profile_name: str,
        region: str,
        service_name: str,
        ttl_minutes: int = 60
    ):
        self.client = client
        self.created_at = created_at
        self.profile_name = profile_name
        self.region = region
        self.service_name = service_name
        self.expires_at = created_at + timedelta(minutes=ttl_minutes)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() >= self.expires_at
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for this entry"""
        return f"{self.profile_name}:{self.region}:{self.service_name}"


class AWSServiceClientFactory:
    """
    Reusable AWS service client factory with regional management and retry logic
    
    Features:
    - Regional client management and caching
    - Intelligent retry logic with exponential backoff
    - Service availability checking per region
    - Connection pooling and reuse
    - Automatic credential refresh
    - Thread-safe client creation
    - Comprehensive error handling
    """
    
    def __init__(self, session_manager: Optional[AWSSessionManager] = None):
        """
        Initialize AWS service client factory
        
        Args:
            session_manager: Optional session manager instance
        """
        self.session_manager = session_manager or get_session_manager()
        self.client_cache: Dict[str, AWSClientCacheEntry] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.service_availability_cache: Dict[str, Dict[str, RegionAvailability]] = {}
        self.max_cached_clients = 200
        
        # Default boto3 config with retry logic
        self.default_config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            connect_timeout=10,
            read_timeout=60
        )
        
        logger.info("AWS Service Client Factory initialized")
    
    async def get_client(
        self,
        service_name: Union[str, AWSServiceType],
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
        config: Optional[Config] = None,
        force_refresh: bool = False,
        **kwargs
    ) -> Any:
        """
        Get AWS service client with caching and retry logic
        
        Args:
            service_name: AWS service name or AWSServiceType enum
            profile_name: AWS profile name
            region: AWS region
            config: Optional boto3 Config object
            force_refresh: Force refresh of cached client
            **kwargs: Additional client configuration
            
        Returns:
            AWS service client
            
        Raises:
            AWSServiceError: If service is not available in region
            AWSSessionError: If session creation fails
        """
        # Convert enum to string if needed
        if isinstance(service_name, AWSServiceType):
            service_name = service_name.value
        
        profile_name = profile_name or "default"
        region = region or "us-east-1"
        
        # Generate cache key
        cache_key = f"{profile_name}:{region}:{service_name}"
        
        # Check cache first (unless force refresh)
        if not force_refresh and cache_key in self.client_cache:
            cache_entry = self.client_cache[cache_key]
            if not cache_entry.is_expired:
                logger.debug(f"Using cached client for {service_name} in {region}")
                return cache_entry.client
            else:
                # Remove expired entry
                del self.client_cache[cache_key]
        
        # Check service availability in region
        availability = await self.check_service_availability(service_name, region)
        if availability == RegionAvailability.UNAVAILABLE:
            raise AWSServiceError(
                f"Service '{service_name}' is not available in region '{region}'"
            )
        
        try:
            # Get session from session manager
            session = await self.session_manager.get_session(profile_name, region)
            
            # Merge configurations
            final_config = self._merge_configs(config, kwargs)
            
            # Create client with retry logic
            client = await self._create_client_with_retry(
                session, service_name, region, final_config
            )
            
            # Cache the client
            self._cache_client(client, profile_name, region, service_name)
            
            logger.info(f"Created {service_name} client for profile '{profile_name}' in region '{region}'")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create {service_name} client: {str(e)}")
            raise AWSServiceError(f"Client creation failed: {str(e)}") from e
    
    async def get_resource(
        self,
        service_name: Union[str, AWSServiceType],
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
        config: Optional[Config] = None,
        **kwargs
    ) -> Any:
        """
        Get AWS service resource
        
        Args:
            service_name: AWS service name or AWSServiceType enum
            profile_name: AWS profile name
            region: AWS region
            config: Optional boto3 Config object
            **kwargs: Additional resource configuration
            
        Returns:
            AWS service resource
        """
        # Convert enum to string if needed
        if isinstance(service_name, AWSServiceType):
            service_name = service_name.value
        
        profile_name = profile_name or "default"
        region = region or "us-east-1"
        
        try:
            # Get session from session manager
            session = await self.session_manager.get_session(profile_name, region)
            
            # Merge configurations
            final_config = self._merge_configs(config, kwargs)
            
            # Create resource
            resource = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: session.resource(service_name, config=final_config, **kwargs)
            )
            
            logger.info(f"Created {service_name} resource for profile '{profile_name}' in region '{region}'")
            return resource
            
        except Exception as e:
            logger.error(f"Failed to create {service_name} resource: {str(e)}")
            raise AWSServiceError(f"Resource creation failed: {str(e)}") from e
    
    async def check_service_availability(
        self,
        service_name: str,
        region: str
    ) -> RegionAvailability:
        """
        Check if a service is available in a specific region
        
        Args:
            service_name: AWS service name
            region: AWS region
            
        Returns:
            RegionAvailability status
        """
        # Check cache first
        cache_key = f"{service_name}:{region}"
        if cache_key in self.service_availability_cache:
            cached_result = self.service_availability_cache[cache_key]
            # Cache availability for 24 hours
            if 'cached_at' in cached_result and \
               (datetime.utcnow() - cached_result['cached_at']).total_seconds() < 86400:
                return cached_result['availability']
        
        try:
            # Get list of available regions for the service
            session = boto3.Session()
            available_regions = session.get_available_regions(service_name)
            
            if region in available_regions:
                availability = RegionAvailability.AVAILABLE
            else:
                # Check for special cases (global services)
                if service_name in ['iam', 'cloudfront', 'route53', 's3']:
                    availability = RegionAvailability.AVAILABLE
                else:
                    availability = RegionAvailability.UNAVAILABLE
            
            # Cache the result
            if service_name not in self.service_availability_cache:
                self.service_availability_cache[service_name] = {}
            
            self.service_availability_cache[service_name][region] = {
                'availability': availability,
                'cached_at': datetime.utcnow()
            }
            
            return availability
            
        except Exception as e:
            logger.warning(f"Could not check availability for {service_name} in {region}: {str(e)}")
            return RegionAvailability.UNKNOWN
    
    async def get_available_regions(self, service_name: str) -> List[str]:
        """
        Get list of available regions for a service
        
        Args:
            service_name: AWS service name
            
        Returns:
            List of available regions
        """
        try:
            session = boto3.Session()
            regions = session.get_available_regions(service_name)
            return sorted(regions)
        except Exception as e:
            logger.warning(f"Could not get available regions for {service_name}: {str(e)}")
            return []
    
    async def get_all_regions(self) -> List[str]:
        """
        Get list of all AWS regions
        
        Returns:
            List of all AWS regions
        """
        try:
            # Use EC2 to get all regions since it's available in all regions
            session = boto3.Session()
            return sorted(session.get_available_regions('ec2'))
        except Exception as e:
            logger.warning(f"Could not get all regions: {str(e)}")
            # Fallback to known regions
            return [
                'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
                'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
                'ap-northeast-2', 'ca-central-1', 'sa-east-1'
            ]
    
    def cleanup_expired_clients(self) -> int:
        """
        Clean up expired clients from cache
        
        Returns:
            Number of expired clients removed
        """
        expired_keys = [
            key for key, entry in self.client_cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self.client_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired clients")
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics
        """
        total_clients = len(self.client_cache)
        expired_clients = len([
            entry for entry in self.client_cache.values()
            if entry.is_expired
        ])
        
        return {
            'total_cached_clients': total_clients,
            'active_clients': total_clients - expired_clients,
            'expired_clients': expired_clients,
            'cache_hit_ratio': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_requests', 1), 1),
            'max_cached_clients': self.max_cached_clients
        }
    
    async def _create_client_with_retry(
        self,
        session: boto3.Session,
        service_name: str,
        region: str,
        config: Config
    ) -> Any:
        """
        Create client with retry logic and error handling
        
        Args:
            session: boto3 Session
            service_name: AWS service name
            region: AWS region
            config: boto3 Config object
            
        Returns:
            AWS service client
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                client = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: session.client(service_name, config=config)
                )
                
                # Test the client with a simple operation if possible
                await self._test_client(client, service_name)
                
                return client
                
            except (NoCredentialsError, TokenRetrievalError) as e:
                # Don't retry credential errors
                logger.error(f"Credential error creating {service_name} client: {str(e)}")
                raise AWSServiceError(f"Credential error: {str(e)}") from e
                
            except (EndpointConnectionError, BotocoreConnectionError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Connection error creating {service_name} client after {max_retries} attempts: {str(e)}")
                    raise AWSServiceError(f"Connection error: {str(e)}") from e
                
                # Exponential backoff
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection error on attempt {attempt + 1}, retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error creating {service_name} client after {max_retries} attempts: {str(e)}")
                    raise AWSServiceError(f"Client creation error: {str(e)}") from e
                
                # Exponential backoff for other errors too
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Error on attempt {attempt + 1}, retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
        
        raise AWSServiceError(f"Failed to create {service_name} client after {max_retries} attempts")
    
    async def _test_client(self, client: Any, service_name: str) -> None:
        """
        Test client with a simple operation to ensure it's working
        
        Args:
            client: AWS service client
            service_name: AWS service name
        """
        try:
            # Different test operations for different services
            if service_name == 'sts':
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    client.get_caller_identity
                )
            elif service_name == 's3':
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    client.list_buckets
                )
            elif service_name == 'ec2':
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: client.describe_regions(MaxResults=1)
                )
            # For other services, just skip testing to avoid unnecessary API calls
            
        except Exception as e:
            # Log warning but don't fail - the test operation might not be allowed
            logger.debug(f"Client test failed for {service_name} (this may be normal): {str(e)}")
    
    def _merge_configs(self, config: Optional[Config], kwargs: Dict[str, Any]) -> Config:
        """
        Merge default config with provided config and kwargs
        
        Args:
            config: Optional user-provided Config
            kwargs: Additional configuration parameters
            
        Returns:
            Merged Config object
        """
        # Start with default config
        merged_config = self.default_config
        
        # If user provided config, merge it
        if config:
            # Create new config with merged settings
            merged_dict = {}
            
            # Merge retries configuration
            if hasattr(merged_config, 'retries') and hasattr(config, 'retries'):
                merged_dict['retries'] = {**merged_config.retries, **config.retries}
            elif hasattr(config, 'retries'):
                merged_dict['retries'] = config.retries
            elif hasattr(merged_config, 'retries'):
                merged_dict['retries'] = merged_config.retries
            
            # Merge other config attributes
            for attr in ['max_pool_connections', 'connect_timeout', 'read_timeout']:
                value = getattr(config, attr, None) or getattr(merged_config, attr, None)
                if value is not None:
                    merged_dict[attr] = value
            
            merged_config = Config(**merged_dict)
        
        return merged_config
    
    def _cache_client(
        self,
        client: Any,
        profile_name: str,
        region: str,
        service_name: str
    ) -> None:
        """
        Cache client with automatic cleanup if needed
        
        Args:
            client: AWS service client
            profile_name: AWS profile name
            region: AWS region
            service_name: AWS service name
        """
        # Clean up expired clients first
        self.cleanup_expired_clients()
        
        # If at max capacity, remove oldest client
        if len(self.client_cache) >= self.max_cached_clients:
            oldest_key = min(
                self.client_cache.keys(),
                key=lambda k: self.client_cache[k].created_at
            )
            del self.client_cache[oldest_key]
        
        # Add new client to cache
        cache_entry = AWSClientCacheEntry(
            client=client,
            created_at=datetime.utcnow(),
            profile_name=profile_name,
            region=region,
            service_name=service_name
        )
        
        self.client_cache[cache_entry.cache_key] = cache_entry


class AWSServiceError(AWSSessionError):
    """Raised when there are issues with AWS service clients"""
    pass


# Global client factory instance
_client_factory: Optional[AWSServiceClientFactory] = None


def get_client_factory() -> AWSServiceClientFactory:
    """Get global client factory instance"""
    global _client_factory
    if _client_factory is None:
        _client_factory = AWSServiceClientFactory()
    return _client_factory


async def cleanup_clients_periodically():
    """Background task to clean up expired clients"""
    while True:
        try:
            await asyncio.sleep(300)  # Clean up every 5 minutes
            factory = get_client_factory()
            cleaned = factory.cleanup_expired_clients()
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} expired AWS clients")
        except Exception as e:
            logger.error(f"Error in client cleanup task: {str(e)}")
