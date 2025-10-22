import pytest
from fastapi import status


class TestChatEndpoints:
    """Test cases for chat endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/chat/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_send_message_success(self, client, sample_chat_request):
        """Test successful message sending."""
        response = client.post("/api/v1/chat/message", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check response structure
        assert "message" in data
        assert "processing_time" in data
        
        # Check message structure
        message = data["message"]
        assert message["role"] == "assistant"
        assert "id" in message
        assert "content" in message
        assert "timestamp" in message
        
        # Check content contains the echo
        assert sample_chat_request["message"] in message["content"]

    def test_send_message_empty_message(self, client):
        """Test sending empty message."""
        response = client.post("/api/v1/chat/message", json={"message": ""})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_message_too_long(self, client):
        """Test sending message that's too long."""
        long_message = "x" * 1001  # Exceeds 1000 character limit
        response = client.post("/api/v1/chat/message", json={"message": long_message})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_message_missing_field(self, client):
        """Test sending request without message field."""
        response = client.post("/api/v1/chat/message", json={})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs_url" in data


class TestChatModels:
    """Test cases for chat models."""

    def test_chat_message_validation(self):
        """Test ChatMessage model validation."""
        from app.models.chat import ChatMessage
        from datetime import datetime
        
        # Valid message
        message = ChatMessage(
            id="test-123",
            content="Hello world",
            role="user",
            timestamp=datetime.now()
        )
        assert message.id == "test-123"
        assert message.content == "Hello world"
        assert message.role == "user"

    def test_chat_request_validation(self):
        """Test ChatRequest model validation."""
        from app.models.chat import ChatRequest
        
        # Valid request
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        
        # Invalid request - empty message
        with pytest.raises(ValueError):
            ChatRequest(message="")