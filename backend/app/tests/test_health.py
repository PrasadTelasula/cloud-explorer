"""
Test health endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Cloud Explorer API"
    assert data["version"] == "0.1.0"
    assert "docs" in data
    assert "health" in data


def test_health_check(client: TestClient):
    """Test basic health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "0.1.0"


def test_detailed_health_check(client: TestClient):
    """Test detailed health check endpoint"""
    response = client.get("/api/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "api" in data
    assert "configuration" in data
    assert data["api"]["name"] == "Cloud Explorer API"
