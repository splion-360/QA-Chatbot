from datetime import datetime
from typing import List, Optional
import os

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from supabase import create_client, Client

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Service role for backend
)

router = APIRouter(prefix="/summary", tags=["summary"])


# Models
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
    summaries: List[dict]


class DeleteResponse(BaseModel):
    success: bool
    message: str


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(request: SummaryRequest):
    """Generate a summary for documents in date range."""
    
    try:
        # 1. Fetch documents from database
        response = supabase.table('documents') \
            .select('document_id, title, content, created_at') \
            .eq('user_id', request.user_id) \
            .gte('created_at', request.start_date) \
            .lte('created_at', request.end_date) \
            .order('created_at') \
            .execute()
        
        documents = response.data
        
        if not documents:
            raise HTTPException(
                status_code=404,
                detail="No documents found in the specified date range"
            )
        
        # 2. Group chunks by document_id
        document_map = {}
        for doc in documents:
            doc_id = doc['document_id']
            if doc_id not in document_map:
                document_map[doc_id] = {
                    'title': doc['title'],
                    'content': [doc['content']],
                    'created_at': doc['created_at']
                }
            else:
                document_map[doc_id]['content'].append(doc['content'])
        
        # 3. Format for summarization
        aggregated_content = "\n\n---\n\n".join([
            f"## {doc['title']}\n\n{' '.join(doc['content'])}"
            for doc in document_map.values()
        ])
        
        # 4. Generate summary with OpenAI
        prompt = f"""You are an expert document summarizer. Generate a comprehensive markdown summary of the following documents.

**Context:**
- Date Range: {request.start_date} to {request.end_date}
- Total Documents: {len(document_map)}

**Task:**
Create a well-structured summary with:
1. Executive Summary (2-3 sentences)
2. Key Topics & Themes
3. Main Points from Each Document
4. Important Findings or Conclusions

**Documents:**
{aggregated_content}

**Output Format:** Well-formatted markdown with clear sections."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional document analyst who creates clear, concise summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        summary_content = response.choices[0].message.content
        
        # 5. Save to database
        save_response = supabase.table('summary').insert({
            'user_id': request.user_id,
            'content': summary_content,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'document_count': len(document_map)
        }).execute()
        
        saved_summary = save_response.data[0]
        
        return SummaryResponse(
            summary_id=saved_summary['summary_id'],
            summary=summary_content,
            document_count=len(document_map),
            start_date=request.start_date,
            end_date=request.end_date,
            created_at=saved_summary['created_at']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.get("/list/{user_id}", response_model=SummaryListResponse)
async def list_summaries(user_id: str):
    """Get all summaries for a user."""
    
    try:
        response = supabase.table('summary') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .execute()
        
        return SummaryListResponse(summaries=response.data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch summaries: {str(e)}"
        )


@router.delete("/{summary_id}/{user_id}", response_model=DeleteResponse)
async def delete_summary(summary_id: str, user_id: str):
    """Delete a specific summary."""
    
    try:
        # Verify ownership
        check = supabase.table('summary') \
            .select('user_id') \
            .eq('summary_id', summary_id) \
            .eq('user_id', user_id) \
            .execute()
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        # Delete
        supabase.table('summary') \
            .delete() \
            .eq('summary_id', summary_id) \
            .execute()
        
        return DeleteResponse(
            success=True,
            message="Summary deleted successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete summary: {str(e)}"
        )