from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
    finish_reason: str


@dataclass
class StreamChunk:
    content: str | None
    is_done: bool


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any]:
        pass

    @abstractmethod
    async def execute(self, user_id: str, **kwargs: Any) -> str:
        pass


class ModelClient(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]]
    ) -> AsyncGenerator[StreamChunk, None]:
        pass


class ConversationRepository(ABC):
    @abstractmethod
    async def save(self, user_id: str, message: str, response: str) -> None:
        pass

    @abstractmethod
    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        pass
