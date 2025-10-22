import logging
import os
from typing import Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from supabase import Client as SU_Client
from supabase import create_client
from temporalio.client import Client as TE_Client


load_dotenv()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

if ENVIRONMENT == "development":
    SUPABASE_URL = os.getenv("SUPABASE_URL_DEV")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY_DEV")

else:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


_openai_client: OpenAI | None = None
_async_openai_client: AsyncOpenAI | None = None
_supabase_client: SU_Client | None = None
_temporal_client: TE_Client | None = None

TEMPORAL_TASK_QUEUE = "qa-chatbot"
TEMPORAL_NAMESPACE = "workers"
TEMPORAL_PORT = 7233
TEMPORAL_MAX_WORKERS = 2
TEMPORAL_RETRY_POLICY = {
    "maximum_attempts": 3,
    "initial_interval_seconds": 10,
    "maximum_interval_seconds": 60,
    "backoff_coefficient": 2.0,
}

LOG_COLORS = {
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BRIGHT_RED": "\033[91m",
    "BRIGHT_GREEN": "\033[92m",
    "BRIGHT_YELLOW": "\033[93m",
    "RESET": "\033[0m",
}

ColorType = Literal[
    "RED",
    "GREEN",
    "YELLOW",
    "BLUE",
    "MAGENTA",
    "CYAN",
    "WHITE",
    "BRIGHT_RED",
    "BRIGHT_GREEN",
    "BRIGHT_YELLOW",
]


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str):
        super().__init__(fmt)
        self.colors = {
            logging.DEBUG: "BRIGHT_YELLOW",
            logging.INFO: "GREEN",
            logging.WARNING: "YELLOW",
            logging.ERROR: "RED",
            logging.CRITICAL: "BRIGHT_RED",
        }

    def format(self, record):
        message = super().format(record)
        color = self.colors.get(record.levelno, "WHITE")
        return f"{LOG_COLORS[color]}{message}{LOG_COLORS['RESET']}"


class CustomLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def debug(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(
            self._logger.name, logging.DEBUG, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def warning(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(
            self._logger.name, logging.WARNING, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def error(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(
            self._logger.name, logging.ERROR, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def __getattr__(self, name):
        return getattr(self._logger, name)


def setup_logger(name: str = __name__) -> CustomLogger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return CustomLogger(logger)

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return CustomLogger(logger)


logger = setup_logger()

# Document Processing Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_EMBEDDING_TOKENS = 8000
EMBEDDING_MODEL = "text-embedding-ada-002"
SUMMARIZATION_MODEL = "gpt-3.5-turbo"
MAX_SUMMARY_TOKENS = 500
SUPPORTED_FILE_TYPES = ["application/pdf"]

# Pagination Configuration
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

# Vector Search Configuration
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50


def get_openai_client() -> OpenAI:
    global _openai_client
    if not _openai_client:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def get_async_openai_client() -> AsyncOpenAI:
    global _async_openai_client
    if not _async_openai_client:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        _async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _async_openai_client


def get_supabase_client() -> SU_Client:
    global _supabase_client
    if not _supabase_client:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client


async def get_temporal_client() -> TE_Client:
    global _temporal_client
    if not _temporal_client:
        try:
            _temporal_client = await TE_Client.connect(
                f"localhost:{TEMPORAL_PORT}",
                namespace=TEMPORAL_NAMESPACE,
            )
            logger.info(
                f"Connected to Temporal @ http://localhost:{TEMPORAL_PORT}",
                "GREEN",
            )
        except Exception as e:
            logger.error(f"Failed to connect to Temporal: {e}", "GREEN")
            raise
    return _temporal_client


async def close_temporal_client():
    global _temporal_client
    if _temporal_client:
        await _temporal_client.close()
        _temporal_client = None
