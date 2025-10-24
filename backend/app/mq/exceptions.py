from datetime import timedelta

from rq.job import Job

from app.config import (
    REDIS_MAX_RETRY,
    REDIS_RETRY_INTERVALS,
    setup_logger,
)
from app.mq.queue import get_queue


logger = setup_logger("mq-exceptions")


class BaseException(Exception):
    """
    Base exception class for the project to enable MQ retries
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args)


class DocumentProcessingError(BaseException):
    def __init__(self, document_id: str, user_id: str, reason: str):
        self.document_id = document_id
        self.user_id = user_id
        self.reason = reason
        message = f"Document processing failed for '{document_id}' (user: {user_id}): {reason}"
        super().__init__(message)


class VectorizationError(BaseException):
    def __init__(self, document_id: str, reason: str):
        self.document_id = document_id
        self.reason = reason
        message = f"Vectorization failed for document '{document_id}': {reason}"
        super().__init__(message)


class DatabaseError(BaseException):
    def __init__(self, operation: str, table: str, reason: str = None):
        self.operation = operation
        self.table = table
        message = f"Database {operation} failed on '{table}': {(reason or 'No information')}"
        super().__init__(message)


def generic_exception_handler(job: Job, exc_type, exc_value, traceback):
    """
    Enqueues the failed jobs if any known exception is raised.
    Exceptions must be one of (DatabaseError | VectorizationError | DocumentProcessingError) to trigger
    retry

    Args:

    Returns:

    """
    retry_count = getattr(job.meta, "retry_count", 0)
    max_retries = REDIS_MAX_RETRY

    if not issubclass(exc_type, BaseException):
        return

    if retry_count < max_retries:
        if retry_count < len(REDIS_RETRY_INTERVALS):
            delay = REDIS_RETRY_INTERVALS[retry_count]
        else:
            base_interval = (
                REDIS_RETRY_INTERVALS[-1] if REDIS_RETRY_INTERVALS else 10
            )
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
    else:
        logger.error(
            f"Job {job.id} exhausted all {max_retries} retry attempts. Moving to DLQ"
        )
        return False
