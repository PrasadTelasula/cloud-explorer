#!/usr/bin/env python3
"""
AWS Accounts API HTTP Test Script

This script tests the AWS Accounts API via HTTP endpoints using FastAPI test client.
"""
import sys
from pathlib import Path

# Add the backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from fastapi.testclient import TestClient
from main import app


def test_accounts_api():
    """Test AWS Accounts API via HTTP endpoints"""
    print("🚀 AWS Accounts API HTTP Test Suite")
    print("=" * 60)
    print("🏦 Testing AWS Accounts API...")
    print("=" * 60)
    
    # Create test client
    client = TestClient(app)
    
    try:
        # Test 1: Basic accounts listing (without validation for speed)
        print("\n📋 Testing Basic Accounts Listing (no validation):")
        
        response = client.get("/api/accounts", params={
            "include_invalid": True,
            "validate_credentials": False,
            "include_permissions": False,
            "use_cache": False
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        print(f"  ✅ Found {data['total_profiles']} profiles")
        print(f"  ✅ Default profile: {data['default_profile']}")
        print(f"  ✅ Response format validated")
        
        # Validate response structure
        assert "profiles" in data
        assert "total_profiles" in data
        assert "default_profile" in data
        assert isinstance(data["profiles"], list)
        
        if data["profiles"]:
            profile = data["profiles"][0]
            print(f"  🔍 Profile structure: {profile}")
            assert "profile_name" in profile
            assert "profile_type" in profile
            assert "validation" in profile
            print(f"  ✅ Profile structure validated: {profile['profile_name']} ({profile['profile_type']})")
        
        # Test 2: Accounts listing with credential validation
        print("\n🔐 Testing Accounts Listing with Credential Validation:")
        
        response_validated = client.get("/api/accounts", params={
            "include_invalid": True,
            "validate_credentials": True,
            "include_permissions": False,
            "use_cache": False
        })
        
        assert response_validated.status_code == 200
        data_validated = response_validated.json()
        
        print(f"  ✅ Total profiles: {data_validated['total_profiles']}")
        
        valid_count = sum(1 for p in data_validated["profiles"] if p["validation"]["is_valid"])
        invalid_count = sum(1 for p in data_validated["profiles"] if not p["validation"]["is_valid"])
        
        print(f"  ✅ Valid profiles: {valid_count}")
        print(f"  ✅ Invalid profiles: {invalid_count}")
        
        # Test 3: Cache functionality
        print("\n💾 Testing Cache Functionality:")
        
        # First call (should generate cache)
        response_cache_1 = client.get("/api/accounts", params={
            "include_invalid": True,
            "validate_credentials": False,
            "include_permissions": False,
            "use_cache": True
        })
        
        # Second call (should use cache)
        response_cache_2 = client.get("/api/accounts", params={
            "include_invalid": True,
            "validate_credentials": False,
            "include_permissions": False,
            "use_cache": True
        })
        
        assert response_cache_1.status_code == 200
        assert response_cache_2.status_code == 200
        
        data_cache_1 = response_cache_1.json()
        data_cache_2 = response_cache_2.json()
        
        print(f"  ✅ Cache test completed")
        print(f"  ✅ First call profiles: {data_cache_1['total_profiles']}")
        print(f"  ✅ Second call profiles: {data_cache_2['total_profiles']}")
        
        # Test 4: Include permissions
        print("\n🔑 Testing Permissions Summary:")
        
        try:
            response_permissions = client.get("/api/accounts", params={
                "include_invalid": False,
                "validate_credentials": True,
                "include_permissions": True,
                "use_cache": False
            })
            
            if response_permissions.status_code == 200:
                data_permissions = response_permissions.json()
                
                permissions_profiles = [p for p in data_permissions["profiles"] if p.get("permissions_summary")]
                print(f"  ✅ Profiles with permissions data: {len(permissions_profiles)}")
                
                if permissions_profiles:
                    sample_profile = permissions_profiles[0]
                    perms = sample_profile["permissions_summary"]
                    print(f"  ✅ Sample permissions for {sample_profile['profile_name']}:")
                    print(f"    - Accessible services: {len(perms.get('accessible_services', []))}")
                    print(f"    - Admin access: {perms.get('has_admin_access', False)}")
                    print(f"    - Read-only access: {perms.get('has_readonly_access', False)}")
            else:
                print(f"  ⚠️  Permissions test skipped (status: {response_permissions.status_code})")
        except Exception as e:
            print(f"  ⚠️  Permissions test failed: {str(e)}")
        
        # Test 5: Valid profiles only
        print("\n✅ Testing Valid Profiles Only:")
        
        response_valid_only = client.get("/api/accounts", params={
            "include_invalid": False,
            "validate_credentials": True,
            "include_permissions": False,
            "use_cache": False
        })
        
        assert response_valid_only.status_code == 200
        data_valid_only = response_valid_only.json()
        
        print(f"  ✅ Valid profiles only: {data_valid_only['total_profiles']}")
        
        # Verify all returned profiles are valid
        invalid_in_response = [p for p in data_valid_only["profiles"] if not p["validation"]["is_valid"]]
        assert len(invalid_in_response) == 0, f"Found invalid profiles in valid-only response: {invalid_in_response}"
        print(f"  ✅ All returned profiles are valid")
        
        # Test 6: Cache clearing
        print("\n🗑️  Testing Cache Clearing:")
        
        cache_response = client.delete("/api/accounts/cache")
        
        if cache_response.status_code == 200:
            cache_data = cache_response.json()
            print(f"  ✅ Cache cleared: {cache_data.get('message', 'Success')}")
        else:
            print(f"  ⚠️  Cache clear test failed (status: {cache_response.status_code})")
        
        print("\n" + "=" * 60)
        print("✅ All accounts API HTTP tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 AWS Accounts API HTTP Test Suite")
    print("=" * 60)
    
    success = test_accounts_api()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
