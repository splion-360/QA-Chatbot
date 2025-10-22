import argparse
import asyncio
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from temporalio import workflow
from temporalio.worker import Worker

from app.config import (
    TEMPORAL_MAX_WORKERS,
    TEMPORAL_RETRY_POLICY,
    TEMPORAL_TASK_QUEUE,
    get_temporal_client,
    setup_logger,
)
from app.mq.activities import process_document_activity


logger = setup_logger()


@workflow.defn
class DocumentProcessingWorkflow:
    @workflow.run
    async def run(
        self, file_data: bytes, filename: str, user_id: str, title: str = None
    ) -> str:
        return await workflow.execute_activity(
            process_document_activity,
            args=[file_data, filename, user_id, title],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=TEMPORAL_RETRY_POLICY,
        )


class TemporalWorkerManager:
    def __init__(self, worker_count: int = 2):
        self.worker_count = worker_count
        self.workers = []
        self.running = True

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("TemporalWorkerManager initialized:", "GREEN")
        logger.info(f"Worker count: {self.worker_count}", "GREEN")
        logger.info(f"Task queue: {TEMPORAL_TASK_QUEUE}", "GREEN")

    def _signal_handler(self, signum, frame):
        logger.info(
            f"Received signal {signum}, initiating graceful shutdown...",
            "GREEN",
        )
        self.running = False

    async def start_workers(self):
        client = await get_temporal_client()

        for i in range(self.worker_count):
            worker = Worker(
                client,
                task_queue=TEMPORAL_TASK_QUEUE,
                workflows=[DocumentProcessingWorkflow],
                activities=[process_document_activity],
                activity_executor=ThreadPoolExecutor(max_workers=4),
            )
            self.workers.append(worker)
            logger.info(f"Started Temporal worker {i + 1}", "GREEN")

        logger.info(
            f"All {self.worker_count} Temporal workers started successfully!",
            "GREEN",
        )

    async def run(self):
        try:
            await self.start_workers()
            await asyncio.gather(*[worker.run() for worker in self.workers])
        except Exception as e:
            logger.error(f"Temporal worker manager failed: {e}")
            sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Launch Temporal workers for QA Chatbot"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=TEMPORAL_MAX_WORKERS,
        help="Number of workers to start",
    )
    args = parser.parse_args()

    manager = TemporalWorkerManager(worker_count=args.workers)

    try:
        await manager.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal", "GREEN")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start Temporal workers: {e}", "GREEN")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
