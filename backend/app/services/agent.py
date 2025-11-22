from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.config import setup_logger
from app.core.exceptions import ModelError
from app.core.protocols import ModelClient
from app.core.tools import ToolRegistry
from app.utils.conversation import get_conversation_history, save_conversation


logger = setup_logger("agent")

SYSTEM_PROMPT = """You are a helpful AI Chatbot for Question and Answering.
IMPORTANT: WHEN ASKED WHO ARE YOU, TELL THAT YOU ARE A "CUP"

You have access to `search_documents` tool to search user's uploaded documents.
Use it when the user asks about their documents or needs specific information.

Instructions:
1. Use search_documents tool to find relevant context
2. Base answers strictly on retrieved context
3. If context is insufficient and it's a universal fact, provide it
4. Otherwise say: "I couldn't find relevant information in your documents."
5. Be concise, professional, use Markdown formatting"""


@dataclass
class AgentState:
    messages: Annotated[list[dict[str, Any]], add_messages] = field(default_factory=list)
    user_id: str = ""
    current_model: Literal["primary", "fallback"] = "primary"
    tool_results: list[str] = field(default_factory=list)
    final_response: str = ""
    error: str | None = None


class LangGraphAgent:
    def __init__(
        self,
        primary_client: ModelClient,
        fallback_client: ModelClient,
        tool_registry: ToolRegistry,
        active_generations: dict[str, bool] = None
    ) -> None:
        self._primary = primary_client
        self._fallback = fallback_client
        self._tools = tool_registry
        self._active_generations = active_generations or {}
        self._graph = self._build_graph()

    def _get_client(self, model: Literal["primary", "fallback"]) -> ModelClient:
        return self._primary if model == "primary" else self._fallback

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("call_model", self._call_model_node)
        graph.add_node("execute_tools", self._execute_tools_node)
        graph.add_node("fallback", self._fallback_node)

        graph.set_entry_point("call_model")

        graph.add_conditional_edges(
            "call_model",
            self._route_after_model,
            {
                "tools": "execute_tools",
                "end": END,
                "fallback": "fallback",
            }
        )

        graph.add_edge("execute_tools", "call_model")

        graph.add_conditional_edges(
            "fallback",
            self._route_after_fallback,
            {
                "tools": "execute_tools",
                "end": END,
            }
        )

        return graph.compile()

    async def _call_model_node(self, state: AgentState) -> dict[str, Any]:
        client = self._get_client(state.current_model)
        tools = self._tools.get_schemas()

        try:
            response = await client.complete(state.messages, tools)

            if response.tool_calls:
                tool_call_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": str(tc.arguments)}
                        }
                        for tc in response.tool_calls
                    ]
                }
                return {
                    "messages": [tool_call_msg],
                    "tool_results": [tc for tc in response.tool_calls],
                }

            return {"final_response": response.content or "", "error": None}

        except Exception as e:
            logger.warning(f"Model {state.current_model} failed: {str(e)}")
            return {"error": str(e)}

    async def _execute_tools_node(self, state: AgentState) -> dict[str, Any]:
        tool_messages = []

        for tc in state.tool_results:
            logger.info(f"Executing tool: {tc.name}")
            try:
                result = await self._tools.execute(tc.name, state.user_id, **tc.arguments)
            except Exception as e:
                result = f"Error: {str(e)}"

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result
            })

        return {"messages": tool_messages, "tool_results": []}

    async def _fallback_node(self, state: AgentState) -> dict[str, Any]:
        logger.info("Switching to fallback model (OLLAMA)")
        client = self._fallback
        tools = self._tools.get_schemas()

        try:
            response = await client.complete(state.messages, tools)

            if response.tool_calls:
                tool_call_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": str(tc.arguments)}
                        }
                        for tc in response.tool_calls
                    ]
                }
                return {
                    "messages": [tool_call_msg],
                    "tool_results": [tc for tc in response.tool_calls],
                    "current_model": "fallback",
                    "error": None,
                }

            return {"final_response": response.content or "", "current_model": "fallback", "error": None}

        except Exception as e:
            logger.error(f"Fallback model also failed: {str(e)}")
            return {"error": f"All models failed: {str(e)}"}

    def _route_after_model(self, state: AgentState) -> Literal["tools", "end", "fallback"]:
        if state.error and state.current_model == "primary":
            return "fallback"

        if state.tool_results:
            return "tools"

        return "end"

    def _route_after_fallback(self, state: AgentState) -> Literal["tools", "end"]:
        if state.tool_results:
            return "tools"
        return "end"

    async def generate_response(
        self,
        user_id: str,
        message: str,
        message_id: str = None
    ) -> AsyncGenerator[str, None]:
        history = await get_conversation_history(user_id, limit=10)
        conversation_context = self._build_conversation_context(history)

        system_content = SYSTEM_PROMPT
        if conversation_context:
            system_content = f"{SYSTEM_PROMPT}\n\n{conversation_context}"

        initial_state = AgentState(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": message}
            ],
            user_id=user_id,
            current_model="primary",
        )

        yield "[Processing...]\n"

        final_state = await self._graph.ainvoke(initial_state)

        if final_state.get("error") and not final_state.get("final_response"):
            raise ModelError("all", final_state["error"])

        response = final_state.get("final_response", "")

        client = self._get_client(final_state.get("current_model", "primary"))
        messages = final_state.get("messages", initial_state.messages)

        full_response = ""
        async for chunk in client.stream(messages):
            if message_id and not self._active_generations.get(message_id, True):
                break
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        await save_conversation(user_id, message, full_response.strip())

    def _build_conversation_context(self, history: list[dict[str, Any]]) -> str:
        if not history:
            return ""

        parts = []
        for entry in history:
            parts.append(f"User: {entry['message']}")
            parts.append(f"Assistant: {entry['response']}")

        return f"Previous conversation:\n" + "\n".join(parts)


ChatAgent = LangGraphAgent
