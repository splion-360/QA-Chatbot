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

_supabase_client: SU_Client | None = None
_redis_client: redis.Redis | None = None
_hf_tokenizer: AutoTokenizer | None = None
_hf_model: AutoModel | None = None

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HOSTED_LLM_BASE_URL = os.getenv("HOSTED_LLM_BASE_URL")
HOSTED_LLM_API_KEY = os.getenv("HOSTED_LLM_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_QUEUE = ["qa-chatbot"]
REDIS_MAX_WORKERS = 8
REDIS_DEFAULT_TTL = 300
REDIS_MAX_RETRY = 3
REDIS_RETRY_INTERVALS = [10, 20, 30]
REDIS_TIMEOUT = 30

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
    "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA",
    "CYAN", "WHITE", "BRIGHT_RED", "BRIGHT_GREEN", "BRIGHT_YELLOW",
]


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str) -> None:
        super().__init__(fmt)
        self.colors = {
            logging.DEBUG: "BRIGHT_YELLOW",
            logging.INFO: "GREEN",
            logging.WARNING: "YELLOW",
            logging.ERROR: "RED",
            logging.CRITICAL: "BRIGHT_RED",
        }

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = getattr(record, "custom_color", None) or self.colors.get(record.levelno, "WHITE")
        return f"{LOG_COLORS[color]}{message}{LOG_COLORS['RESET']}"


class CustomLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _log(self, level: int, message: str, color: ColorType = None) -> None:
        record = self._logger.makeRecord(
            self._logger.name, level, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def info(self, message: str, color: ColorType = None) -> None:
        self._log(logging.INFO, message, color)

    def debug(self, message: str, color: ColorType = None) -> None:
        self._log(logging.DEBUG, message, color)

    def warning(self, message: str, color: ColorType = None) -> None:
        self._log(logging.WARNING, message, color)

    def error(self, message: str, color: ColorType = None) -> None:
        self._log(logging.ERROR, message, color)

    def __getattr__(self, name: str):
        return getattr(self._logger, name)


def setup_logger(name: str = __name__) -> CustomLogger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return CustomLogger(logger)

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

    return CustomLogger(logger)


logger = setup_logger("config")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_EMBEDDING_TOKENS = 8000
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
SUMMARIZATION_MODEL = os.getenv("SUMMARIZATION_MODEL", "gemma3")
MAX_SUMMARY_TOKENS = 500
MAX_STREAMING_TOKENS = 1000000
TEMPERATURE = 0.5
SUPPORTED_FILE_TYPES = ["application/pdf"]

MAX_PAGE_SIZE = 50

MAX_SEARCH_LIMIT = 10
SIMILARITY_SCORE = 0.3

WS_MAX_CONNECTIONS_PER_USER = 3
WS_IDLE_TIMEOUT = 600
WS_HEARTBEAT_INTERVAL = 30


def get_hosted_llm_client(api_key: str | None = None, base_url: str | None = None) -> AsyncOpenAI:
    resolved_api_key = api_key or HOSTED_LLM_API_KEY or OPENAI_API_KEY
    if not resolved_api_key:
        raise ValueError("Hosted LLM API key not configured")

    resolved_base_url = base_url or HOSTED_LLM_BASE_URL or OPENAI_BASE_URL
    return AsyncOpenAI(base_url=resolved_base_url, api_key=resolved_api_key)


def get_ollama_client(api_key: str | None = None, base_url: str | None = None) -> AsyncOpenAI:
    resolved_base_url = base_url or OLLAMA_BASE_URL
    resolved_api_key = api_key or OLLAMA_API_KEY
    return AsyncOpenAI(base_url=resolved_base_url, api_key=resolved_api_key)


async def get_supabase_client() -> SU_Client:
    global _supabase_client

    if _supabase_client:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase credentials not configured")

    _supabase_client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


def get_redis_client() -> redis.Redis:
    global _redis_client

    if _redis_client:
        return _redis_client

    try:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=False,
        )
        _redis_client.ping()
        logger.info(f"Connected to Redis @ {REDIS_HOST}:{REDIS_PORT}", "BLUE")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    return _redis_client


def get_hf_tokenizer() -> AutoTokenizer:
    global _hf_tokenizer

    if _hf_tokenizer is None:
        _hf_tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    return _hf_tokenizer


def get_hf_model() -> AutoModel:
    global _hf_model

    if _hf_model is None:
        _hf_model = AutoModel.from_pretrained(EMBEDDING_MODEL)
        _hf_model.eval()
    return _hf_model
