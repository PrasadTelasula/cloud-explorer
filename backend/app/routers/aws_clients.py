"""
AWS Client Factory API endpoints
"""
import logging
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.aws.client_factory import (
    get_client_factory, 
    AWSServiceClientFactory, 
    AWSServiceType,
    AWSServiceError,
    RegionAvailability
)
from app.aws.session_manager import AWSSessionManager, get_session_manager
from app.models.aws import AWSSessionError, AWSProfileNotFoundError
from app.core.security import rate_limit_default

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/aws/clients",
    tags=["AWS Clients"],
    responses={
        404: {"description": "Service or profile not found"},
        500: {"description": "Client factory error"}
    }
)


@router.get("/services",
           summary="List supported AWS services",
           description="Get list of all supported AWS services with their identifiers")
@rate_limit_default()
async def list_supported_services(request: Request) -> Dict[str, Any]:
    """
    List all supported AWS services
    
    Returns:
        Dictionary of service categories and their services
    """
    try:
        services_by_category = {
            "compute": [
                {"name": "EC2", "identifier": "ec2", "description": "Elastic Compute Cloud"},
                {"name": "Lambda", "identifier": "lambda", "description": "Serverless Functions"},
                {"name": "ECS", "identifier": "ecs", "description": "Elastic Container Service"},
                {"name": "EKS", "identifier": "eks", "description": "Elastic Kubernetes Service"},
                {"name": "Batch", "identifier": "batch", "description": "Batch Computing"}
            ],
            "storage": [
                {"name": "S3", "identifier": "s3", "description": "Simple Storage Service"},
                {"name": "EBS", "identifier": "ebs", "description": "Elastic Block Store"},
                {"name": "EFS", "identifier": "efs", "description": "Elastic File System"},
                {"name": "FSx", "identifier": "fsx", "description": "File Systems"}
            ],
            "database": [
                {"name": "RDS", "identifier": "rds", "description": "Relational Database Service"},
                {"name": "DynamoDB", "identifier": "dynamodb", "description": "NoSQL Database"},
                {"name": "Redshift", "identifier": "redshift", "description": "Data Warehouse"},
                {"name": "DocumentDB", "identifier": "docdb", "description": "Document Database"},
                {"name": "Neptune", "identifier": "neptune", "description": "Graph Database"}
            ],
            "networking": [
                {"name": "VPC", "identifier": "ec2", "description": "Virtual Private Cloud"},
                {"name": "ELB", "identifier": "elbv2", "description": "Elastic Load Balancing"},
                {"name": "Route53", "identifier": "route53", "description": "DNS Service"},
                {"name": "CloudFront", "identifier": "cloudfront", "description": "Content Delivery Network"}
            ],
            "security": [
                {"name": "IAM", "identifier": "iam", "description": "Identity and Access Management"},
                {"name": "STS", "identifier": "sts", "description": "Security Token Service"},
                {"name": "Secrets Manager", "identifier": "secretsmanager", "description": "Secrets Management"},
                {"name": "KMS", "identifier": "kms", "description": "Key Management Service"}
            ],
            "monitoring": [
                {"name": "CloudWatch", "identifier": "cloudwatch", "description": "Monitoring and Observability"},
                {"name": "CloudTrail", "identifier": "cloudtrail", "description": "API Logging"},
                {"name": "X-Ray", "identifier": "xray", "description": "Distributed Tracing"}
            ],
            "messaging": [
                {"name": "SNS", "identifier": "sns", "description": "Simple Notification Service"},
                {"name": "SQS", "identifier": "sqs", "description": "Simple Queue Service"},
                {"name": "SES", "identifier": "ses", "description": "Simple Email Service"}
            ]
        }
        
        return {
            "services": services_by_category,
            "total_services": sum(len(services) for services in services_by_category.values())
        }
        
    except Exception as e:
        logger.error(f"Error listing services: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list services: {str(e)}")


@router.get("/regions",
           summary="List available regions",
           description="Get list of all AWS regions or regions available for a specific service")
@rate_limit_default()
async def list_regions(
    request: Request,
    service: Optional[str] = Query(None, description="AWS service name to check region availability"),
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    List AWS regions, optionally filtered by service availability
    
    Args:
        service: Optional AWS service name to filter regions
        
    Returns:
        List of regions with availability information
    """
    try:
        if service:
            # Get regions available for specific service
            available_regions = await client_factory.get_available_regions(service)
            return {
                "service": service,
                "available_regions": available_regions,
                "total_regions": len(available_regions)
            }
        else:
            # Get all regions
            all_regions = await client_factory.get_all_regions()
            return {
                "all_regions": all_regions,
                "total_regions": len(all_regions)
            }
            
    except Exception as e:
        logger.error(f"Error listing regions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list regions: {str(e)}")


@router.get("/availability/{service}/{region}",
           summary="Check service availability",
           description="Check if a specific AWS service is available in a region")
@rate_limit_default()
async def check_service_availability(
    request: Request,
    service: str = Path(..., description="AWS service name"),
    region: str = Path(..., description="AWS region"),
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    Check if a service is available in a specific region
    
    Args:
        service: AWS service name
        region: AWS region
        
    Returns:
        Service availability information
    """
    try:
        availability = await client_factory.check_service_availability(service, region)
        
        return {
            "service": service,
            "region": region,
            "availability": availability.value,
            "available": availability == RegionAvailability.AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Error checking availability for {service} in {region}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")


@router.post("/test/{service}",
            summary="Test service client",
            description="Test creating a client for a specific AWS service")
@rate_limit_default()
async def test_service_client(
    request: Request,
    service: str = Path(..., description="AWS service name"),
    profile_name: Optional[str] = Query(None, description="AWS profile name"),
    region: Optional[str] = Query("us-east-1", description="AWS region"),
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    Test creating a client for a specific service
    
    Args:
        service: AWS service name
        profile_name: AWS profile name
        region: AWS region
        
    Returns:
        Test result with client information
    """
    try:
        profile_name = profile_name or "default"
        
        # Check service availability first
        availability = await client_factory.check_service_availability(service, region)
        if availability == RegionAvailability.UNAVAILABLE:
            raise HTTPException(
                status_code=400, 
                detail=f"Service '{service}' is not available in region '{region}'"
            )
        
        # Try to create the client
        client = await client_factory.get_client(
            service_name=service,
            profile_name=profile_name,
            region=region
        )
        
        return {
            "success": True,
            "service": service,
            "profile": profile_name,
            "region": region,
            "client_type": str(type(client).__name__),
            "availability": availability.value,
            "message": f"Successfully created {service} client"
        }
        
    except AWSServiceError as e:
        logger.error(f"Service error testing {service} client: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except AWSProfileNotFoundError as e:
        logger.error(f"Profile not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error testing {service} client: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Client test failed: {str(e)}")


@router.get("/cache/stats",
           summary="Get client cache statistics",
           description="Get statistics about the client cache")
@rate_limit_default()
async def get_cache_stats(
    request: Request,
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    Get client cache statistics
    
    Returns:
        Cache statistics and health information
    """
    try:
        stats = client_factory.get_cache_stats()
        
        return {
            "cache_stats": stats,
            "timestamp": "2025-08-20T15:20:23Z"  # Use actual timestamp in production
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/cache/cleanup",
            summary="Clean up expired clients",
            description="Manually trigger cleanup of expired clients from cache")
@rate_limit_default()
async def cleanup_cache(
    request: Request,
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    Manually trigger cache cleanup
    
    Returns:
        Cleanup results
    """
    try:
        cleaned_count = client_factory.cleanup_expired_clients()
        stats = client_factory.get_cache_stats()
        
        return {
            "cleanup_results": {
                "expired_clients_removed": cleaned_count,
                "remaining_active_clients": stats["active_clients"]
            },
            "message": f"Successfully cleaned up {cleaned_count} expired clients"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache cleanup failed: {str(e)}")


@router.get("/matrix",
           summary="Service-Region availability matrix",
           description="Get availability matrix for multiple services across regions")
@rate_limit_default()
async def get_availability_matrix(
    request: Request,
    services: Optional[str] = Query(None, description="Comma-separated list of services"),
    regions: Optional[str] = Query(None, description="Comma-separated list of regions"),
    client_factory: AWSServiceClientFactory = Depends(get_client_factory)
) -> Dict[str, Any]:
    """
    Get service availability matrix across multiple regions
    
    Args:
        services: Comma-separated list of services to check
        regions: Comma-separated list of regions to check
        
    Returns:
        Availability matrix with service-region combinations
    """
    try:
        # Parse input parameters
        service_list = services.split(',') if services else ['ec2', 's3', 'rds', 'lambda']
        region_list = regions.split(',') if regions else ['us-east-1', 'us-west-2', 'eu-west-1']
        
        # Clean up the lists
        service_list = [s.strip() for s in service_list if s.strip()]
        region_list = [r.strip() for r in region_list if r.strip()]
        
        # Build availability matrix
        matrix = {}
        for service in service_list:
            matrix[service] = {}
            for region in region_list:
                availability = await client_factory.check_service_availability(service, region)
                matrix[service][region] = {
                    "availability": availability.value,
                    "available": availability == RegionAvailability.AVAILABLE
                }
        
        return {
            "availability_matrix": matrix,
            "services_checked": service_list,
            "regions_checked": region_list,
            "total_combinations": len(service_list) * len(region_list)
        }
        
    except Exception as e:
        logger.error(f"Error generating availability matrix: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Matrix generation failed: {str(e)}")
