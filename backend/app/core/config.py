"""
Configuration settings for Cloud Explorer Backend
"""
import os
from typing import List, Optional, Any, Dict
from pathlib import Path

from pydantic import Field, validator, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with comprehensive configuration validation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    
    PROJECT_NAME: str = Field(default="Cloud Explorer API", description="Project name")
    VERSION: str = Field(default="0.1.0", description="API version")
    DESCRIPTION: str = Field(
        default="AWS resource management and monitoring API",
        description="API description"
    )
    
    # =============================================================================
    # SERVER CONFIGURATION
    # =============================================================================
    
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Port to bind the server to")
    WORKERS: int = Field(default=1, ge=1, le=16, description="Number of worker processes")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    RELOAD: bool = Field(default=False, description="Enable auto-reload in development")
    
    # API Configuration
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    
    ALLOWED_HOSTS: str = Field(
        default="localhost,127.0.0.1,0.0.0.0,testserver",
        description="Allowed hosts for the application (comma-separated)"
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # JWT Configuration
    SECRET_KEY: str = Field(
        default="your-super-secret-key-here-change-in-production",
        min_length=32,
        description="Secret key for JWT tokens"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, ge=1, le=1440, description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, ge=1, le=30, description="Refresh token expiration in days"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    
    # HTTPS Configuration
    HTTPS_ENABLED: bool = Field(default=False, description="Enable HTTPS for development")
    SSL_CERT_PATH: str = Field(default="certs/cert.pem", description="SSL certificate path")
    SSL_KEY_PATH: str = Field(default="certs/key.pem", description="SSL private key path")
    
    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, description="Enable security headers")
    HSTS_MAX_AGE: int = Field(default=31536000, description="HSTS max age in seconds")
    CSP_POLICY: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data: fastapi.tiangolo.com; font-src 'self' cdn.jsdelivr.net; connect-src 'self'",
        description="Content Security Policy"
    )
    
    # Rate Limiting
    RATE_LIMITING_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1, description="Rate limit requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    
    # API Rate Limits
    API_RATE_LIMIT_CONFIG: int = Field(default=10, ge=1, description="Config API rate limit per minute")
    API_RATE_LIMIT_HEALTH: int = Field(default=60, ge=1, description="Health API rate limit per minute")
    API_RATE_LIMIT_DEFAULT: int = Field(default=100, ge=1, description="Default API rate limit per minute")
    
    # =============================================================================
    # AWS CONFIGURATION
    # =============================================================================
    
    AWS_DEFAULT_REGION: str = Field(default="us-east-1", description="Default AWS region")
    AWS_PROFILE: str = Field(default="default", description="Default AWS profile")
    
    # AWS Rate Limiting
    AWS_EC2_RATE_LIMIT: int = Field(default=100, ge=1, description="EC2 API rate limit per minute")
    AWS_RDS_RATE_LIMIT: int = Field(default=50, ge=1, description="RDS API rate limit per minute")
    AWS_VPC_RATE_LIMIT: int = Field(default=100, ge=1, description="VPC API rate limit per minute")
    AWS_S3_RATE_LIMIT: int = Field(default=200, ge=1, description="S3 API rate limit per minute")
    
    # AWS Retry Configuration
    AWS_MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="AWS API max retries")
    AWS_RETRY_DELAY: int = Field(default=1, ge=1, le=60, description="AWS API retry delay in seconds")
    
    # =============================================================================
    # CACHING CONFIGURATION
    # =============================================================================
    
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    CACHE_TTL_SECONDS: int = Field(default=300, ge=60, description="Default cache TTL in seconds")
    
    # Session Configuration
    SESSION_COOKIE_NAME: str = Field(default="cloud_explorer_session", description="Session cookie name")
    SESSION_MAX_AGE_SECONDS: int = Field(default=86400, ge=3600, description="Session max age in seconds")
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    LOG_FILE_ENABLED: bool = Field(default=True, description="Enable file logging")
    LOG_FILE_PATH: str = Field(default="logs/cloud_explorer.log", description="Log file path")
    LOG_FILE_MAX_SIZE_MB: int = Field(default=10, ge=1, description="Max log file size in MB")
    LOG_FILE_BACKUP_COUNT: int = Field(default=5, ge=1, description="Log file backup count")
    
    # =============================================================================
    # RATE LIMITING
    # =============================================================================
    
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1, description="Rate limit requests per window")
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    
    # Per-endpoint rate limits
    HEALTH_CHECK_RATE_LIMIT: int = Field(default=1000, ge=1, description="Health check rate limit")
    ACCOUNTS_RATE_LIMIT: int = Field(default=10, ge=1, description="Accounts endpoint rate limit")
    RESOURCES_RATE_LIMIT: int = Field(default=50, ge=1, description="Resources endpoint rate limit")
    
    # =============================================================================
    # MONITORING & OBSERVABILITY
    # =============================================================================
    
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, ge=1, le=30, description="Health check timeout")
    HEALTH_CHECK_AWS_ENABLED: bool = Field(default=True, description="Enable AWS health checks")
    
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PREFIX: str = Field(default="cloud_explorer", description="Metrics prefix")
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    
    # Service toggles
    ENABLE_EC2_SERVICE: bool = Field(default=True, description="Enable EC2 service")
    ENABLE_RDS_SERVICE: bool = Field(default=True, description="Enable RDS service")
    ENABLE_VPC_SERVICE: bool = Field(default=True, description="Enable VPC service")
    ENABLE_S3_SERVICE: bool = Field(default=True, description="Enable S3 service")
    ENABLE_LAMBDA_SERVICE: bool = Field(default=True, description="Enable Lambda service")
    ENABLE_ELB_SERVICE: bool = Field(default=True, description="Enable ELB service")
    
    # Advanced features
    ENABLE_COST_ESTIMATION: bool = Field(default=False, description="Enable cost estimation")
    ENABLE_COMPLIANCE_CHECKS: bool = Field(default=False, description="Enable compliance checks")
    ENABLE_RESOURCE_RECOMMENDATIONS: bool = Field(
        default=False, description="Enable resource recommendations"
    )
    
    # Development features
    ENABLE_OPENAPI_DOCS: bool = Field(default=True, description="Enable OpenAPI documentation")
    ENABLE_DEBUG_TOOLBAR: bool = Field(default=False, description="Enable debug toolbar")
    ENABLE_PROFILING: bool = Field(default=False, description="Enable profiling")
    USE_MOCK_AWS_DATA: bool = Field(default=False, description="Use mock AWS data for testing")
    MOCK_DELAY_SECONDS: float = Field(default=0.5, ge=0, description="Mock delay in seconds")
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("AWS_DEFAULT_REGION")
    def validate_aws_region(cls, v):
        """Validate AWS region format"""
        if not v or len(v) < 9:  # Minimum: us-east-1
            raise ValueError("AWS_DEFAULT_REGION must be a valid AWS region")
        return v
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.DEBUG
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.DEBUG
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as a list"""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]
        return self.ALLOWED_HOSTS
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS
    
    @property
    def enabled_services(self) -> List[str]:
        """Get list of enabled AWS services"""
        services = []
        if self.ENABLE_EC2_SERVICE:
            services.append("ec2")
        if self.ENABLE_RDS_SERVICE:
            services.append("rds")
        if self.ENABLE_VPC_SERVICE:
            services.append("vpc")
        if self.ENABLE_S3_SERVICE:
            services.append("s3")
        if self.ENABLE_LAMBDA_SERVICE:
            services.append("lambda")
        if self.ENABLE_ELB_SERVICE:
            services.append("elb")
        return services
    
    @property
    def log_file_dir(self) -> Path:
        """Get log file directory path"""
        return Path(self.LOG_FILE_PATH).parent
    
    def get_service_rate_limit(self, service: str) -> int:
        """Get rate limit for specific AWS service"""
        rate_limits = {
            "ec2": self.AWS_EC2_RATE_LIMIT,
            "rds": self.AWS_RDS_RATE_LIMIT,
            "vpc": self.AWS_VPC_RATE_LIMIT,
            "s3": self.AWS_S3_RATE_LIMIT,
        }
        return rate_limits.get(service.lower(), 50)  # Default rate limit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding sensitive data)"""
        data = self.dict()
        # Remove sensitive information
        sensitive_keys = ["SECRET_KEY"]
        for key in sensitive_keys:
            if key in data:
                data[key] = "***"
        return data


# Configuration hot-reloading for development
def create_settings() -> Settings:
    """Create settings instance with environment detection"""
    # First try to load from .env to check DEBUG setting
    temp_settings = Settings(_env_file=".env")
    
    # Use the DEBUG value from settings to determine environment file
    if temp_settings.DEBUG and os.path.exists(".env.development"):
        env_file = ".env.development"
    elif not temp_settings.DEBUG and os.path.exists(".env.production"):
        env_file = ".env.production"
    else:
        env_file = ".env"
    
    # Return final settings with correct environment file
    return Settings(_env_file=env_file)


# Create settings instance
settings = create_settings()
