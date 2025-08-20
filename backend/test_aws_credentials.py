"""
Test script for AWS Credentials Reader
"""
import os
import tempfile
from pathlib import Path
from textwrap import dedent

from app.aws.credentials import AWSCredentialsReader
from app.models.aws import AWSCredentialError, AWSProfileNotFoundError


def create_test_aws_files():
    """Create test AWS configuration files"""
    # Create temporary directory for test files
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create test credentials file
    credentials_content = dedent("""
        [default]
        aws_access_key_id = AKIAIOSFODNN7EXAMPLE
        aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        
        [user2]
        aws_access_key_id = AKIAI44QH8DHBEXAMPLE
        aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
        aws_session_token = temporary_session_token
        
        [sso-user]
        # SSO users don't have credentials in this file
    """).strip()
    
    credentials_file = temp_dir / "credentials"
    credentials_file.write_text(credentials_content)
    
    # Create test config file
    config_content = dedent("""
        [default]
        region = us-west-2
        output = json
        
        [profile user2]
        region = us-east-1
        output = table
        
        [profile production]
        region = us-west-2
        role_arn = arn:aws:iam::123456789012:role/ProductionRole
        source_profile = default
        mfa_serial = arn:aws:iam::123456789012:mfa/user
        duration_seconds = 3600
        
        [profile sso-user]
        sso_start_url = https://my-sso-portal.awsapps.com/start
        sso_region = us-east-1
        sso_account_id = 123456789012
        sso_role_name = ReadOnlyAccess
        region = us-west-2
        
        [profile federated]
        web_identity_token_file = /tmp/token
        role_arn = arn:aws:iam::123456789012:role/FederatedRole
        region = eu-west-1
    """).strip()
    
    config_file = temp_dir / "config"
    config_file.write_text(config_content)
    
    return temp_dir


def test_aws_credentials_reader():
    """Test the AWS credentials reader functionality"""
    print("🧪 Testing AWS Credentials Reader")
    print("=" * 50)
    
    # Create test files
    test_aws_dir = create_test_aws_files()
    print(f"📁 Created test AWS files in: {test_aws_dir}")
    
    try:
        # Initialize credentials reader with test directory
        reader = AWSCredentialsReader(aws_dir=test_aws_dir)
        
        # Test getting profile names
        print("\n📋 Testing profile discovery...")
        profile_names = reader.get_profile_names()
        print(f"Found profiles: {profile_names}")
        
        # Test reading all profiles
        print("\n📖 Testing profile reading...")
        profile_collection = reader.read_all_profiles()
        print(f"Total profiles: {profile_collection.profile_count}")
        print(f"Valid profiles: {profile_collection.valid_profile_count}")
        
        # Test individual profiles
        print("\n🔍 Testing individual profiles...")
        for profile_name in profile_names:
            try:
                profile = reader.read_profile(profile_name)
                print(f"✅ {profile_name}: {profile.profile_type.value}, valid={profile.is_valid}, mfa={profile.requires_mfa}")
            except (AWSProfileNotFoundError, AWSCredentialError) as e:
                print(f"❌ {profile_name}: {e}")
        
        # Test profile validation
        print("\n🔒 Testing profile validation...")
        for profile_name in profile_names:
            is_valid, error = reader.validate_profile(profile_name)
            status = "✅" if is_valid else "❌"
            print(f"{status} {profile_name}: {'Valid' if is_valid else error}")
        
        # Test profile chains
        print("\n🔗 Testing profile chains...")
        for profile_name in ['production', 'default']:
            try:
                chain = reader.resolve_profile_chain(profile_name)
                print(f"Chain for {profile_name}: {' -> '.join(chain)}")
            except AWSCredentialError as e:
                print(f"❌ Chain error for {profile_name}: {e}")
        
        # Test effective regions
        print("\n🌍 Testing effective regions...")
        for profile_name in profile_names:
            region = reader.get_effective_region(profile_name)
            print(f"Region for {profile_name}: {region}")
        
        # Test cache info
        print("\n🗂️ Cache information:")
        cache_info = reader.get_cache_info()
        for key, value in cache_info.items():
            print(f"  {key}: {value}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    
    finally:
        # Cleanup test files
        import shutil
        shutil.rmtree(test_aws_dir)
        print(f"\n🧹 Cleaned up test files")


if __name__ == "__main__":
    test_aws_credentials_reader()
