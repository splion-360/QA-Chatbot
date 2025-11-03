import asyncio
import json
import time
from collections import defaultdict

from fastapi import (
    APIRouter,
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
from app.services.chat_service import ChatService


logger = setup_logger("ws-chat")
router = APIRouter()
chat_service = ChatService()

active_connections: dict[str, set[WebSocket]] = defaultdict(set)
connection_last_activity: dict[WebSocket, float] = {}
heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}


async def cleanup_connection(websocket: WebSocket, user_id: str):
    active_connections[user_id].discard(websocket)
    connection_last_activity.pop(websocket, None)

    if websocket in heartbeat_tasks:
        heartbeat_tasks[websocket].cancel()
        del heartbeat_tasks[websocket]

    if not active_connections[user_id]:
        del active_connections[user_id]


async def check_connection_limit(user_id: str) -> bool:
    return len(active_connections[user_id]) < WS_MAX_CONNECTIONS_PER_USER


async def is_connection_idle(websocket: WebSocket) -> bool:
    last_activity = connection_last_activity.get(websocket, time.time())
    return time.time() - last_activity > WS_IDLE_TIMEOUT


async def heartbeat_handler(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

            if await is_connection_idle(websocket):
                await websocket.send_text(json.dumps({"type": "idle_timeout"}))
                await websocket.close(code=1000)
                break

            await websocket.send_text(json.dumps({"type": "ping"}))

    except Exception:
        pass


@router.websocket("/ws")
async def chat(websocket: WebSocket, user_id: str = Query(...)):
    client_info = f"{websocket.client.host}:{websocket.client.port}"
    headers = dict(websocket.headers)

    logger.info("=== WebSocket Connection Attempt ===")
    logger.info(f"Client: {client_info}")
    logger.info(f"User ID: '{user_id}' (type: {type(user_id)})")
    logger.info(f"Headers: {headers}")
    logger.info(
        f"Current connections for user: {len(active_connections.get(user_id, set()))}"
    )

    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.error(f"REJECTING: Invalid user_id received: '{user_id}'")
            await websocket.close(code=4000, reason="Invalid user ID")
            return

        if not await check_connection_limit(user_id):
            logger.warning(
                f"REJECTING: Connection limit exceeded for user {user_id} ({len(active_connections[user_id])}/{WS_MAX_CONNECTIONS_PER_USER})"
            )
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return

        logger.info(f"ACCEPTING: WebSocket connection for user {user_id}")
        await websocket.accept()
        logger.info(
            f"SUCCESS: WebSocket connection established for user {user_id}"
        )
    except Exception as e:
        logger.error(
            f"FAILED: WebSocket accept failed for user {user_id}: {str(e)}"
        )
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {repr(e)}")
        return

    active_connections[user_id].add(websocket)
    connection_last_activity[websocket] = time.time()

    heartbeat_task = asyncio.create_task(heartbeat_handler(websocket))
    heartbeat_tasks[websocket] = heartbeat_task

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"Received message from {user_id}: {message}")

            connection_last_activity[websocket] = time.time()

            if message.get("type") == "pong":
                continue

            user_message = message.get("message", "").strip()
            if not user_message:
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": "Empty message received"}
                    )
                )
                continue

            await websocket.send_text(
                json.dumps(
                    {"type": "message_received", "user_message": user_message}
                )
            )

            try:
                async for chunk in chat_service.generate_streaming_response(
                    user_id, user_message
                ):
                    await websocket.send_text(
                        json.dumps({"type": "stream", "content": chunk})
                    )

                await websocket.send_text(json.dumps({"type": "complete"}))

            except Exception as e:
                logger.error(
                    f"Error generating response for user {user_id}: {str(e)}"
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Failed to generate response: {str(e)}",
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        await cleanup_connection(websocket, user_id)


@router.post("/")
async def chat_main():
    return {"message": "Chat service is active"}


@router.get("/ws/test")
async def websocket_test():
    return {
        "message": "WebSocket endpoint is accessible",
        "path": "/chat/ws",
    }
