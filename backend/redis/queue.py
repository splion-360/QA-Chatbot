import time
from datetime import datetime

import redis
from rq import Queue

from app.core.config import settings


# Redis connection
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password if settings.redis_password else None,
    decode_responses=True
)

# RQ Queue
task_queue = Queue("chat_tasks", connection=redis_client)


def process_chat_message(message: str, user_id: str = None) -> dict:
    """
    Process a chat message asynchronously.
    
    Args:
        message: The user message to process
        user_id: Optional user identifier
        
    Returns:
        Dictionary containing the processed response
    """
    
    # Simulate processing time
    time.sleep(2)
    
    # TODO: Replace with actual AI/RAG processing
    response = {
        "id": str(int(time.time() * 1000)),
        "content": f"Processed: {message}",
        "role": "assistant",
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "processing_method": "async_queue"
    }
    
    return response


def enqueue_chat_message(message: str, user_id: str = None) -> str:
    """
    Enqueue a chat message for processing.
    
    Args:
        message: The user message to process
        user_id: Optional user identifier
        
    Returns:
        Job ID for tracking the task
    """
    
    job = task_queue.enqueue(
        process_chat_message,
        message,
        user_id,
        job_timeout="30s",
        result_ttl=3600  # Keep result for 1 hour
    )
    
    return job.id


def get_job_result(job_id: str) -> dict:
    """
    Get the result of a queued job.
    
    Args:
        job_id: The job identifier
        
    Returns:
        Dictionary containing job status and result
    """
    
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=redis_client)
        
        return {
            "job_id": job_id,
            "status": job.get_status(),
            "result": job.result,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
        
    except Exception as e:
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }


def get_queue_info() -> dict:
    """
    Get information about the task queue.
    
    Returns:
        Dictionary containing queue statistics
    """
    
    return {
        "queue_name": task_queue.name,
        "pending_jobs": len(task_queue),
        "failed_jobs": len(task_queue.failed_job_registry),
        "workers": len(task_queue.workers),
        "redis_connected": redis_client.ping()
    }