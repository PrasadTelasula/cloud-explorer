#!/usr/bin/env python3
"""
AWS Accounts API Test Script

This script demonstrates and tests the AWS Accounts API functionality
including profile listing, validation, and metadata retrieval.
"""
import asyncio
import sys
import json
from pathlib import Path

# Add the backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.routers.accounts import _build_account_profile, _get_profile_validation, _get_available_regions, _get_permissions_summary
from app.aws.session_manager import AWSSessionManager
from app.aws.client_factory import AWSServiceClientFactory
from app.models.aws import AWSSessionError, AWSProfileNotFoundError, AWSProfile
from fastapi.testclient import TestClient
from app.main import app


async def test_accounts_functionality():
    """Test AWS Accounts API core functionality"""
    print("🏦 Testing AWS Accounts API Core Functionality...")
    print("=" * 60)
    
    # Initialize dependencies
    session_manager = AWSSessionManager()
    client_factory = AWSServiceClientFactory()
    
    try:
        # Test 1: Get all profiles
        print("\n📋 Testing Profile Discovery:")
        
        profiles_data = session_manager.credentials_reader.read_all_profiles()
        print(f"  ✅ Found {len(profiles_data.profiles)} profiles")
        
        for profile_name, aws_profile in list(profiles_data.profiles.items())[:3]:  # Show first 3
            print(f"    - {profile_name} ({aws_profile.profile_type.value})")
            print(f"      Region: {aws_profile.region}")
            if aws_profile.role_arn:
                print(f"      Role ARN: {aws_profile.role_arn}")
            if aws_profile.sso_start_url:
                print(f"      SSO URL: {aws_profile.sso_start_url}")
        
        # Test 2: Test profile validation
        print("\n🔐 Testing Profile Validation:")
        
        # Test with first available profile
        first_profile_name = list(profiles_data.profiles.keys())[0]
        first_profile = list(profiles_data.profiles.values())[0]
        
        print(f"  🧪 Testing validation for profile: {first_profile_name}")
        
        validation_info = await _get_profile_validation(
            first_profile_name, session_manager, client_factory
        )
        
        print(f"  ✅ Validation status: {validation_info.status.value}")
        print(f"  ✅ Is valid: {validation_info.is_valid}")
        if validation_info.account_id:
            print(f"  ✅ Account ID: {validation_info.account_id}")
        if validation_info.user_arn:
            print(f"  ✅ User ARN: {validation_info.user_arn}")
        if validation_info.error:
            print(f"  ⚠️  Error: {validation_info.error}")
        
        # Test 3: Test available regions
        print("\n🌍 Testing Available Regions:")
        
        regions = await _get_available_regions(first_profile_name, client_factory)
        print(f"  ✅ Found {len(regions)} regions: {regions[:5]}{'...' if len(regions) > 5 else ''}")
        
        # Test 4: Test permissions summary (only if profile is valid)
        if validation_info.is_valid:
            print("\n🔑 Testing Permissions Summary:")
            print(f"  🧪 Testing permissions for profile: {first_profile_name}")
            
            permissions = await _get_permissions_summary(
                first_profile_name, validation_info, client_factory
            )
            
            if permissions:
                print(f"  ✅ Accessible services: {permissions.get('services', [])}")
                print(f"  ✅ Admin access: {permissions.get('admin_access', False)}")
                print(f"  ✅ Read-only access: {permissions.get('read_only', False)}")
                print(f"  ✅ Service count: {permissions.get('service_count', 0)}")
                if 'error' in permissions:
                    print(f"  ⚠️  Permission error: {permissions['error']}")
            else:
                print(f"  ⚠️  No permissions data available")
        else:
            print("\n🔑 Skipping Permissions Summary (profile invalid)")
        
        # Test 5: Test full account profile building
        print("\n🏗️  Testing Account Profile Building:")
        
        account_profile = await _build_account_profile(
            first_profile, session_manager, client_factory, is_default=(first_profile_name == "default")
        )
        
        print(f"  ✅ Profile name: {account_profile.profile_name}")
        print(f"  ✅ Profile type: {account_profile.profile_type.value}")
        print(f"  ✅ Is default: {account_profile.is_default}")
        print(f"  ✅ Available regions: {len(account_profile.available_regions)}")
        print(f"  ✅ Validation status: {account_profile.validation.status.value}")
        
        if account_profile.permissions_summary:
            print(f"  ✅ Permissions services: {account_profile.permissions_summary.get('services', [])}")
        
        # Test 6: Test multiple profiles
        print("\n🔍 Testing Multiple Profiles:")
        
        profile_types = {}
        valid_count = 0
        invalid_count = 0
        
        for profile_name, aws_profile in list(profiles_data.profiles.items())[:5]:  # Test first 5
            try:
                validation = await _get_profile_validation(profile_name, session_manager, client_factory)
                
                profile_type = aws_profile.profile_type.value
                profile_types[profile_type] = profile_types.get(profile_type, 0) + 1
                
                if validation.is_valid:
                    valid_count += 1
                    print(f"    ✅ {profile_name} ({profile_type}) - Valid")
                else:
                    invalid_count += 1
                    print(f"    ❌ {profile_name} ({profile_type}) - Invalid: {validation.error}")
                    
            except Exception as e:
                invalid_count += 1
                print(f"    ⚠️  {profile_name} - Error: {str(e)}")
        
        print(f"\n  📊 Summary:")
        print(f"    Valid profiles: {valid_count}")
        print(f"    Invalid profiles: {invalid_count}")
        print(f"    Profile types: {profile_types}")
        
        # Test 7: Test SSO profile handling
        print("\n🔐 Testing SSO Profile Handling:")
        
        sso_profiles = [
            (name, profile) for name, profile in profiles_data.profiles.items()
            if profile.profile_type.value == "SSO"
        ]
        
        if sso_profiles:
            sso_profile_name, sso_profile = sso_profiles[0]
            print(f"  🧪 Testing SSO profile: {sso_profile_name}")
            
            sso_validation = await _get_profile_validation(sso_profile_name, session_manager, client_factory)
            print(f"  ✅ SSO validation: {sso_validation.status.value}")
            
            if sso_profile.sso_start_url:
                print(f"  ✅ SSO start URL: {sso_profile.sso_start_url}")
            if sso_profile.sso_session:
                print(f"  ✅ SSO session: {sso_profile.sso_session}")
        else:
            print(f"  ℹ️  No SSO profiles found")
        
        print("\n" + "=" * 60)
        print("✅ All accounts functionality tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    print("🚀 AWS Accounts API Test Suite")
    print("=" * 60)
    
    try:
        # Run accounts functionality tests
        asyncio.run(test_accounts_functionality())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


async def test_accounts_api():
    """Test AWS Accounts API functionality"""
    print("🏦 Testing AWS Accounts API...")
    print("=" * 60)
    
    # Initialize dependencies
    session_manager = AWSSessionManager()
    client_factory = AWSServiceClientFactory()
    
    try:
        # Test 1: Basic accounts listing (without validation for speed)
        print("\n📋 Testing Basic Accounts Listing (no validation):")
        
        from unittest.mock import MagicMock
        
        # Create a proper mock request object
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "localhost"
        
        response = await list_accounts(
            request=mock_request,
            include_invalid=True,
            validate_credentials=False,
            include_permissions=False,
            use_cache=False,
            session_manager=session_manager,
            client_factory=client_factory
        )
        
        print(f"  ✅ Found {response.total_profiles} profiles")
        print(f"  ✅ Default profile: {response.default_profile}")
        print(f"  ✅ Cache info: {response.cache_info}")
        
        print(f"\n  📋 Profile Summary:")
        for profile in response.profiles[:3]:  # Show first 3 profiles
            print(f"    - {profile.profile_name} ({profile.profile_type.value})")
            print(f"      Region: {profile.region}")
            print(f"      Validation: {profile.validation.status.value}")
            if profile.role_arn:
                print(f"      Role ARN: {profile.role_arn}")
            if profile.sso_start_url:
                print(f"      SSO URL: {profile.sso_start_url}")
        
        # Test 2: Accounts listing with credential validation
        print("\n🔐 Testing Accounts Listing with Credential Validation:")
        
        response_validated = await list_accounts(
            request=mock_request,
            include_invalid=True,
            validate_credentials=True,
            include_permissions=False,
            use_cache=False,
            session_manager=session_manager,
            client_factory=client_factory
        )
        
        print(f"  ✅ Total profiles: {response_validated.total_profiles}")
        print(f"  ✅ Valid profiles: {response_validated.valid_profiles}")
        print(f"  ✅ Invalid profiles: {response_validated.invalid_profiles}")
        
        print(f"\n  🔍 Validation Details:")
        for profile in response_validated.profiles[:3]:  # Show first 3
            validation = profile.validation
            print(f"    - {profile.profile_name}:")
            print(f"      Status: {validation.status.value}")
            print(f"      Valid: {validation.is_valid}")
            if validation.account_id:
                print(f"      Account ID: {validation.account_id}")
            if validation.user_arn:
                print(f"      User ARN: {validation.user_arn}")
            if validation.error:
                print(f"      Error: {validation.error}")
        
        # Test 3: Test caching
        print("\n💾 Testing Response Caching:")
        
        # First call (should generate cache)
        response_cache_1 = await list_accounts(
            request=MockRequest(),
            include_invalid=True,
            validate_credentials=False,
            include_permissions=False,
            use_cache=True,
            session_manager=session_manager,
            client_factory=client_factory
        )
        
        # Second call (should use cache)
        response_cache_2 = await list_accounts(
            request=MockRequest(),
            include_invalid=True,
            validate_credentials=False,
            include_permissions=False,
            use_cache=True,
            session_manager=session_manager,
            client_factory=client_factory
        )
        
        print(f"  ✅ First call cache status: {response_cache_1.cache_info['cached']}")
        print(f"  ✅ Second call cache status: {response_cache_2.cache_info['cached']}")
        print(f"  ✅ Cache age: {response_cache_2.cache_info.get('cache_age_seconds', 0)} seconds")
        
        # Test 4: Test with permissions (slower but more detailed)
        print("\n🔑 Testing with Permissions Summary (first valid profile only):")
        
        # Find first valid profile
        valid_profiles = [p for p in response_validated.profiles if p.validation.is_valid]
        
        if valid_profiles:
            valid_profile_name = valid_profiles[0].profile_name
            print(f"  🧪 Testing permissions for profile: {valid_profile_name}")
            
            response_permissions = await list_accounts(
                request=MockRequest(),
                include_invalid=False,
                validate_credentials=True,
                include_permissions=True,
                use_cache=False,
                session_manager=session_manager,
                client_factory=client_factory
            )
            
            target_profile = next(
                (p for p in response_permissions.profiles if p.profile_name == valid_profile_name), 
                None
            )
            
            if target_profile and target_profile.permissions_summary:
                permissions = target_profile.permissions_summary
                print(f"  ✅ Accessible services: {permissions.get('services', [])}")
                print(f"  ✅ Admin access: {permissions.get('admin_access', False)}")
                print(f"  ✅ Read-only access: {permissions.get('read_only', False)}")
                print(f"  ✅ Service count: {permissions.get('service_count', 0)}")
            else:
                print(f"  ⚠️  No permissions data available")
        else:
            print(f"  ⚠️  No valid profiles found for permissions testing")
        
        # Test 5: Test profile filtering
        print("\n🔍 Testing Profile Filtering:")
        
        # Only valid profiles
        response_valid_only = await list_accounts(
            request=MockRequest(),
            include_invalid=False,
            validate_credentials=True,
            include_permissions=False,
            use_cache=False,
            session_manager=session_manager,
            client_factory=client_factory
        )
        
        print(f"  ✅ Total profiles (all): {response_validated.total_profiles}")
        print(f"  ✅ Valid profiles only: {response_valid_only.total_profiles}")
        print(f"  ✅ Filtered out: {response_validated.total_profiles - response_valid_only.total_profiles} invalid profiles")
        
        # Test 6: Test cache clearing
        print("\n🧹 Testing Cache Clearing:")
        
        cache_result = await clear_accounts_cache(MockRequest())
        print(f"  ✅ Cleared entries: {cache_result['cleared_entries']}")
        print(f"  ✅ Cache duration: {cache_result['cache_duration_seconds']} seconds")
        
        # Test 7: Test different profile types
        print("\n🔍 Testing Profile Type Distribution:")
        
        type_counts = {}
        for profile in response_validated.profiles:
            profile_type = profile.profile_type.value
            type_counts[profile_type] = type_counts.get(profile_type, 0) + 1
        
        print(f"  📊 Profile Type Distribution:")
        for profile_type, count in type_counts.items():
            print(f"    - {profile_type}: {count} profiles")
        
        print("\n" + "=" * 60)
        print("✅ All accounts API tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    print("🚀 AWS Accounts API Test Suite")
    print("=" * 60)
    
    try:
        # Run accounts API tests
        asyncio.run(test_accounts_api())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
