import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from app.config import MAX_STREAMING_TOKENS, TEMPERATURE, setup_logger
from app.core.protocols import ModelClient, ModelResponse, StreamChunk, ToolCall


logger = setup_logger("model-client")


class OpenAICompatibleClient(ModelClient):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": MAX_STREAMING_TOKENS,
            "temperature": TEMPERATURE,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in choice.message.tool_calls
            ]

        return ModelResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )

    async def stream(
        self, messages: list[dict[str, Any]]
    ) -> AsyncGenerator[StreamChunk]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            max_tokens=MAX_STREAMING_TOKENS,
            temperature=TEMPERATURE,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            is_done = chunk.choices[0].finish_reason is not None
            yield StreamChunk(content=content, is_done=is_done)


class OpenRouterClient(OpenAICompatibleClient):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model=model,
        )


class OllamaClient(OpenAICompatibleClient):
    def __init__(
        self, model: str, host: str = "http://localhost:11434"
    ) -> None:
        super().__init__(base_url=f"{host}/v1", api_key="ollama", model=model)
