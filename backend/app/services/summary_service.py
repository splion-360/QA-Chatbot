import os
import typing as Any

from openai import OpenAI
from postgrest.exceptions import APIError

from app.config import get_supabase_client, setup_logger
from app.mq.exceptions import DatabaseError

logger = setup_logger("summary-service")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class summaryService:
    """Service for generating and managing document summaries."""

    def __init__(self):
        self.openai_client = openai_client

    async def generate_summary(
        self, user_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """
        Generate a summary for documents in the specified date range.
        
        Args:
            user_id: User identifier
            start_date: Start date for filtering documents
            end_date: End date for filtering documents
            
        Returns:
            Dictionary containing summary details
            
        Raises:
            ValueError: If no documents found
            DatabaseError: If database operation fails
        """
        try:
            # fetch documents from database
            supabase = await get_supabase_client()
            response = await (
                supabase.table('documents')
                .select('document_id, title, content, created_at')
                .eq('user_id', user_id)
                .gte('created_at', start_date)
                .lte('created_at', end_date)
                .order('created_at')
                .execute()
            )
            documents = response.data
        
            if not documents:
                raise ValueError(
                    "No documents found in the specified date range"
                )
        
            # Group chunks by document_id
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
        
            # Format for summarization
            aggregated_content = "\n\n---\n\n".join([
                f"## {doc['title']}\n\n{' '.join(doc['content'])}"
                for doc in document_map.values()
            ])
            
            # Generate summary with OpenAI
            summary_content = await self.generate_summary(
                aggregated_content,
                start_date,
                end_date,
                len(document_map)
            )

            # Save to database
            saved_summary = await self.save_summary(
                user_id=user_id,
                content=summary_content,
                start_date=start_date,
                end_date=end_date,
                document_count=len(document_map)
            )

            logger.info(
                f"Generated summary {saved_summary['summary_id']} for user {user_id}"
            )

            return {
                "summary_id":saved_summary['summary_id'],
                "summary":summary_content,
                "document_count":len(document_map),
                "start_date":start_date,
                "end_date":end_date,
                "created_at":saved_summary['created_at']
            }
        
        except ValueError:
            raise
        except APIError as e:
            raise DatabaseError("select", "documents", e.message) from e
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            raise

    async def _generate_ai_summary(
        self, content: str, start_date: str, end_date: str, doc_count: int
    ) -> str:
        """Generate AI summary using OpenAI."""
        prompt = f"""You are an expert document summarizer. Generate a comprehensive markdown summary of the following documents.

**Context:**
- Date Range: {start_date} to {end_date}
- Total Documents: {doc_count}

**Task:**
Create a well-structured summary with:
1. Executive Summary (2-3 sentences)
2. Key Topics & Themes
3. Main Points from Each Document
4. Important Findings or Conclusions

**Documents:**
{content}

**Output Format:** Well-formatted markdown with clear sections."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional document analyst who creates clear, concise summaries."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content        
        
    async def _save_summary(
        self,
        user_id: str,
        content: str,
        start_date: str,
        end_date: str,
        document_count: int
    ) -> dict[str, Any]:
        """Save summary to database."""
        try:
            supabase = await get_supabase_client()
            save_response = await (
                supabase.table('summary')
                .insert({
                    'user_id': user_id,
                    'content': content,
                    'start_date': start_date,
                    'end_date': end_date,
                    'document_count': document_count
                })
                .execute()
            )
            
            return save_response.data[0]
            
        except APIError as e:
            raise DatabaseError("insert", "summary", e.message) from e


    async def list_summaries(self, user_id: str) -> list[dict[str, Any]]:
        """Get all summaries for a user."""
        try:
            supabase = await get_supabase_client()
            response = await (
                supabase.table('summary')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .execute()
            )
            
            return response.data
            
        except APIError as e:
            raise DatabaseError("select", "summary", e.message) from e


    async def get_summary(
        self, summary_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get a specific summary by ID."""
        try:
            supabase = await get_supabase_client()
            response = await (
                supabase.table('summary')
                .select('*')
                .eq('summary_id', summary_id)
                .eq('user_id', user_id)
                .single()
                .execute()
            )
            
            return response.data if response.data else None
            
        except APIError as e:
            raise DatabaseError("select", "summary", e.message) from e


    async def delete_summary(self, summary_id: str, user_id: str) -> bool:
        """Delete a specific summary."""
        try:
            supabase = await get_supabase_client()
            
            check = await (
                supabase.table('summary')
                .select('user_id')
                .eq('summary_id', summary_id)
                .eq('user_id', user_id)
                .execute()
            )
            
            if not check.data:
                return False
            
            await (
                supabase.table('summary')
                .delete()
                .eq('summary_id', summary_id)
                .execute()
            )
            
            return True
            
        except APIError as e:
            raise DatabaseError("delete", "summary", e.message) from e