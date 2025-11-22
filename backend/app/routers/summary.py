from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.config import setup_logger
from app.core.exceptions import handle_exceptions
from app.services.summary_service import SummaryService
from app.utils.auth import ensure_user_access


logger = setup_logger("summary-router")
router = APIRouter()
summary_service = SummaryService()


class SummaryRequest(BaseModel):
    user_id: str
    start_date: str
    end_date: str


class SummaryResponse(BaseModel):
    summary_id: str
    summary: str
    document_count: int
    start_date: str
    end_date: str
    created_at: str


class SummaryListResponse(BaseModel):
    summaries: list[dict]


class DeleteResponse(BaseModel):
    success: bool
    message: str


@router.post("/generate", response_model=SummaryResponse)
@handle_exceptions
async def generate_summary(
    request: SummaryRequest,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    ensure_user_access(request.user_id, x_user_id)
    result = await summary_service.generate_summary(
        user_id=request.user_id,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return SummaryResponse(
        summary_id=result["summary_id"],
        summary=result["summary"],
        document_count=result["document_count"],
        start_date=result["start_date"],
        end_date=result["end_date"],
        created_at=result["created_at"]
    )


@router.get("/list/{user_id}", response_model=SummaryListResponse)
@handle_exceptions
async def list_summaries(
    user_id: str,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    ensure_user_access(user_id, x_user_id)
    summaries = await summary_service.list_summaries(user_id)
    return SummaryListResponse(summaries=summaries)


@router.get("/{summary_id}", response_model=SummaryResponse)
@handle_exceptions
async def get_summary(
    summary_id: str,
    user_id: str = Query(...),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    ensure_user_access(user_id, x_user_id)
    summary = await summary_service.get_summary(summary_id, user_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    return SummaryResponse(
        summary_id=summary["summary_id"],
        summary=summary["content"],
        document_count=summary["document_count"],
        start_date=summary["start_date"],
        end_date=summary["end_date"],
        created_at=summary["created_at"]
    )


@router.delete("/{summary_id}/{user_id}", response_model=DeleteResponse)
@handle_exceptions
async def delete_summary(
    summary_id: str,
    user_id: str,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    ensure_user_access(user_id, x_user_id)
    success = await summary_service.delete_summary(summary_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Summary not found")

    logger.info(f"Summary {summary_id} deleted by user {user_id}")
    return DeleteResponse(success=True, message="Summary deleted successfully")
