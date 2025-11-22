from typing import Any

from app.config import get_supabase_client, setup_logger


logger = setup_logger("conversation")


async def save_conversation(user_id: str, message: str, response: str) -> None:
    try:
        supabase = await get_supabase_client()
        await supabase.table("conversation_history").insert({
            "user_id": user_id,
            "message": message,
            "response": response,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save conversation: {str(e)}")


async def get_conversation_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        supabase = await get_supabase_client()
        result = await (
            supabase.table("conversation_history")
            .select("message, response, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(result.data))
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        return []
