import asyncio
import json
import time
import uuid
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

active_connections: dict[str, set[WebSocket]] = defaultdict(set)
active_sessions: dict[str, set[str]] = defaultdict(set)
connection_last_activity: dict[WebSocket, float] = {}
heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}
active_generations: dict[str, bool] = {}

chat_service = ChatService(active_generations)


async def cleanup_connection(
    websocket: WebSocket, user_id: str, session_id: str = None
):
    active_connections[user_id].discard(websocket)
    connection_last_activity.pop(websocket, None)

    if websocket in heartbeat_tasks:
        heartbeat_tasks[websocket].cancel()
        del heartbeat_tasks[websocket]

    if session_id and session_id in active_sessions[user_id]:
        active_sessions[user_id].discard(session_id)
        await chat_service.clear_session_cache(session_id)

    if not active_connections[user_id]:
        del active_connections[user_id]
    if user_id in active_sessions and not active_sessions[user_id]:
        del active_sessions[user_id]


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

    try:
        logger.info(f"Opening Websocket for {user_id}")
        if not user_id:
            await websocket.close(code=4000, reason="Invalid user ID")
            return

        if not await check_connection_limit(user_id):
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return

        await websocket.accept()

    except Exception as e:
        logger.error(f"WebSocket accept failed for user {user_id}: {str(e)}")
        return

    active_connections[user_id].add(websocket)
    connection_last_activity[websocket] = time.time()

    heartbeat_task = asyncio.create_task(heartbeat_handler(websocket))
    heartbeat_tasks[websocket] = heartbeat_task

    current_session_id = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.debug(f"Received message: {message}", "BRIGHT_GREEN")

            connection_last_activity[websocket] = time.time()

            if message.get("type") == "pong":
                continue

            if message.get("type") == "stop_generation":
                message_id = message.get("message_id")
                if message_id and message_id in active_generations:
                    logger.info(f"Stopping generation for message {message_id}")
                    active_generations[message_id] = False
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "generation_stopped",
                                "message_id": message_id,
                            }
                        )
                    )
                continue

            user_message = message.get("message", "").strip()
            session_id = message.get("session_id")

            if session_id and session_id != current_session_id:
                if current_session_id:
                    active_sessions[user_id].discard(current_session_id)
                current_session_id = session_id
                active_sessions[user_id].add(session_id)

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
                message_id = str(uuid.uuid4())
                active_generations[message_id] = True
                logger.info(f"Starting stream for message ID: {message_id}")
                await websocket.send_text(
                    json.dumps(
                        {"type": "stream_start", "message_id": message_id}
                    )
                )

                full_message = ""
                async for chunk in chat_service.generate_streaming_response(
                    user_id, user_message, session_id, message_id
                ):
                    if not active_generations.get(message_id, False):
                        logger.info(
                            f"Generation stopped for message {message_id}"
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "generation_stopped",
                                    "message_id": message_id,
                                }
                            )
                        )
                        break

                    full_message += chunk
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "stream",
                                "content": chunk,
                                "message_id": message_id,
                            }
                        )
                    )

                if active_generations.get(message_id, False):
                    logger.info(
                        f"Complete message for {message_id}: {full_message[:100]}..."
                    )
                    await websocket.send_text(
                        json.dumps(
                            {"type": "complete", "message_id": message_id}
                        )
                    )

                active_generations.pop(message_id, None)

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
        await cleanup_connection(websocket, user_id, current_session_id)


@router.post("/")
async def chat_main():
    return {"message": "Chat service is active"}


@router.get("/ws/test")
async def websocket_test():
    return {
        "message": "WebSocket endpoint is accessible",
        "path": "/chat/ws",
    }
