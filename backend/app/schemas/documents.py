from pydantic import BaseModel


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    size: int
    created_at: str


class DocumentList(BaseModel):
    documents: list[DocumentResponse]
    pagination: dict


class UploadResponse(BaseModel):
    message: str
    job_id: str
    filename: str
