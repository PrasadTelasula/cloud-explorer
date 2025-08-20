"""
Test configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user data fixture"""
    return {
        "username": "testuser",
        "email": "test@example.com"
    }
