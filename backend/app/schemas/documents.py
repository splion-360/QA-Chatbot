from pydantic import BaseModel


class DocumentUpload(BaseModel):
    user_id: str


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    created_at: str


class DocumentDetail(BaseModel):
    document_id: str
    title: str
    content: str
    chunks: int
    created_at: str


class DocumentPreview(BaseModel):
    document_id: str
    title: str
    preview: str
    total_length: int
    chunks: int


class DocumentList(BaseModel):
    documents: list[DocumentResponse]
    pagination: dict


class UploadResponse(BaseModel):
    message: str
    job_id: str
    filename: str
