from collections.abc import AsyncGenerator

from app.config import (
    CHAT_MODEL,
    MAX_SEARCH_LIMIT,
    MAX_STREAMING_TOKENS,
    SIMILARITY_SCORE,
    TEMPERATURE,
    get_async_openai_client,
    get_supabase_client,
    setup_logger,
)
from app.core.config import settings
from app.services.document_service import search_similar_documents


logger = setup_logger("chat-service")


class ChatService:
    def __init__(self):
        self.openai_client = get_async_openai_client()
        self.supabase = get_supabase_client()

    async def get_relevant_context(
        self,
        query: str,
        user_id: str,
        max_results: int = MAX_SEARCH_LIMIT,
        similarity: float = SIMILARITY_SCORE,
    ) -> str | None:
        try:
            result = await search_similar_documents(
                user_id, query, max_results, similarity
            )

            if not result:
                logger.info("No relevant documents found")
                return

            context_parts = []
            chunk_ids, document_ids = set(), set()

            for i, data in enumerate(result):
                content = data.get("content", "")
                chunk_ids.add(data.get("chunk_id", ""))
                document_ids.add(data.get("document_id", ""))
                context_parts.append(f"Doc {i+1}: {content}")

            logger.info(
                f"Found {len(chunk_ids)} relevant chunks from {len(set(document_ids))} documents"
            )
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(
                f"Error retrieving context for user {user_id}: {str(e)}"
            )
            return

    async def generate_streaming_response(
        self, user_id: str, message: str
    ) -> AsyncGenerator[str]:

        try:
            logger.info(
                f"Retrieving context for user {user_id} with query: {message}"
            )
            context = await self.get_relevant_context(message, user_id)

            system_prompt = f"""
            You are a helpful AI Chatbot designed primarily for Question and Answering.
            Your task is to answer questions based on the user's uploaded documents.

            Use the following context from the user's document library to answer questions.
            Context from user's documents:
            {context}

            Instructions:
            1). Primary Source:
                - Base your answers strictly on the provided context.
                - If a clear answer exists in the context, respond concisely but thoroughly.

                When Context Is Insufficient:
                - If the answer is not present in the context, check if it is a universally true fact (e.g., “The sun rises in the east”).
                - If so, provide the general truth clearly and politely.
                - Otherwise, refrain from answering, and say something like: “I’m sorry, but I couldn’t find any relevant information in the provided documents.”

            2). Tone and Style:
                - ALWAYS maintain a polite, respectful, and professional tone.
                - AVOID speculation, assumptions, or unverifiable claims.
                - Write in clear, grammatically correct English.

            3). Formatting:
                - Use brief paragraphs and Markdown for readability (headings, lists, etc.).
                - Highlight important terms (like numbers, dates, answers) only if it improves clarity.

"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]

            logger.info(
                f"Starting streaming response generation for user {user_id}"
            )

            try:
                headers = {"X-Title": settings.name}
                stream = await self.openai_client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=MAX_STREAMING_TOKENS,
                    temperature=TEMPERATURE,
                    extra_headers=headers,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content

            except Exception as e:
                logger.error(f"Streaming error for user {user_id}: {str(e)}")
                yield f"I apologize, but I'm having trouble generating a response right now. Error: {str(e)}"

        except Exception as e:
            logger.error(
                f"Error in generating streaming response for user {user_id}: {str(e)}"
            )
            yield f"I apologize, but I encountered an error while processing request: {str(e)}"

    # async def get_conversation_history(
    #     self, user_id: str, limit: int = 10
    # ) -> list[dict]:
    #     try:
    #         return []
    #     except Exception as e:
    #         logger.error(
    #             f"Error fetching conversation history for user {user_id}: {str(e)}"
    #         )
    #         return []
