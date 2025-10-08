from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model."""
    
    id: str = Field(..., description="Unique message identifier")
    content: str = Field(..., description="Message content")
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class ChatRequest(BaseModel):
    """Chat request model."""
    
    message: str = Field(..., min_length=1, max_length=1000, description="User message")


class ChatResponse(BaseModel):
    """Chat response model."""
    
    message: ChatMessage = Field(..., description="Assistant response message")
    processing_time: float = Field(..., description="Processing time in seconds")


class ChatHistory(BaseModel):
    """Chat history model."""
    
    messages: list[ChatMessage] = Field(default_factory=list, description="List of chat messages")
    total_count: int = Field(..., description="Total number of messages")


class HealthCheck(BaseModel):
    """Health check response model."""
    
    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")
    version: str = Field(..., description="API version")