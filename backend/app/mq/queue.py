from rq import Queue
from rq.job import Job

from app.config import (
    REDIS_TIMEOUT,
    get_redis_client,
    setup_logger,
)


logger = setup_logger("redis-queue")

_queues = {}


def get_queue(queue_name: str = "qa-chatbot") -> Queue:
    global _queues
    if queue_name not in _queues:
        redis_client = get_redis_client()
        _queues[queue_name] = Queue(queue_name, connection=redis_client)
    return _queues[queue_name]


async def enqueue_task(
    func,
    args: list[any] = None,
    queue_name: str = "qa-chatbot",
    task_timeout: int = None,
    allow_retry: bool = True,
    **kwargs,
) -> str:
    queue = get_queue(queue_name)
    if not task_timeout or not isinstance(task_timeout, int):
        logger.info("No (or) invalid timestamp argument provided!!")
        logger.info(f"Using default timeout: {REDIS_TIMEOUT}")
        task_timeout = REDIS_TIMEOUT

    # Cap the task timeout to 30 minutes
    task_timeout = min(task_timeout, 1800)

    # Add metadata for retry handling
    meta = {
        "retry_count": 0,
        "queue_name": queue_name,
        "allow_retry": allow_retry,
    }

    job = queue.enqueue(
        func, args=(args or []), job_timeout=task_timeout, meta=meta, **kwargs
    )

    logger.info(f"Enqueued job {job.id} to queue {queue_name}", "BLUE")
    return job.id


async def get_job_status(job_id: str) -> dict:
    redis_client = get_redis_client()

    try:
        job = Job.fetch(job_id, connection=redis_client)

        if job.is_finished:
            return {
                "job_id": job_id,
                "status": "completed",
                "result": job.result,
            }
        elif job.is_failed:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(job.exc_info),
            }
        else:
            return {"job_id": job_id, "status": "running", "result": None}
    except Exception as e:
        return {"job_id": job_id, "status": "failed", "error": str(e)}
