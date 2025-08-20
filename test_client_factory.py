#!/usr/bin/env python3
"""
AWS Client Factory Test Script

This script demonstrates and tests the AWS Client Factory functionality
including service clients, regional management, and caching.
"""
import asyncio
import sys
import json
from pathlib import Path

# Add the backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.aws.client_factory import AWSServiceClientFactory, AWSServiceType, AWSServiceError
from app.aws.session_manager import AWSSessionManager
from app.models.aws import AWSSessionError, AWSProfileNotFoundError


async def test_client_factory():
    """Test AWS Client Factory functionality"""
    print("🏭 Testing AWS Client Factory...")
    print("=" * 60)
    
    # Initialize client factory
    client_factory = AWSServiceClientFactory()
    
    try:
        # Test 1: Get client factory info
        print("\n📊 Client Factory Information:")
        stats = client_factory.get_cache_stats()
        print(json.dumps(stats, indent=2))
        
        # Test 2: Test service availability checking
        print("\n🌍 Testing Service Availability:")
        test_services = ['s3', 'ec2', 'lambda', 'rds']
        test_regions = ['us-east-1', 'eu-west-1', 'ap-southeast-1']
        
        for service in test_services:
            print(f"\n  Service: {service}")
            for region in test_regions:
                try:
                    availability = await client_factory.check_service_availability(service, region)
                    print(f"    {region}: {availability.value}")
                except Exception as e:
                    print(f"    {region}: Error - {str(e)}")
        
        # Test 3: Get available regions for services
        print("\n📍 Available Regions for Services:")
        for service in ['s3', 'ec2', 'lambda'][:2]:  # Test first 2
            try:
                regions = await client_factory.get_available_regions(service)
                print(f"  {service}: {len(regions)} regions - {regions[:5]}{'...' if len(regions) > 5 else ''}")
            except Exception as e:
                print(f"  {service}: Error - {str(e)}")
        
        # Test 4: Create S3 client (most likely to work)
        print("\n🪣 Testing S3 Client Creation:")
        try:
            s3_client = await client_factory.get_client(
                service_name=AWSServiceType.S3,
                profile_name="default",
                region="us-east-1"
            )
            print(f"  ✅ S3 client created successfully: {type(s3_client).__name__}")
            
            # Test the client with a list buckets call
            print("  🧪 Testing S3 client with list_buckets:")
            try:
                response = s3_client.list_buckets()
                bucket_count = len(response.get('Buckets', []))
                print(f"  ✅ Found {bucket_count} S3 buckets")
            except Exception as e:
                print(f"  ⚠️  S3 list_buckets failed (may be expected): {str(e)}")
                
        except Exception as e:
            print(f"  ❌ S3 client creation failed: {str(e)}")
        
        # Test 5: Create EC2 client
        print("\n🖥️  Testing EC2 Client Creation:")
        try:
            ec2_client = await client_factory.get_client(
                service_name="ec2",
                profile_name="default",
                region="us-east-1"
            )
            print(f"  ✅ EC2 client created successfully: {type(ec2_client).__name__}")
            
            # Test the client with describe regions
            print("  🧪 Testing EC2 client with describe_regions:")
            try:
                response = ec2_client.describe_regions(MaxResults=5)
                region_count = len(response.get('Regions', []))
                print(f"  ✅ Found {region_count} regions")
            except Exception as e:
                print(f"  ⚠️  EC2 describe_regions failed (may be expected): {str(e)}")
                
        except Exception as e:
            print(f"  ❌ EC2 client creation failed: {str(e)}")
        
        # Test 6: Test client caching
        print("\n💾 Testing Client Caching:")
        try:
            # Create the same S3 client again
            s3_client_2 = await client_factory.get_client(
                service_name="s3",
                profile_name="default", 
                region="us-east-1"
            )
            print(f"  ✅ Second S3 client created")
            
            # Check cache stats
            stats_after = client_factory.get_cache_stats()
            print(f"  ✅ Cache stats: {stats_after['total_cached_clients']} total, {stats_after['active_clients']} active")
            
        except Exception as e:
            print(f"  ❌ Client caching test failed: {str(e)}")
        
        # Test 7: Test multiple regions
        print("\n🌐 Testing Multiple Regions:")
        regions_to_test = ['us-east-1', 'us-west-2', 'eu-west-1']
        
        for region in regions_to_test:
            try:
                sts_client = await client_factory.get_client(
                    service_name="sts",
                    profile_name="default",
                    region=region
                )
                print(f"  ✅ STS client created for {region}")
                
                # Test with get_caller_identity
                try:
                    identity = sts_client.get_caller_identity()
                    account = identity.get('Account', 'Unknown')
                    print(f"    Account: {account}")
                except Exception as e:
                    print(f"    ⚠️  STS call failed: {str(e)}")
                    
            except Exception as e:
                print(f"  ❌ STS client creation failed for {region}: {str(e)}")
        
        # Test 8: Test cache cleanup
        print("\n🧹 Testing Cache Cleanup:")
        try:
            cleaned = client_factory.cleanup_expired_clients()
            stats_final = client_factory.get_cache_stats()
            print(f"  ✅ Cleaned up {cleaned} expired clients")
            print(f"  ✅ Final cache stats: {json.dumps(stats_final, indent=2)}")
        except Exception as e:
            print(f"  ❌ Cache cleanup test failed: {str(e)}")
        
        # Test 9: Test error handling
        print("\n⚠️  Testing Error Handling:")
        try:
            # Try to create client for non-existent profile
            await client_factory.get_client(
                service_name="s3",
                profile_name="non-existent-profile",
                region="us-east-1"
            )
            print("  ❌ Should have failed with non-existent profile")
        except AWSProfileNotFoundError:
            print("  ✅ Correctly handled non-existent profile")
        except Exception as e:
            print(f"  ⚠️  Unexpected error (may be normal): {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ All client factory tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_service_types():
    """Test service type enumeration"""
    print("\n🔧 Testing Service Types:")
    print("=" * 40)
    
    service_categories = {
        "Compute": [AWSServiceType.EC2, AWSServiceType.LAMBDA, AWSServiceType.ECS],
        "Storage": [AWSServiceType.S3, AWSServiceType.EBS, AWSServiceType.EFS],
        "Database": [AWSServiceType.RDS, AWSServiceType.DYNAMODB],
        "Security": [AWSServiceType.IAM, AWSServiceType.STS, AWSServiceType.KMS]
    }
    
    for category, services in service_categories.items():
        print(f"\n{category}:")
        for service in services:
            print(f"  - {service.name}: {service.value}")


def main():
    """Main test function"""
    print("🚀 AWS Client Factory Test Suite")
    print("=" * 60)
    
    try:
        # Run service types test first
        asyncio.run(test_service_types())
        
        # Run main client factory tests
        asyncio.run(test_client_factory())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
