import logging
import os
from typing import Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import Client as SU_Client
from supabase import acreate_client
from transformers import AutoModel, AutoTokenizer

import redis


load_dotenv()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

if ENVIRONMENT == "development":
    SUPABASE_URL = os.getenv("SUPABASE_URL_DEV")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY_DEV")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY_DEV")


else:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY")


_async_openai_client: AsyncOpenAI | None = None
_supabase_client: SU_Client | None = None
_redis_client: redis.Redis | None = None
_hf_tokenizer: AutoTokenizer | None = None
_hf_model: AutoModel | None = None

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_QUEUE = ["qa-chatbot"]
REDIS_MAX_WORKERS = 8
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
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
SUMMARIZATION_MODEL = "gpt-3.5-turbo"
CHAT_MODEL = "meta-llama/llama-4-maverick:free"
MAX_SUMMARY_TOKENS = 500
MAX_STREAMING_TOKENS = 1000
TEMPERATURE = 0.1
SUPPORTED_FILE_TYPES = ["application/pdf"]

# Pagination Configuration
MAX_PAGE_SIZE = 50

# Vector Search Configuration
MAX_SEARCH_LIMIT = 5
SIMILARITY_SCORE = 0.7

# WebSocket Configuration
WS_MAX_CONNECTIONS_PER_USER = 1
WS_IDLE_TIMEOUT = 600
WS_HEARTBEAT_INTERVAL = 30


def get_async_openai_client() -> AsyncOpenAI:
    global _async_openai_client

    if not _async_openai_client:
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenAI API key not configured")
        _async_openai_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return _async_openai_client


async def get_supabase_client() -> SU_Client:
    global _supabase_client
    if not _supabase_client:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase_client = await acreate_client(
            SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        )
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


def get_hf_tokenizer() -> AutoTokenizer:
    global _hf_tokenizer
    if not _hf_tokenizer:
        _hf_tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    return _hf_tokenizer


def get_hf_model() -> AutoModel:
    global _hf_model
    if not _hf_model:
        _hf_model = AutoModel.from_pretrained(EMBEDDING_MODEL)
    return _hf_model
