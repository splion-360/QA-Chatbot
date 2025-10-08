import time
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse, HealthCheck


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Send a message to the chatbot and get a response."""
    
    start_time = time.time()
    
    try:
        # TODO: Implement actual AI processing here
        # For now, return a simple echo response
        response_content = f"Echo: {request.message}"
        
        response_message = ChatMessage(
            id=str(int(time.time() * 1000)),  # Simple ID generation
            content=response_content,
            role="assistant",
            timestamp=datetime.now()
        )
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            message=response_message,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version
    )