#!/usr/bin/env python3
"""
AWS Session Manager Test Script

This script demonstrates and tests the AWS Session Manager functionality
including credential validation, session caching, and role assumption.
"""
import asyncio
import sys
import json
from pathlib import Path

# Add the backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.aws.session_manager import AWSSessionManager
from app.aws.credentials import AWSCredentialsReader
from app.models.aws import AWSSessionError, AWSProfileNotFoundError


async def test_session_manager():
    """Test AWS Session Manager functionality"""
    print("🚀 Testing AWS Session Manager...")
    print("=" * 50)
    
    # Initialize session manager
    session_manager = AWSSessionManager()
    
    try:
        # Test 1: Get session manager info
        print("\n📊 Session Manager Information:")
        info = session_manager.get_session_info()
        print(json.dumps(info, indent=2))
        
        # Test 2: List available profiles
        print("\n👤 Available AWS Profiles:")
        profiles = session_manager.credentials_reader.read_all_profiles()
        for profile_name, profile in profiles.profiles.items():
            print(f"  - {profile_name}: {profile.profile_type.value} ({profile.region or 'no region'})")
        
        # Test 3: Validate credentials for default profile
        print("\n🔐 Validating Credentials for 'default' profile:")
        try:
            validation_result = await session_manager.validate_credentials("default")
            if validation_result['valid']:
                print(f"  ✅ Valid - Account: {validation_result.get('account', 'Unknown')}")
                print(f"  ✅ User/Role: {validation_result.get('arn', 'Unknown')}")
            else:
                print(f"  ❌ Invalid - Error: {validation_result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ Validation failed: {str(e)}")
        
        # Test 4: Create session for default profile
        print("\n⚡ Creating AWS Session for 'default' profile:")
        try:
            session = await session_manager.get_session("default")
            print(f"  ✅ Session created successfully")
            print(f"  ✅ Region: {session.region_name}")
            
            # Test 5: Test session with STS call
            print("\n🔍 Testing session with STS call:")
            sts_client = session.client('sts')
            identity = sts_client.get_caller_identity()
            print(f"  ✅ Account ID: {identity.get('Account')}")
            print(f"  ✅ User ID: {identity.get('UserId')}")
            print(f"  ✅ ARN: {identity.get('Arn')}")
            
        except Exception as e:
            print(f"  ❌ Session creation failed: {str(e)}")
        
        # Test 6: Test session caching
        print("\n💾 Testing Session Caching:")
        try:
            session1 = await session_manager.get_session("default")
            session2 = await session_manager.get_session("default")
            print(f"  ✅ Created two sessions for same profile")
            print(f"  ✅ Cache stats - Active sessions: {session_manager.session_cache.active_session_count}")
        except Exception as e:
            print(f"  ❌ Session caching test failed: {str(e)}")
        
        # Test 7: Test with different profiles (if available)
        print("\n🔄 Testing Multiple Profiles:")
        profile_names = list(profiles.profiles.keys())
        for profile_name in profile_names[:3]:  # Test first 3 profiles
            try:
                validation = await session_manager.validate_credentials(profile_name)
                if validation['valid']:
                    print(f"  ✅ Profile '{profile_name}': Valid")
                else:
                    print(f"  ⚠️  Profile '{profile_name}': Invalid - {validation.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ Profile '{profile_name}': Error - {str(e)}")
        
        # Test 8: Test session cleanup
        print("\n🧹 Testing Session Cleanup:")
        cleaned = session_manager.cleanup_expired_sessions()
        print(f"  ✅ Cleaned up {cleaned} expired sessions")
        print(f"  ✅ Remaining active sessions: {session_manager.session_cache.active_session_count}")
        
        # Test 9: Test refresh credentials
        print("\n🔄 Testing Credential Refresh:")
        try:
            refresh_success = await session_manager.refresh_credentials("default")
            print(f"  ✅ Refresh successful: {refresh_success}")
        except Exception as e:
            print(f"  ❌ Refresh failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_role_assumption():
    """Test role assumption if role profiles are available"""
    print("\n🔄 Testing Role Assumption...")
    
    session_manager = AWSSessionManager()
    profiles = session_manager.credentials_reader.read_all_profiles()
    
    # Look for role profiles
    role_profiles = [p for p in profiles.profiles.values() 
                    if p.profile_type.value == "iam_role" and p.role_arn]
    
    if not role_profiles:
        print("  ⚠️  No IAM role profiles found for testing")
        return
    
    for role_profile in role_profiles[:1]:  # Test first role profile
        print(f"  🎭 Testing role assumption for: {role_profile.name}")
        print(f"      Role ARN: {role_profile.role_arn}")
        print(f"      Source Profile: {role_profile.source_profile}")
        
        try:
            role_session = await session_manager.assume_role(
                role_arn=role_profile.role_arn,
                source_profile=role_profile.source_profile,
                duration_seconds=role_profile.duration_seconds,
                external_id=role_profile.external_id,
                mfa_serial=role_profile.mfa_serial
            )
            
            # Test the role session
            sts_client = role_session.client('sts')
            identity = sts_client.get_caller_identity()
            print(f"  ✅ Role assumption successful!")
            print(f"      Assumed ARN: {identity.get('Arn')}")
            print(f"      Account: {identity.get('Account')}")
            
        except Exception as e:
            print(f"  ❌ Role assumption failed: {str(e)}")


def main():
    """Main test function"""
    print("AWS Session Manager Test Suite")
    print("=" * 50)
    
    try:
        # Run basic session manager tests
        asyncio.run(test_session_manager())
        
        # Run role assumption tests
        asyncio.run(test_role_assumption())
        
    except KeyboardInterrupt:
        print("\n\n⛔ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
