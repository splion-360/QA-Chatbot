import logging

from rq import Worker

from app.config import (
    REDIS_DEFAULT_TTL,
    get_redis_client,
    setup_logger,
)


logger = setup_logger("worker")


class ChatBotWorker(Worker):
    def __init__(
        self,
        queues: list[any],
        suffix: str,
        exception_handlers: list[callable] = None,
    ):

        self.conn = get_redis_client()
        self.name = f"chatbot:worker:{suffix}"
        self.queues = queues

        super().__init__(
            queues,
            self.name,
            REDIS_DEFAULT_TTL,
            self.conn,
            exception_handlers=exception_handlers,
            log_job_description=False,
        )

        rq_logger = logging.getLogger("rq.worker")
        rq_logger.setLevel(logging.WARNING)
