from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.config import logger
from app.mq.queue import enqueue_task
from app.schemas.documents import (
    DocumentList,
    UploadResponse,
)
from app.services.document_service import (
    delete_document,
    get_document,
    get_documents,
    process_file,
    search_documents,
)


router = APIRouter()
_file = File(...)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = _file,
    user_id: str = Query(...),
    title: str = Form(None),
):
    file_content = await file.read()
    file_data = {
        "content": file_content,
        "filename": file.filename,
        "size": file.size,
        "content_type": file.content_type,
    }

    job_id = await enqueue_task(process_file, [file_data, user_id, title])

    return UploadResponse(
        message="Document upload queued for processing",
        job_id=job_id,
        filename=file.filename,
    )


@router.get("/", response_model=DocumentList)
async def list_documents(
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: str = Query(
        None, description="Search query for document titles and content"
    ),
    search_type: str = Query("title"),
):
    offset = (page - 1) * limit

    if search and search.strip():
        result = await search_documents(
            user_id, search.strip(), search_type, offset, limit
        )
    else:
        result = await get_documents(user_id, offset, limit)

    return DocumentList(
        documents=result["documents"],
        pagination={
            "total": result["total"],
            "page": page,
            "limit": limit,
            "pages": (result["total"] + limit - 1) // limit,
        },
    )


@router.get("/{document_id}")
async def fetch_document(document_id: str, user_id: str = Query(...)):
    document = await get_document(document_id, user_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("/{document_id}/preview")
async def preview_document(document_id: str, user_id: str = Query(...)):
    document = await get_document(document_id, user_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    preview_content = document["content"][:500]
    if len(document["content"]) > 500:
        preview_content += "..."

    return {
        "document_id": document_id,
        "title": document["title"],
        "preview": preview_content,
        "total_length": len(document["content"]),
        "chunks": document["chunks"],
    }


@router.delete("/{document_id}")
async def delete(document_id: str, user_id: str = Query(...)):
    success = await delete_document(document_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info(f"Document {document_id} deleted by user {user_id}")
    return {"message": "Document deleted successfully"}
