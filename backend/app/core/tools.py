from typing import Any

from app.config import MAX_SEARCH_LIMIT, SIMILARITY_SCORE, setup_logger
from app.core.exceptions import ToolExecutionError
from app.core.protocols import Tool


logger = setup_logger("tools")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values()]

    async def execute(self, name: str, user_id: str, **kwargs: Any) -> str:
        tool = self._tools.get(name)
        if not tool:
            raise ToolExecutionError(name, "Tool not found")

        try:
            return await tool.execute(user_id, **kwargs)
        except Exception as e:
            logger.error(f"Tool {name} failed: {str(e)}")
            raise ToolExecutionError(name, str(e)) from e


class SearchDocumentsTool(Tool):
    def __init__(self, document_service: Any) -> None:
        self._document_service = document_service

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search user's uploaded documents for relevant information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for relevant document sections"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results (default: 5)"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def execute(self, user_id: str, **kwargs: Any) -> str:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", MAX_SEARCH_LIMIT)

        results = await self._document_service.search_similar_documents(
            user_id=user_id,
            query=query,
            limit=max_results,
            similarity_threshold=SIMILARITY_SCORE
        )

        if not results:
            return "No relevant documents found."

        context_parts = [
            f"Document '{r.get('title', 'Unknown')}' - Section {i+1}: {r.get('content', '')}"
            for i, r in enumerate(results)
        ]
        logger.info(f"Found {len(results)} document sections")
        return "\n\n".join(context_parts)
