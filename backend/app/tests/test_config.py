"""
Test configuration validation
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings, create_settings
from app.core.validation import ConfigValidator, validate_configuration


class TestSettings:
    """Test settings configuration"""
    
    def test_default_settings(self):
        """Test default settings are valid"""
        settings = Settings()
        assert settings.PROJECT_NAME == "Cloud Explorer API"
        assert settings.VERSION == "0.1.0"
        assert settings.PORT == 8000
        assert settings.DEBUG is False
    
    def test_environment_detection(self):
        """Test environment detection properties"""
        # Development settings
        dev_settings = Settings(DEBUG=True)
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False
        
        # Production settings
        prod_settings = Settings(DEBUG=False)
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True
    
    def test_enabled_services(self):
        """Test enabled services property"""
        settings = Settings(
            ENABLE_EC2_SERVICE=True,
            ENABLE_RDS_SERVICE=False,
            ENABLE_VPC_SERVICE=True
        )
        enabled = settings.enabled_services
        assert "ec2" in enabled
        assert "rds" not in enabled
        assert "vpc" in enabled
    
    def test_service_rate_limit(self):
        """Test service rate limit getter"""
        settings = Settings(
            AWS_EC2_RATE_LIMIT=100,
            AWS_RDS_RATE_LIMIT=50
        )
        assert settings.get_service_rate_limit("ec2") == 100
        assert settings.get_service_rate_limit("rds") == 50
        assert settings.get_service_rate_limit("unknown") == 50  # Default
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string"""
        settings = Settings(CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000")
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
    
    def test_allowed_hosts_parsing(self):
        """Test allowed hosts parsing from string"""
        settings = Settings(ALLOWED_HOSTS="localhost,127.0.0.1,testserver")
        assert len(settings.ALLOWED_HOSTS) == 3
        assert "localhost" in settings.ALLOWED_HOSTS
    
    def test_log_level_validation(self):
        """Test log level validation"""
        # Valid log level
        settings = Settings(LOG_LEVEL="DEBUG")
        assert settings.LOG_LEVEL == "DEBUG"
        
        # Invalid log level should raise validation error
        with pytest.raises(ValueError):
            Settings(LOG_LEVEL="INVALID")
    
    def test_production_secret_key_validation(self):
        """Test production secret key validation"""
        # Should raise error for default key in production
        with pytest.raises(ValueError):
            Settings(
                DEBUG=False,
                SECRET_KEY="your-super-secret-key-here-change-in-production"
            )
    
    def test_to_dict_excludes_sensitive(self):
        """Test to_dict excludes sensitive information"""
        settings = Settings(SECRET_KEY="super-secret-key")
        data = settings.to_dict()
        assert data["SECRET_KEY"] == "***"


class TestConfigValidator:
    """Test configuration validator"""
    
    def test_basic_validation_success(self):
        """Test successful validation"""
        settings = Settings(
            DEBUG=True,
            SECRET_KEY="a-secure-secret-key-for-development-only",
            AWS_DEFAULT_REGION="us-east-1"
        )
        validator = ConfigValidator(settings)
        assert validator.validate_environment() is True
        assert len(validator.errors) == 0
    
    def test_missing_required_settings(self):
        """Test validation with missing required settings"""
        settings = Settings(AWS_DEFAULT_REGION="")
        validator = ConfigValidator(settings)
        assert validator.validate_environment() is False
        assert len(validator.errors) > 0
    
    def test_production_security_validation(self):
        """Test production security validation"""
        settings = Settings(
            DEBUG=False,
            SECRET_KEY="short",  # Too short
            CORS_ORIGINS=["http://unsafe-origin.com"]  # Non-HTTPS
        )
        validator = ConfigValidator(settings)
        validator.validate_environment()
        
        # Should have errors for short secret key
        assert any("32 characters" in error for error in validator.errors)
        # Should have warnings for non-HTTPS origins
        assert any("Non-HTTPS" in warning for warning in validator.warnings)
    
    def test_aws_settings_validation(self):
        """Test AWS settings validation"""
        settings = Settings(
            AWS_DEFAULT_REGION="invalid",
            AWS_EC2_RATE_LIMIT=2000  # Very high
        )
        validator = ConfigValidator(settings)
        validator.validate_environment()
        
        # Should have error for invalid region
        assert any("valid AWS region" in error for error in validator.errors)
        # Should have warning for high rate limit
        assert any("very high" in warning.lower() for warning in validator.warnings)
    
    def test_file_path_validation(self):
        """Test file path validation and creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "test.log"
            settings = Settings(
                LOG_FILE_ENABLED=True,
                LOG_FILE_PATH=str(log_path)
            )
            validator = ConfigValidator(settings)
            validator.validate_environment()
            
            # Log directory should be created
            assert log_path.parent.exists()
    
    def test_validation_summary(self):
        """Test validation summary"""
        settings = Settings(DEBUG=True)
        validator = ConfigValidator(settings)
        validator.validate_environment()
        
        summary = validator.get_validation_summary()
        assert "valid" in summary
        assert "warnings_count" in summary
        assert "errors_count" in summary
        assert "environment" in summary
        assert "enabled_services" in summary


class TestConfigurationHelpers:
    """Test configuration helper functions"""
    
    def test_validate_configuration_function(self):
        """Test validate_configuration function"""
        settings = Settings(DEBUG=True, SECRET_KEY="test-key-for-development")
        result = validate_configuration(settings)
        assert result is True
    
    @patch.dict("os.environ", {"DEBUG": "true"})
    @patch("os.path.exists")
    def test_create_settings_development(self, mock_exists):
        """Test create_settings with development environment"""
        mock_exists.side_effect = lambda path: path == ".env.development"
        
        with patch("app.core.config.Settings") as mock_settings:
            create_settings()
            mock_settings.assert_called_once_with(_env_file=".env.development")
    
    @patch.dict("os.environ", {"DEBUG": "false"})
    @patch("os.path.exists")
    def test_create_settings_production(self, mock_exists):
        """Test create_settings with production environment"""
        mock_exists.side_effect = lambda path: path == ".env.production"
        
        with patch("app.core.config.Settings") as mock_settings:
            create_settings()
            mock_settings.assert_called_once_with(_env_file=".env.production")


class TestFeatureFlags:
    """Test feature flag functionality"""
    
    def test_service_feature_flags(self):
        """Test service feature flags"""
        settings = Settings(
            ENABLE_EC2_SERVICE=True,
            ENABLE_RDS_SERVICE=False,
            ENABLE_S3_SERVICE=True
        )
        
        enabled = settings.enabled_services
        assert "ec2" in enabled
        assert "rds" not in enabled
        assert "s3" in enabled
    
    def test_advanced_feature_flags(self):
        """Test advanced feature flags"""
        settings = Settings(
            ENABLE_COST_ESTIMATION=True,
            ENABLE_COMPLIANCE_CHECKS=False
        )
        
        assert settings.ENABLE_COST_ESTIMATION is True
        assert settings.ENABLE_COMPLIANCE_CHECKS is False
