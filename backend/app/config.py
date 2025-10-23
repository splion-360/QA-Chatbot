import logging
import os
from typing import Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import Client as SU_Client
from supabase import create_client

import redis


load_dotenv()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

if ENVIRONMENT == "development":
    SUPABASE_URL = os.getenv("SUPABASE_URL_DEV")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY_DEV")

else:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


_async_openai_client: AsyncOpenAI | None = None
_supabase_client: SU_Client | None = None
_redis_client: redis.Redis | None = None

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_QUEUE = ["qa-chatbot"]
REDIS_MAX_WORKERS = 2
REDIS_DEFAULT_TTL = 300
REDIS_MAX_RETRY = 3
REDIS_RETRY_INTERVALS = [10, 20, 30]
REDIS_TIMEOUT = 30  # s

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
        if hasattr(record, "custom_color") and record.custom_color:
            color = record.custom_color
        else:
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


logger = setup_logger("config")

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


def get_async_openai_client() -> AsyncOpenAI:
    global _async_openai_client
    if not _async_openai_client:
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenAI API key not configured")
        _async_openai_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY
        )
    return _async_openai_client


def get_supabase_client() -> SU_Client:
    global _supabase_client
    if not _supabase_client:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client


def get_redis_client() -> redis.Redis:
    global _redis_client
    if not _redis_client:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=False,
            )
            _redis_client.ping()
            logger.info(
                f"Connected to Redis @ {REDIS_HOST}:{REDIS_PORT}",
                "BLUE",
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", "BLUE")
            raise
    return _redis_client


def close_redis_client():
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
