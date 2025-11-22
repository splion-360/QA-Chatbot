from datetime import timedelta

from rq.job import Job

from app.config import REDIS_MAX_RETRY, REDIS_RETRY_INTERVALS, setup_logger
from app.core.exceptions import (
    AppException,
    DatabaseError,
    DocumentProcessingError,
    VectorizationError,
)
from app.mq.queue import get_queue


logger = setup_logger("mq-exceptions")

__all__ = [
    "AppException",
    "DatabaseError",
    "DocumentProcessingError",
    "VectorizationError",
    "generic_exception_handler",
]


def generic_exception_handler(job: Job, exc_type, exc_value, traceback):
    retry_count = getattr(job.meta, "retry_count", 0)
    max_retries = REDIS_MAX_RETRY

    if not issubclass(exc_type, AppException):
        return

    if retry_count >= max_retries:
        logger.error(f"Job {job.id} exhausted all {max_retries} retry attempts. Moving to DLQ")
        return False

    if retry_count < len(REDIS_RETRY_INTERVALS):
        delay = REDIS_RETRY_INTERVALS[retry_count]
    else:
        base_interval = REDIS_RETRY_INTERVALS[-1] if REDIS_RETRY_INTERVALS else 10
        delay = min(base_interval * (2**retry_count), 300)

    logger.info(
        f"Retrying job {job.id} in {delay} seconds (attempt {retry_count + 1}/{max_retries})",
        "YELLOW",
    )

    queue_name = getattr(job.meta, "queue_name", "qa-chatbot")
    allow_retry = getattr(job.meta, "allow_retry", True)
    queue = get_queue(queue_name)

    another_job = queue.enqueue_in(
        timedelta(seconds=delay),
        job.func,
        args=job.args,
        kwargs=job.kwargs,
        job_timeout=job.timeout,
        meta={
            "retry_count": retry_count + 1,
            "queue_name": queue_name,
            "allow_retry": allow_retry,
        },
    )

    logger.info(f"Re-enqueued job as {another_job.id}", "BLUE")
    return True
