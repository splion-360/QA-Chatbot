import asyncio
import json
import os
import time
import uuid
from collections import defaultdict

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from app.config import (
    WS_HEARTBEAT_INTERVAL,
    WS_IDLE_TIMEOUT,
    WS_MAX_CONNECTIONS_PER_USER,
    setup_logger,
)
from app.core.tools import SearchDocumentsTool, ToolRegistry
from app.services.agent import ChatAgent
from app.services.document_service import document_service
from app.services.model_client import OllamaClient, OpenRouterClient
from app.utils.auth import ensure_user_access


logger = setup_logger("ws-chat")
router = APIRouter()

active_connections: dict[str, set[WebSocket]] = defaultdict(set)
active_sessions: dict[str, set[str]] = defaultdict(set)
connection_last_activity: dict[WebSocket, float] = {}
heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}
active_generations: dict[str, bool] = {}


def create_agent() -> ChatAgent:
    tool_registry = ToolRegistry()
    tool_registry.register(SearchDocumentsTool(document_service))

    primary = OpenRouterClient(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        model=os.getenv("PRIMARY_MODEL", "meta-llama/llama-4-maverick:free"),
    )
    fallback = OllamaClient(model=os.getenv("OLLAMA_MODEL", "gemma3"))

    return ChatAgent(
        primary_client=primary,
        fallback_client=fallback,
        tool_registry=tool_registry,
        active_generations=active_generations,
    )


agent = create_agent()


async def cleanup_connection(
    websocket: WebSocket, user_id: str, session_id: str = None
) -> None:
    active_connections[user_id].discard(websocket)
    connection_last_activity.pop(websocket, None)

    if websocket in heartbeat_tasks:
        heartbeat_tasks[websocket].cancel()
        del heartbeat_tasks[websocket]

    if session_id:
        active_sessions[user_id].discard(session_id)

    if not active_connections[user_id]:
        del active_connections[user_id]

    if user_id in active_sessions and not active_sessions[user_id]:
        del active_sessions[user_id]


def check_connection_limit(user_id: str) -> bool:
    return len(active_connections[user_id]) < WS_MAX_CONNECTIONS_PER_USER


def is_connection_idle(websocket: WebSocket) -> bool:
    last_activity = connection_last_activity.get(websocket, time.time())
    return time.time() - last_activity > WS_IDLE_TIMEOUT


async def heartbeat_handler(websocket: WebSocket) -> None:
    try:
        while True:
            await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

            if is_connection_idle(websocket):
                await websocket.send_text(json.dumps({"type": "idle_timeout"}))
                await websocket.close(code=1000)
                return

            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass


async def send_json(websocket: WebSocket, data: dict) -> None:
    await websocket.send_text(json.dumps(data))


async def stop_generation(websocket: WebSocket, stop_message: dict) -> None:
    message_id = stop_message.get("message_id")

    if not message_id:
        await send_json(
            websocket,
            {
                "type": "error",
                "message": "Missing message_id for stop request",
            },
        )
        return

    if message_id not in active_generations:
        await send_json(
            websocket,
            {
                "type": "error",
                "message": "Streaming session not found",
                "message_id": message_id,
            },
        )
        return

    active_generations[message_id] = False
    await send_json(
        websocket,
        {
            "type": "stop_ack",
            "message": "Stopping generation",
            "message_id": message_id,
        },
    )


async def handle_message(
    websocket: WebSocket,
    user_id: str,
    user_message: str,
    session_id: str | None,
) -> None:
    message_id = str(uuid.uuid4())
    active_generations[message_id] = True

    logger.info(f"Starting stream for message ID: {message_id}")
    await send_json(
        websocket, {"type": "stream_start", "message_id": message_id}
    )

    try:
        async for chunk in agent.generate_response(
            user_id, user_message, message_id
        ):
            if not active_generations.get(message_id, False):
                logger.info(f"Generation stopped for message {message_id}")
                await send_json(
                    websocket,
                    {"type": "generation_stopped", "message_id": message_id},
                )
                return

            await send_json(
                websocket,
                {"type": "stream", "content": chunk, "message_id": message_id},
            )

        if active_generations.get(message_id, False):
            await send_json(
                websocket, {"type": "complete", "message_id": message_id}
            )
    finally:
        active_generations.pop(message_id, None)


@router.websocket("/ws")
async def chat(websocket: WebSocket, user_id: str = Query(...)) -> None:
    logger.info(f"Active Connections: {active_connections}")

    if not user_id:
        await websocket.close(code=4000, reason="Invalid user ID")
        return

    header_user = websocket.headers.get("x-user-id")
    if not header_user:
        # Allow query param fallback for browser clients that cannot set custom WS headers
        header_user = websocket.query_params.get("x_user_id")

    try:
        ensure_user_access(user_id, header_user)
    except HTTPException as exc:
        await websocket.close(code=4401, reason=exc.detail)
        return

    if not check_connection_limit(user_id):
        await websocket.close(code=1008, reason="Connection limit exceeded")
        return

    try:
        logger.info(f"Opening Websocket for {user_id}")
        await websocket.accept()
    except Exception as e:
        logger.error(f"WebSocket accept failed for user {user_id}: {str(e)}")
        return

    active_connections[user_id].add(websocket)
    connection_last_activity[websocket] = time.time()
    heartbeat_tasks[websocket] = asyncio.create_task(
        heartbeat_handler(websocket)
    )

    current_session_id = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            connection_last_activity[websocket] = time.time()

            if message.get("type") == "pong":
                continue

            if message.get("type") == "stop":
                await stop_generation(websocket, message)
                continue

            user_message = message.get("message", "").strip()
            session_id = message.get("session_id")

            if session_id and session_id != current_session_id:
                if current_session_id:
                    active_sessions[user_id].discard(current_session_id)
                current_session_id = session_id
                active_sessions[user_id].add(session_id)

            if not user_message:
                await send_json(
                    websocket,
                    {"type": "error", "message": "Empty message received"},
                )
                continue

            await send_json(
                websocket,
                {"type": "message_received", "user_message": user_message},
            )

            try:
                await handle_message(
                    websocket, user_id, user_message, current_session_id
                )
            except Exception as e:
                logger.error(
                    f"Error generating response for user {user_id}: {str(e)}"
                )
                await send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": f"Failed to generate response: {str(e)}",
                    },
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        await cleanup_connection(websocket, user_id, current_session_id)


@router.post("/")
async def chat_main():
    return {"message": "Chat service is active"}


@router.get("/ws/test")
async def websocket_test():
    return {"message": "WebSocket endpoint is accessible", "path": "/chat/ws"}
