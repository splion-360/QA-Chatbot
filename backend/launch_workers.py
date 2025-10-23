import argparse
import signal
import sys
import time
from multiprocessing import Process

from app.config import (
    REDIS_MAX_WORKERS,
    REDIS_QUEUE,
    setup_logger,
)
from app.mq.exceptions import generic_exception_handler
from app.mq.worker import ChatBotWorker


logger = setup_logger("worker")


class WorkerManager:
    def __init__(self, worker_count: int = 2):
        self.worker_count = worker_count
        self.workers: list[Process] = []
        self.running = True
        self.worker_restart_counts = {}
        self.worker_restart_delays = {}
        self.max_restart_attempts = 5
        self.base_restart_delay = 5

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("WorkerManager initialized!", "BLUE")
        logger.info(f"Worker count: {self.worker_count}", "BLUE")

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, stopping workers...", "BLUE")
        self.running = False
        self.stop_workers()
        sys.exit(0)

    def start_worker_process(self, worker_id):
        def worker_func():
            exception_handlers = [generic_exception_handler]
            worker = ChatBotWorker(REDIS_QUEUE, worker_id, exception_handlers)
            logger.info(f"Worker {worker_id} started", "BLUE")
            worker.work()

        process = Process(target=worker_func)
        process.start()
        return process

    def start_workers(self):
        for i in range(self.worker_count):
            worker_process = self.start_worker_process(i + 1)
            self.workers.append(worker_process)

        logger.info(f"All {self.worker_count} Redis workers started!", "BLUE")

    def stop_workers(self):
        logger.info(f"Stopping {self.worker_count} workers...", "BLUE")

        for worker in self.workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
                if worker.is_alive():
                    worker.kill()

        logger.info("All workers stopped", "BLUE")

    def run(self):
        try:
            self.start_workers()

            while self.running:
                for worker in self.workers[:]:
                    if not worker.is_alive():
                        worker_id = id(worker)
                        restart_count = self.worker_restart_counts.get(
                            worker_id, 0
                        )

                        if restart_count >= self.max_restart_attempts:
                            logger.error(
                                f"Worker {worker_id} retired after {restart_count} restart attempts",
                                "RED",
                            )
                            self.workers.remove(worker)
                            continue

                        delay = self.base_restart_delay * (2**restart_count)
                        self.worker_restart_delays[worker_id] = (
                            time.time() + delay
                        )
                        self.worker_restart_counts[worker_id] = (
                            restart_count + 1
                        )

                        logger.warning(
                            f"Worker {worker_id} died, restarting in {delay}s (attempt {restart_count + 1}/{self.max_restart_attempts})",
                        )
                        self.workers.remove(worker)

                for worker_id, restart_time in list(
                    self.worker_restart_delays.items()
                ):
                    if time.time() >= restart_time:
                        new_worker = self.start_worker_process(
                            len(self.workers) + 1
                        )
                        self.workers.append(new_worker)
                        del self.worker_restart_delays[worker_id]
                        logger.info(
                            f"Restarted worker as {id(new_worker)}", "GREEN"
                        )

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal", "BLUE")
        finally:
            self.stop_workers()


def main():
    parser = argparse.ArgumentParser(
        description="Launch Redis workers for QA Chatbot"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=REDIS_MAX_WORKERS,
        help="Number of workers to start",
    )
    args = parser.parse_args()

    manager = WorkerManager(worker_count=args.workers)
    manager.run()


if __name__ == "__main__":
    main()
