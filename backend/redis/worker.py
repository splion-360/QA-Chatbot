#!/usr/bin/env python3
"""
RQ Worker script for processing chat messages.

Usage:
    python redis/worker.py

Environment Variables:
    REDIS_HOST: Redis server host (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_DB: Redis database number (default: 0)
    REDIS_PASSWORD: Redis password (optional)
"""

import logging
import sys
from pathlib import Path

import redis
from rq import Connection, Worker

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("worker.log")
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main worker function."""
    
    # Redis connection
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password if settings.redis_password else None,
        decode_responses=True
    )
    
    logger.info(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
    
    try:
        # Test Redis connection
        redis_client.ping()
        logger.info("Successfully connected to Redis")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)
    
    # Start worker
    with Connection(redis_client):
        worker = Worker(["chat_tasks"], connection=redis_client)
        logger.info("Starting RQ worker for 'chat_tasks' queue...")
        logger.info("Press Ctrl+C to stop the worker")
        
        try:
            worker.work()
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()