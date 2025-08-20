"""
Cloud Explorer Backend - Main FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.validation import validate_configuration, setup_logging
from app.core.security import (
    SecurityHeadersMiddleware, 
    RequestLoggingMiddleware, 
    setup_rate_limiting,
    rate_limit_default,
    rate_limit_config
)
from app.core.ssl_utils import get_ssl_context
from app.routers import health, aws_profiles
from app.models.responses import RootResponse, ConfigResponse, ErrorResponse


# Setup logging
setup_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Cloud Explorer API...")
    
    # Validate configuration
    if not validate_configuration(settings):
        logger.error("Configuration validation failed")
        raise SystemExit(1)
    
    logger.info(f"Environment: {'development' if settings.is_development else 'production'}")
    logger.info(f"Enabled services: {', '.join(settings.enabled_services)}")
    logger.info(f"API documentation: {'/docs' if settings.ENABLE_OPENAPI_DOCS else 'disabled'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cloud Explorer API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs" if settings.ENABLE_OPENAPI_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_OPENAPI_DOCS else None,
    lifespan=lifespan,
    contact={
        "name": "Cloud Explorer Team",
        "url": "https://github.com/PrasadTelasula/cloud-explorer",
        "email": "support@cloudexplorer.dev",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://localhost:{settings.PORT}",
            "description": "Development server",
        },
        {
            "url": "https://api.cloudexplorer.dev",
            "description": "Production server",
        },
    ],
    tags_metadata=[
        {
            "name": "root",
            "description": "Root API endpoints providing basic information and configuration",
        },
        {
            "name": "health",
            "description": "Health check endpoints for monitoring API status",
        },
        {
            "name": "accounts",
            "description": "AWS account and profile management endpoints",
            "externalDocs": {
                "description": "AWS CLI Configuration Guide",
                "url": "https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html",
            },
        },
        {
            "name": "resources",
            "description": "AWS resource discovery and management endpoints",
        },
    ],
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)

# Security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enabled=settings.SECURITY_HEADERS_ENABLED,
)

# Request logging middleware (for security monitoring)
app.add_middleware(
    RequestLoggingMiddleware,
)

# CORS middleware (configured for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Setup rate limiting
rate_limiter = setup_rate_limiting(app)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(aws_profiles.router, prefix="/api/aws", tags=["aws-profiles"])


def custom_openapi():
    """Custom OpenAPI schema generator with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=f"""
        {settings.DESCRIPTION}
        
        ## Overview
        
        Cloud Explorer is a comprehensive AWS resource management and exploration tool that provides:
        
        - **Multi-Account Support**: Manage resources across multiple AWS accounts
        - **Read-Only Operations**: Safe exploration without modification capabilities
        - **Real-Time Data**: Live AWS resource information and status
        - **Regional Coverage**: Support for all AWS regions and services
        
        ## Authentication
        
        This API uses AWS credential profiles configured locally. Ensure your AWS CLI is properly configured
        with the necessary profiles and permissions.
        
        ## Rate Limiting
        
        API requests are rate-limited to prevent AWS API throttling. Default limits:
        - 100 requests per minute for read operations
        - 10 requests per minute for configuration operations
        
        ## Error Handling
        
        All endpoints return standardized error responses with appropriate HTTP status codes.
        Check the error message and detail fields for troubleshooting information.
        """,
        routes=app.routes,
        contact={
            "name": "Cloud Explorer Team",
            "url": "https://github.com/PrasadTelasula/cloud-explorer",
            "email": "support@cloudexplorer.dev",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )
    
    # Add security schemes for future authentication
    openapi_schema["components"]["securitySchemes"] = {
        "AWSCredentials": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "AWS",
            "description": "AWS credentials via local profile configuration",
        },
        "APIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for rate limiting and access control",
        },
    }
    
    # Add global error responses
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method != "parameters":
                openapi_schema["paths"][path][method]["responses"].update({
                    "400": {
                        "description": "Bad Request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                    "500": {
                        "description": "Internal Server Error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                })
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get(
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    summary="API Information",
    description="Get basic information about the Cloud Explorer API including version, documentation links, and enabled services",
    tags=["root"],
    responses={
        200: {
            "description": "API information retrieved successfully",
            "model": RootResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_default()
async def root(request: Request) -> RootResponse:
    """
    Root endpoint providing API information and navigation links.
    
    This endpoint serves as the entry point for the API, providing essential information
    about the service including version, documentation links, and available features.
    
    Returns:
        RootResponse: Complete API information including navigation links
    """
    return RootResponse(
        message=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        environment="development" if settings.is_development else "production",
        docs="/docs" if settings.ENABLE_OPENAPI_DOCS else None,
        health="/api/health",
        enabled_services=settings.enabled_services
    )


@app.get(
    "/config",
    response_model=ConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Configuration Information",
    description="Get non-sensitive configuration information (development only)",
    tags=["root"],
    responses={
        200: {
            "description": "Configuration retrieved successfully",
            "model": ConfigResponse,
        },
        404: {
            "description": "Configuration endpoint not available in production",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
    },
)
@rate_limit_config()
async def get_config(request: Request) -> ConfigResponse:
    """
    Get non-sensitive configuration information.
    
    This endpoint is only available in development mode and provides insight into
    the current configuration settings without exposing sensitive information.
    
    Returns:
        ConfigResponse: Current configuration settings
        
    Raises:
        HTTPException: 404 if called in production environment
    """
    if not settings.is_development:
        return JSONResponse(
            {"error": "Configuration endpoint only available in development"},
            status_code=404
        )
    
    config_dict = settings.to_dict()
    return ConfigResponse(
        project_name=config_dict.get("PROJECT_NAME", ""),
        version=config_dict.get("VERSION", ""),
        debug=config_dict.get("DEBUG", False),
        environment="development" if settings.is_development else "production",
        aws_region=config_dict.get("AWS_DEFAULT_REGION", ""),
        enabled_services=settings.enabled_services,
        cors_origins=settings.cors_origins_list,
        log_level=config_dict.get("LOG_LEVEL", "")
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get SSL context for HTTPS if enabled
    ssl_context = get_ssl_context()
    
    # Hot-reload configuration in development
    reload_dirs = ["./app"] if settings.is_development else None
    
    # Configure server parameters
    server_config = {
        "app": "main:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.RELOAD,
        "reload_dirs": reload_dirs,
        "workers": settings.WORKERS if not settings.RELOAD else 1,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": settings.is_development,
    }
    
    # Add SSL configuration if HTTPS is enabled
    if ssl_context:
        server_config.update({
            "ssl_certfile": ssl_context[0],
            "ssl_keyfile": ssl_context[1],
        })
        print(f"Starting server with HTTPS on https://{settings.HOST}:{settings.PORT}")
        print("Note: Self-signed certificate will trigger browser warnings")
    else:
        print(f"Starting server with HTTP on http://{settings.HOST}:{settings.PORT}")
    
    # Security information
    if settings.SECURITY_HEADERS_ENABLED:
        print("Security headers: Enabled")
    if settings.RATE_LIMITING_ENABLED:
        print(f"Rate limiting: {settings.RATE_LIMIT_REQUESTS} requests/minute")
    
    uvicorn.run(**server_config)
