from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Document Summarization Service",
    description="AI-powered document summarization",
    version="1.0.0"
)

# CORS - Allow Next.js frontend to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Request/Response models
class SummarizeRequest(BaseModel):
    content: str
    start_date: str
    end_date: str
    document_count: int

class SummarizeResponse(BaseModel):
    summary: str

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_documents(request: SummarizeRequest):
    """
    Generate a markdown summary of documents.
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    try:
        # Build the prompt
        prompt = f"""You are an expert document summarizer. Generate a comprehensive markdown summary of the following documents.

**Context:**
- Date Range: {request.start_date} to {request.end_date}
- Total Documents: {request.document_count}

**Task:**
Create a well-structured summary with:
1. Executive Summary (2-3 sentences)
2. Key Topics & Themes
3. Main Points from Each Document
4. Important Findings or Conclusions

**Documents:**
{request.content}

**Output Format:** Well-formatted markdown with clear sections."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional document analyst who creates clear, concise summaries."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        summary = response.choices[0].message.content
        
        return SummarizeResponse(summary=summary)
    
    except Exception as e:
        print(f"Error during summarization: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Summarization failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Document Summarization",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
