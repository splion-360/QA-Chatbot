import uuid
from io import BytesIO
from typing import Any

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SEARCH_LIMIT,
    EMBEDDING_MODEL,
    MAX_FILE_SIZE_BYTES,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LIMIT,
    MAX_SUMMARY_TOKENS,
    SUMMARIZATION_MODEL,
    SUPPORTED_FILE_TYPES,
    get_async_openai_client,
    get_supabase_client,
    setup_logger,
)


logger = setup_logger("document-service")


def extract_text(pdf_file: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_file))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


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
    client = get_async_openai_client()
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def summarize_text(text: str) -> str:
    client = get_async_openai_client()
    response = await client.chat.completions.create(
        model=SUMMARIZATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Summarize the following document content concisely.",
            },
            {"role": "user", "content": text},
        ],
        max_tokens=MAX_SUMMARY_TOKENS,
    )
    return response.choices[0].message.content


async def save_document(
    user_id: str,
    title: str,
    filename: str,
    original_content: str,
    chunks: list[str],
    embeddings: list[list[float]],
    file_size: int,
) -> str:
    supabase = get_supabase_client()
    document_id = str(uuid.uuid4())

    # Insert document metadata and full content
    supabase.table("documents").insert(
        {
            "document_id": document_id,
            "user_id": user_id,
            "title": title,
            "size": file_size,
            "content": original_content,
        }
    ).execute()

    # Insert chunks with embeddings into vector_store
    for chunk, embedding in zip(chunks, embeddings, strict=False):
        supabase.table("vector_store").insert(
            {
                "document_id": document_id,
                "content": chunk,
                "embedding": embedding,
            }
        ).execute()

    return document_id


async def save_summary(user_id: str, content: str) -> str:
    supabase = get_supabase_client()
    result = (
        supabase.table("summary")
        .insert({"user_id": user_id, "content": content})
        .execute()
    )
    return result.data[0]["summary_id"]


async def get_documents(
    user_id: str, offset: int = 0, limit: int = DEFAULT_PAGE_SIZE
) -> dict[str, Any]:
    limit = min(limit, MAX_PAGE_SIZE)
    supabase = get_supabase_client()

    result = (
        supabase.table("documents")
        .select("document_id, title, size, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    count_result = (
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


async def get_document(document_id: str, user_id: str) -> dict[str, Any] | None:
    supabase = get_supabase_client()

    # Get document metadata and full content
    doc_result = (
        supabase.table("documents")
        .select("*")
        .eq("document_id", document_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not doc_result.data:
        return None

    document = doc_result.data[0]

    # Get chunk count from vector_store
    count_result = (
        supabase.table("vector_store")
        .select("chunk_id", count="exact")
        .eq("document_id", document_id)
        .execute()
    )

    # Create preview from full content (first 500 chars)
    preview_content = document["content"][:500]
    if len(document["content"]) > 500:
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


async def delete_document(document_id: str, user_id: str) -> bool:
    supabase = get_supabase_client()

    # Delete document (vector_store entries will cascade delete due to FK)
    result = (
        supabase.table("documents")
        .delete()
        .eq("document_id", document_id)
        .eq("user_id", user_id)
        .execute()
    )
    return len(result.data) > 0


async def search_documents(
    user_id: str, query: str, limit: int = DEFAULT_SEARCH_LIMIT
) -> list[dict[str, Any]]:
    limit = min(limit, MAX_SEARCH_LIMIT)
    supabase = get_supabase_client()
    query_embedding = await get_embedding(query)

    result = supabase.rpc(
        "search_similar_documents",
        {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "match_count": limit,
        },
    ).execute()

    return result.data


def validate_file(file: UploadFile) -> None:
    if file.content_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only {', '.join(SUPPORTED_FILE_TYPES)} are supported.",
        )

    if file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB",
        )


async def process_file(
    file: UploadFile, user_id: str, title: str = None
) -> str:
    validate_file(file)

    content = await file.read()
    text = extract_text(content)

    chunks = chunk_text(text)
    embeddings = []

    for chunk in chunks:
        embedding = await get_embedding(chunk)
        embeddings.append(embedding)

    # Use provided title or fallback to filename
    doc_title = title if title else file.filename.replace(".pdf", "")

    document_id = await save_document(
        user_id=user_id,
        title=doc_title,
        filename=file.filename,
        original_content=text,
        chunks=chunks,
        embeddings=embeddings,
        file_size=file.size,
    )

    summary = await summarize_text(text[:4000])
    await save_summary(user_id, summary)

    logger.info(f"Processed document {document_id} for user {user_id}")
    return document_id
