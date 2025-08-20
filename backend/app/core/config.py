"""
Configuration settings for Cloud Explorer Backend
"""
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cloud Explorer API"
    VERSION: str = "0.1.0"
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(default=8000, description="Port to bind the server to")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # Security Configuration
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0", "testserver"],
        description="Allowed hosts for the application"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # AWS Configuration
    AWS_DEFAULT_REGION: str = Field(default="us-east-1", description="Default AWS region")
    AWS_PROFILE: str = Field(default="default", description="Default AWS profile")
    
    # Development Configuration
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    RELOAD: bool = Field(default=False, description="Enable auto-reload in development")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")


# Create settings instance
settings = Settings()
