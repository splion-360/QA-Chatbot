import asyncio
from io import BytesIO
from typing import Any

import torch
import torch.nn.functional as F
from fastapi import HTTPException, UploadFile
from postgrest.exceptions import APIError
from pypdf import PdfReader

from app.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MAX_FILE_SIZE_BYTES,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LIMIT,
    MAX_SUMMARY_TOKENS,
    SIMILARITY_SCORE,
    SUMMARIZATION_MODEL,
    SUPPORTED_FILE_TYPES,
    get_async_openai_client,
    get_hf_model,
    get_hf_tokenizer,
    get_redis_client,
    get_supabase_client,
    setup_logger,
)
from app.mq.exceptions import (
    DatabaseError,
    DocumentProcessingError,
    VectorizationError,
)
from app.mq.queue import enqueue_task


logger = setup_logger("document-service")


def extract_text(pdf_file: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_file))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise DocumentProcessingError(
            "unknown", "unknown", f"PDF extraction failed: {str(e)}"
        ) from e


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


async def get_embedding(text: str) -> list[float]:
    try:
        tokenizer = get_hf_tokenizer()
        model = get_hf_model()

        def mean_pooling(model_output, attention_mask):
            token_embeddings = model_output[0]
            input_mask_expanded = (
                attention_mask.unsqueeze(-1)
                .expand(token_embeddings.size())
                .float()
            )
            return torch.sum(
                token_embeddings * input_mask_expanded, 1
            ) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

        encoded_input = tokenizer(
            [text], padding=True, truncation=True, return_tensors="pt"
        )
        with torch.no_grad():
            model_output = model(**encoded_input)

        sentence_embeddings = mean_pooling(
            model_output, encoded_input["attention_mask"]
        )

        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings[0].tolist()
    except Exception as e:
        raise VectorizationError(
            "unknown", f"Embedding generation failed: {str(e)}"
        ) from e


async def process_chunk(chunk_text: str, document_id: str, chunk_index: int):
    try:
        summary = await summarize_text(chunk_text)
        embedding = await get_embedding(summary)

        supabase = await get_supabase_client()
        await supabase.table("vector_store").insert(
            {
                "document_id": document_id,
                "content": chunk_text,
                "embedding": embedding,
            }
        ).execute()

        redis_client = get_redis_client()
        redis_client.incr(f"chunk_count:{document_id}")
        redis_client.expire(f"chunk_count:{document_id}", 3600)

        logger.info(f"Processed chunk {chunk_index} for document {document_id}")
        return embedding
    except APIError as e:
        raise DatabaseError("insertion", "vector_store", e.message) from e
    except Exception as e:
        raise VectorizationError(document_id, str(e)) from e


async def check_document_completion(document_id: str, total_chunks: int):
    try:
        redis_client = get_redis_client()

        while True:
            processed_count = redis_client.get(f"chunk_count:{document_id}")
            if processed_count and int(processed_count) >= total_chunks:
                break
            await asyncio.sleep(0.5)

        redis_client.delete(f"chunk_count:{document_id}")
        logger.info(
            f"Document {document_id} processing completed - all {total_chunks} chunks processed"
        )
        return document_id
    except Exception as e:
        raise DocumentProcessingError(document_id, "unknown", str(e)) from e


async def summarize_text(text: str, instructions: str = None) -> str:
    client = get_async_openai_client()
    if not instructions:
        instructions = f"Summarize the following content in less than {MAX_SUMMARY_TOKENS} words"
    response = await client.chat.completions.create(
        model=SUMMARIZATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": instructions,
            },
            {"role": "user", "content": text},
        ],
        max_tokens=MAX_SUMMARY_TOKENS,
    )
    return response.choices[0].message.content


async def save_document(
    user_id: str,
    title: str,
    original_content: str,
    chunks: list[str],
    embeddings: list[list[float]],
    file_size: int,
) -> str:
    supabase = await get_supabase_client()
    try:
        response = await (
            supabase.table("documents")
            .insert(
                {
                    "user_id": user_id,
                    "title": title,
                    "size": file_size,
                    "content": original_content,
                }
            )
            .execute()
        )

        document_id = response.data[0]["document_id"]

    except APIError as e:
        raise DatabaseError("insertion", "documents", e.message) from e

    try:
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            await supabase.table("vector_store").insert(
                {
                    "document_id": document_id,
                    "content": chunk,
                    "embedding": embedding,
                }
            ).execute()

    except APIError as e:
        raise DatabaseError("insertion", "vector_store", e.message) from e

    return document_id


async def save_summary(user_id: str, content: str) -> str:
    try:
        supabase = await get_supabase_client()
        result = await (
            supabase.table("summary")
            .insert({"user_id": user_id, "content": content})
            .execute()
        )
        return result.data[0]["summary_id"]
    except APIError as e:
        raise DatabaseError("insertion", "summary", e.message) from e


async def get_documents(
    user_id: str, offset: int = 0, limit: int = MAX_PAGE_SIZE
) -> dict[str, Any]:
    try:
        supabase = await get_supabase_client()

        result = await (
            supabase.table("documents")
            .select("document_id, title, size, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        count_result = await (
            supabase.table("documents")
            .select("document_id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "documents": result.data,
            "total": count_result.count,
            "offset": offset,
            "limit": limit,
        }
    except APIError as e:
        raise DatabaseError("select", "documents", e.message) from e


async def get_document(document_id: str, user_id: str) -> dict[str, Any] | None:
    try:
        supabase = await get_supabase_client()

        doc_result = await (
            supabase.table("documents")
            .select("*")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not doc_result.data:
            return None

        document = doc_result.data[0]

        count_result = await (
            supabase.table("vector_store")
            .select("chunk_id", count="exact")
            .eq("document_id", document_id)
            .execute()
        )

        preview_content = document["content"][:1000]
        if len(document["content"]) > 1000:
            preview_content += "..."

        return {
            "document_id": document_id,
            "title": document["title"],
            "content": preview_content,
            "preview": preview_content,
            "total_length": len(document["content"]),
            "chunks": count_result.count,
            "created_at": document["created_at"],
        }
    except APIError as e:
        raise DatabaseError("select", "documents", e.message) from e


async def delete_document(document_id: str, user_id: str) -> bool:
    try:
        supabase = await get_supabase_client()

        result = await (
            supabase.table("documents")
            .delete()
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(result.data) > 0
    except APIError as e:
        raise DatabaseError("delete", "documents", e.message) from e


async def search_similar_documents(
    user_id: str,
    query: str,
    limit: int = MAX_SEARCH_LIMIT,
    similarity_threshold: float = SIMILARITY_SCORE,
) -> list[dict[str, Any]]:
    """
    Query based document retrieval from the database
    TODO: OpenAI tool construction
    """
    try:
        supabase = await get_supabase_client()
        query_embedding = await get_embedding(query)

        result = await supabase.rpc(
            "search_similar_documents",
            {
                "query_embedding": query_embedding,
                "user_id": user_id,
                "match_count": limit,
                "similarity_threshold": similarity_threshold,
            },
        ).execute()

        return result.data
    except APIError as e:
        raise DatabaseError("rpc", "search_similar_documents", e.message) from e


def is_valid(file: UploadFile) -> bool | None:
    if file.content_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only {', '.join(SUPPORTED_FILE_TYPES)} are supported.",
        )

    if file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
        )

    return True


async def process_file(data: dict, user_id: str, title: str = None) -> str:
    filename = data["filename"]
    file_size = data["size"]
    content = data["content"]
    content_type = data["content_type"]

    if not content_type == "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
        )

    try:
        text = extract_text(content)
        chunks = chunk_text(text)
        doc_title = title if title else filename.replace(".pdf", "")

        supabase = await get_supabase_client()
        response = await (
            supabase.table("documents")
            .insert(
                {
                    "user_id": user_id,
                    "title": doc_title,
                    "size": file_size,
                    "content": text,
                }
            )
            .execute()
        )

        document_id = response.data[0]["document_id"]

        logger.info(f"Found {len(chunks)} chunks for {filename}", "WHITE")

        for i, chunk in enumerate(chunks):
            await enqueue_task(
                process_chunk,
                args=[chunk, document_id, i],
                queue_name="qa-chatbot",
            )

        await enqueue_task(
            check_document_completion,
            args=[document_id, len(chunks)],
            queue_name="qa-chatbot",
        )

    except DatabaseError:
        raise

    except Exception as e:
        raise DocumentProcessingError(document_id, user_id, str(e)) from e

    logger.info(f"Submitted document {document_id} for parallel processing")
    return document_id


async def search_documents(
    user_id: str,
    search_query: str,
    offset: int = 0,
    limit: int = MAX_PAGE_SIZE,
) -> dict[str, Any]:
    """
    Simple key-word based search service for retrieving user documents
    NOTE: This utility is only for improving UX and SHOULD NOT BE used as a tool for RAG

    """
    try:
        supabase = await get_supabase_client()

        result = await (
            supabase.table("documents")
            .select("document_id, title, size, created_at")
            .eq("user_id", user_id)
            .ilike("title", f"%{search_query}%")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        count_result = await (
            supabase.table("documents")
            .select("document_id", count="exact")
            .eq("user_id", user_id)
            .ilike("title", f"%{search_query}%")
            .execute()
        )

        documents = result.data if result.data else []
        total = count_result.count if hasattr(count_result, "count") else 0

        return {
            "documents": documents,
            "total": total,
        }

    except Exception as e:
        logger.error(
            f"Search error for user {user_id}, query '{search_query}': {str(e)}"
        )
        raise DatabaseError(f"Search failed: {str(e)}") from e