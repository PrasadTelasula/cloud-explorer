"""
Configuration validation utilities
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from pydantic import ValidationError

from app.core.config import Settings


logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration validation and environment setup utility"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def validate_environment(self) -> bool:
        """
        Validate the current environment configuration
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        logger.info("Validating environment configuration...")
        
        # Reset validation state
        self.warnings.clear()
        self.errors.clear()
        
        # Run validation checks
        self._validate_required_settings()
        self._validate_security_settings()
        self._validate_aws_settings()
        self._validate_file_paths()
        self._validate_network_settings()
        self._validate_feature_flags()
        
        # Log results
        if self.warnings:
            logger.warning(f"Configuration warnings: {len(self.warnings)}")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        if self.errors:
            logger.error(f"Configuration errors: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("Environment configuration validation passed")
        return True
    
    def _validate_required_settings(self) -> None:
        """Validate required settings"""
        required_settings = [
            ("PROJECT_NAME", "Project name is required"),
            ("VERSION", "Version is required"),
            ("AWS_DEFAULT_REGION", "AWS default region is required"),
        ]
        
        for setting, message in required_settings:
            value = getattr(self.settings, setting, None)
            if not value:
                self.errors.append(message)
    
    def _validate_security_settings(self) -> None:
        """Validate security-related settings"""
        # Check secret key in production
        if self.settings.is_production:
            if "change-in-production" in self.settings.SECRET_KEY.lower():
                self.errors.append(
                    "SECRET_KEY must be changed for production deployment"
                )
            
            if len(self.settings.SECRET_KEY) < 32:
                self.errors.append("SECRET_KEY must be at least 32 characters long")
            
            # Check HTTPS in production CORS origins
            for origin in self.settings.CORS_ORIGINS:
                if origin.startswith("http://") and "localhost" not in origin:
                    self.warnings.append(
                        f"Non-HTTPS CORS origin in production: {origin}"
                    )
        
        # Validate allowed hosts
        if not self.settings.ALLOWED_HOSTS:
            self.errors.append("ALLOWED_HOSTS cannot be empty")
        
        # Check for wildcard allowed hosts in production
        if self.settings.is_production and "*" in self.settings.ALLOWED_HOSTS:
            self.errors.append("Wildcard allowed hosts not permitted in production")
    
    def _validate_aws_settings(self) -> None:
        """Validate AWS-related settings"""
        # Check AWS region format
        region = self.settings.AWS_DEFAULT_REGION
        if not region or len(region) < 9:  # Minimum: us-east-1
            self.errors.append("AWS_DEFAULT_REGION must be a valid AWS region")
        
        # Validate AWS profile
        if not self.settings.AWS_PROFILE:
            self.errors.append("AWS_PROFILE is required")
        
        # Check rate limits are reasonable
        rate_limits = {
            "EC2": self.settings.AWS_EC2_RATE_LIMIT,
            "RDS": self.settings.AWS_RDS_RATE_LIMIT,
            "VPC": self.settings.AWS_VPC_RATE_LIMIT,
            "S3": self.settings.AWS_S3_RATE_LIMIT,
        }
        
        for service, limit in rate_limits.items():
            if limit > 1000:
                self.warnings.append(
                    f"AWS {service} rate limit is very high: {limit}/min"
                )
            elif limit < 5:
                self.warnings.append(
                    f"AWS {service} rate limit is very low: {limit}/min"
                )
    
    def _validate_file_paths(self) -> None:
        """Validate file paths and create directories if needed"""
        if self.settings.LOG_FILE_ENABLED:
            log_dir = self.settings.log_file_dir
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Log directory created/verified: {log_dir}")
            except Exception as e:
                self.errors.append(f"Cannot create log directory {log_dir}: {e}")
    
    def _validate_network_settings(self) -> None:
        """Validate network-related settings"""
        # Validate port range
        if not (1 <= self.settings.PORT <= 65535):
            self.errors.append(f"Invalid port number: {self.settings.PORT}")
        
        # Check for common port conflicts
        if self.settings.PORT in [22, 25, 53, 80, 443, 993, 995]:
            self.warnings.append(
                f"Port {self.settings.PORT} is commonly used by other services"
            )
        
        # Validate worker count
        if self.settings.WORKERS > 16:
            self.warnings.append(
                f"High worker count: {self.settings.WORKERS}. "
                "Consider CPU core count."
            )
    
    def _validate_feature_flags(self) -> None:
        """Validate feature flag consistency"""
        enabled_services = self.settings.enabled_services
        
        if not enabled_services:
            self.warnings.append("No AWS services are enabled")
        
        # Check if advanced features are enabled without basic services
        if self.settings.ENABLE_COST_ESTIMATION and len(enabled_services) < 2:
            self.warnings.append(
                "Cost estimation enabled with few services enabled"
            )
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get validation summary
        
        Returns:
            Dict containing validation results
        """
        return {
            "valid": len(self.errors) == 0,
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "warnings": self.warnings,
            "errors": self.errors,
            "environment": "development" if self.settings.is_development else "production",
            "enabled_services": self.settings.enabled_services,
        }


def validate_configuration(settings: Optional[Settings] = None) -> bool:
    """
    Validate configuration and log results
    
    Args:
        settings: Settings instance to validate (uses global if None)
    
    Returns:
        bool: True if validation passes
    """
    if settings is None:
        from app.core.config import settings as global_settings
        settings = global_settings
    
    validator = ConfigValidator(settings)
    return validator.validate_environment()


def setup_logging(settings: Settings) -> None:
    """
    Set up logging configuration based on settings
    
    Args:
        settings: Settings instance
    """
    # Configure root logger
    log_level = getattr(logging, settings.LOG_LEVEL)
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if settings.LOG_FILE_ENABLED:
        try:
            # Ensure log directory exists
            settings.log_file_dir.mkdir(parents=True, exist_ok=True)
            
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                settings.LOG_FILE_PATH,
                maxBytes=settings.LOG_FILE_MAX_SIZE_MB * 1024 * 1024,
                backupCount=settings.LOG_FILE_BACKUP_COUNT
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
            
            logger.info(f"File logging enabled: {settings.LOG_FILE_PATH}")
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")


def create_environment_file(env_type: str = "development") -> Path:
    """
    Create environment file from template
    
    Args:
        env_type: Type of environment ("development" or "production")
    
    Returns:
        Path to created environment file
    """
    if env_type not in ["development", "production"]:
        raise ValueError("env_type must be 'development' or 'production'")
    
    source_file = Path(f".env.{env_type}")
    target_file = Path(".env")
    
    if not source_file.exists():
        raise FileNotFoundError(f"Template file {source_file} not found")
    
    if target_file.exists():
        backup_file = Path(f".env.backup.{env_type}")
        target_file.rename(backup_file)
        logger.info(f"Existing .env backed up to {backup_file}")
    
    # Copy template to .env
    import shutil
    shutil.copy2(source_file, target_file)
    
    logger.info(f"Created .env from {source_file}")
    return target_file
