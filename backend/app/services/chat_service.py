import json
from collections.abc import AsyncGenerator

from openai import RateLimitError

from app.config import (
    FALLBACK_MODELS,
    MAX_SEARCH_LIMIT,
    MAX_STREAMING_TOKENS,
    SIMILARITY_SCORE,
    TEMPERATURE,
    get_async_openai_client,
    get_fallback_api_key,
    get_redis_client,
    get_supabase_client,
    setup_logger,
)
from app.services.document_service import (
    search_similar_documents,
    summarize_text,
)


logger = setup_logger("chat-service")


class ChatService:
    def __init__(self, active_generations: dict[str, bool] = None):
        self.openai_client = get_async_openai_client()
        self.supabase = get_supabase_client()
        self.redis_client = get_redis_client()
        self.active_generations = active_generations or {}

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
                title = data.get("title", "")
                chunk_ids.add(data.get("chunk_id", ""))
                document_ids.add(data.get("document_id", ""))
                context_parts.append(
                    f"Document '{title}' - Section {i+1}: {content}"
                )

            logger.info(
                f"Found {len(chunk_ids)} relevant chunks from {len(set(document_ids))} documents"
            )
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(
                f"Error retrieving context for user {user_id}: {str(e)}"
            )
            return

    @staticmethod
    async def get_chat_stream(client, model, messages, should_stop=None):
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            max_tokens=MAX_STREAMING_TOKENS,
            temperature=TEMPERATURE,
        )

        async for chunk in stream:
            if should_stop and should_stop():
                break
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                yield content

    async def generate_streaming_response(
        self,
        user_id: str,
        message: str,
        session_id: str = None,
        message_id: str = None,
    ) -> AsyncGenerator[str]:
        full_response = ""
        try:
            logger.info(
                f"Retrieving context for user {user_id} with query: {message}"
            )

            if session_id:
                context = await self.get_session_document_context(
                    session_id, message, user_id
                )
                history = await self.get_session_conversation_history(
                    session_id, user_id
                )
                conversation_context = (
                    await self.build_conversation_context_from_history(history)
                )
            else:
                context = await self.get_relevant_context(message, user_id)
                conversation_context = await self.get_conversation_context(
                    user_id
                )

            system_prompt = f"""
            You are a helpful AI Chatbot designed primarily for Question and Answering.
            Your task is to answer questions based on the user's uploaded documents and previous conversation context.

            Use the following context from the user's document library to answer questions.
            Context from user's documents:
            {context}

            {conversation_context}

            Instructions:
            1). Primary Source:
                - Base your answers strictly on the provided context.
                - If a clear answer exists in the context, respond concisely but thoroughly.

                When Context Is Insufficient:
                - If the answer is not present in the context, check if it is a universally true fact (e.g., "The sun rises in the east").
                - If so, provide the general truth clearly and politely.
                - Otherwise, refrain from answering, and say something like: "I'm sorry, but I couldn't find any relevant information in the provided documents."

            2). Tone and Style:
                - ALWAYS maintain a polite, respectful, and professional tone.
                - AVOID speculation, assumptions, or unverifiable claims.
                - Write in clear, grammatically correct English.
                - Keep your answers short and to the point. Be concise and direct.

            3). Formatting:
                - Use brief paragraphs and Markdown for readability (headings, lists, etc.).
                - Highlight important terms (like numbers, dates, answers) only if it improves clarity.
                - When presenting numerical values, use appropriate formatting:
                  * For large numbers, use scientific notation or abbreviations (e.g., "1.39 × 10^12" or "1.39 trillion")
                  * Limit decimal places to 2-3 significant digits maximum
                  * NEVER output extremely long decimal numbers with hundreds of digits

"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
            logger.info(
                f"Starting streaming response generation for user {user_id}"
            )

            clients_available = []
            for model, api_key_name in FALLBACK_MODELS:
                api_key = get_fallback_api_key(api_key_name)
                if api_key:
                    clients_available.append(
                        (get_async_openai_client(api_key), model)
                    )

            for client, model in clients_available:
                try:
                    logger.info(f"Trying: {model}")

                    def should_stop():
                        return (
                            not self.active_generations.get(message_id, True)
                            if message_id
                            else False
                        )

                    async for content in self.get_chat_stream(
                        client, model, messages, should_stop
                    ):
                        full_response += content
                        yield content

                    break

                except RateLimitError as e:
                    if e.status_code == 429:
                        logger.warning(
                            f"Rate limit hit, trying fallback models for user {user_id}"
                        )
                        continue

                    else:
                        raise
                except Exception as e:
                    raise e
            else:
                error = "I'm having trouble generating a response right now. All models are rate limited."
                full_response = error
                yield error

            if full_response.strip():
                await self.save_conversation(
                    user_id, message, full_response.strip()
                )

        except Exception as e:
            logger.error(
                f"Error in generating streaming response for user {user_id}: {str(e)}"
            )
            error = "I'm having trouble generating a response right now"
            await self.save_conversation(user_id, message, error)
            yield error

    async def get_conversation_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict]:
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
            logger.error(
                f"Error fetching conversation history for user {user_id}: {str(e)}"
            )
            return []

    async def save_conversation(
        self, user_id: str, message: str, response: str
    ):
        try:
            supabase = await get_supabase_client()
            await (
                supabase.table("conversation_history")
                .insert(
                    {
                        "user_id": user_id,
                        "message": message,
                        "response": response,
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.error(
                f"Error saving conversation for user {user_id}: {str(e)}"
            )

    async def get_conversation_context(self, user_id: str) -> str:
        instructions = """
        You are a summarizing agent. Your task is to produce a detailed summary of a dialogue between two speakers (typically an agent and a user) in such a way that it can serve as meaningful context for continuing or initiating further exchanges between them.
        You must create two separate summaries, one for each speaker. Each summary should be written as a coherent paragraph of NOT MORE THAN 500 WORDS, ensuring that all important keywords, questions, and answers (Q&A), significant figures like dates
        metrics, etc. are captured accurately without losing the original context, tone, or intent of the dialogue.
        Your goal is not just to compress the conversation but to preserve its flow, reasoning, and emotional undertones, highlighting the key points, arguments, and responses exchanged between the speakers.

        EXAMPLE:

        Given below is a conversation between two users discussing a research paper.

        USER: They asked several critical questions about the algorithm
        and its underlying mathematics, referencing their expertise in the field.
        They also expressed skepticism about the validity of the reported results, challenging the credibility of the conclusions presented in the paper.
        In some parts of the discussion, they appeared unconvinced by the responses, suggesting that they are analytical and not easily persuaded.

        AI: They responded politely and thoughtfully, addressing each technical question with detailed explanations and examples.
        They clarified the rationale behind the algorithm’s design, defended the experimental results with supporting evidence, and acknowledged the user’s concerns where appropriate.
        The tone remained respectful and professional throughout, showing a willingness to engage in constructive debate and maintain intellectual rigor.
        """
        try:
            history = await self.get_conversation_history(user_id, limit=20)
            if not history:
                return ""

            context_parts = []
            for entry in history:
                context_parts.append(f"User: {entry['message']}")
                context_parts.append(f"Assistant: {entry['response']}")

            conversation_text = "\n".join(context_parts)

            if len(conversation_text) > 400000:
                logger.info("Compacting..", "BLUE")
                summary = await summarize_text(conversation_text, instructions)
                return f"Previous conversation summary: {summary}"

            return f"Previous conversation:\n{conversation_text}"

        except Exception as e:
            logger.error(
                f"Error building conversation context for user {user_id}: {str(e)}"
            )
            return ""

    async def build_conversation_context_from_history(
        self, history: list[dict]
    ) -> str:
        if not history:
            return ""

        context_parts = []
        for entry in history:
            context_parts.append(f"User: {entry['message']}")
            context_parts.append(f"Assistant: {entry['response']}")

        conversation_text = "\n".join(context_parts)
        return f"Previous conversation:\n{conversation_text}"

    def get_cache_key(
        self, prefix: str, session_id: str, suffix: str = ""
    ) -> str:
        return f"{prefix}:{session_id}" + (f":{suffix}" if suffix else "")

    async def cache_data(self, key: str, data: any, ttl: int = 3600):
        try:
            self.redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.error(f"Error caching data: {str(e)}")

    async def get_cached_data(self, key: str) -> any:
        try:
            cached_data = self.redis_client.get(key)
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Error retrieving cached data: {str(e)}")
            return None

    async def get_session_conversation_history(
        self, session_id: str, user_id: str
    ) -> list[dict]:
        cache_key = self.get_cache_key("conversation", session_id)
        cached_history = await self.get_cached_data(cache_key)

        if cached_history:
            return cached_history

        history = await self.get_conversation_history(user_id)
        await self.cache_data(cache_key, history, 3600)
        return history

    async def get_session_document_context(
        self, session_id: str, query: str, user_id: str
    ) -> str:
        query_hash = str(hash(query))[:10]
        cache_key = self.get_cache_key("doc_context", session_id, query_hash)
        cached_context = await self.get_cached_data(cache_key)

        if cached_context and cached_context.get("query") == query:
            return cached_context.get("context", "")

        context = await self.get_relevant_context(query, user_id)
        if context:
            await self.cache_data(
                cache_key, {"query": query, "context": context}, 1800
            )

        return context or ""

    async def clear_session_cache(self, session_id: str):
        try:
            conv_key = self.get_cache_key("conversation", session_id)
            self.redis_client.delete(conv_key)

            pattern = f"context:{session_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Error clearing session cache: {str(e)}")