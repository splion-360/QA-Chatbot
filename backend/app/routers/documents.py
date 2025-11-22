from fastapi import (
    APIRouter,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
)

from app.config import setup_logger
from app.core.exceptions import handle_exceptions
from app.mq.queue import enqueue_task
from app.schemas.documents import DocumentList, UploadResponse
from app.services.document_service import document_service
from app.utils.auth import ensure_user_access


logger = setup_logger("documents-router")
router = APIRouter()
_file = File(...)


@router.post("/upload", response_model=UploadResponse)
@handle_exceptions
async def upload_document(
    file: UploadFile = _file,
    user_id: str = Query(...),
    title: str = Form(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    current_user = ensure_user_access(user_id, x_user_id)
    file_content = await file.read()
    file_data = {
        "content": file_content,
        "filename": file.filename,
        "size": file.size,
        "content_type": file.content_type,
    }

    job_id = await enqueue_task(
        document_service.process_file, [file_data, current_user, title]
    )

    return UploadResponse(
        message="Document upload queued for processing",
        job_id=job_id,
        filename=file.filename,
    )


@router.get("/", response_model=DocumentList)
@handle_exceptions
async def list_documents(
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: str = Query(None, description="Search query for document titles"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    current_user = ensure_user_access(user_id, x_user_id)
    offset = (page - 1) * limit

    if search and search.strip():
        result = await document_service.search_documents(
            current_user, search.strip(), offset, limit
        )
    else:
        result = await document_service.get_documents(
            current_user, offset, limit
        )

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
@handle_exceptions
async def fetch_document(
    document_id: str,
    user_id: str = Query(...),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    current_user = ensure_user_access(user_id, x_user_id)
    document = await document_service.get_document(document_id, current_user)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("/{document_id}/preview")
@handle_exceptions
async def preview_document(
    document_id: str,
    user_id: str = Query(...),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    current_user = ensure_user_access(user_id, x_user_id)
    document = await document_service.get_document(document_id, current_user)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "title": document["title"],
        "preview": document["preview"],
        "total_length": document["total_length"],
        "chunks": document["chunks"],
    }


@router.delete("/{document_id}")
@handle_exceptions
async def delete(
    document_id: str,
    user_id: str = Query(...),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    current_user = ensure_user_access(user_id, x_user_id)
    success = await document_service.delete_document(document_id, current_user)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info(f"Document {document_id} deleted by user {current_user}")
    return {"message": "Document deleted successfully"}
