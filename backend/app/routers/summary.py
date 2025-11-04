from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import logger
from app.services.summary_service import SummaryService

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
async def generate_summary(request: SummaryRequest):
    """Generate a summary for documents in date range."""
    try:
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.get("/list/{user_id}", response_model=SummaryListResponse)
async def list_summaries(user_id: str):
    """Get all summaries for a user."""
    try:
        summaries = await summary_service.list_summaries(user_id)
        return SummaryListResponse(summaries=summaries)
    except Exception as e:
        logger.error(f"Failed to fetch summaries: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch summaries: {str(e)}"
        )


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(summary_id: str, user_id: str = Query(...)):
    """Get a specific summary by ID."""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch summary: {str(e)}"
        )


@router.delete("/{summary_id}/{user_id}", response_model=DeleteResponse)
async def delete_summary(summary_id: str, user_id: str):
    """Delete a specific summary."""
    try:
        success = await summary_service.delete_summary(summary_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        logger.info(f"Summary {summary_id} deleted by user {user_id}")
        return DeleteResponse(
            success=True,
            message="Summary deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete summary: {str(e)}"
        )