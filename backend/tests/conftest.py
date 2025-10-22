import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    """Create FastAPI test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {"message": "Hello, how are you?"}


@pytest.fixture
def sample_chat_message():
    """Sample chat message for testing."""
    return {
        "id": "test-123",
        "content": "Hello, how are you?",
        "role": "user",
        "timestamp": "2024-01-01T00:00:00Z"
    }