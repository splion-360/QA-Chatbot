from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import chat, documents


app = FastAPI(
    title=settings.name,
    version=settings.version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix=f"{settings.prefix}/chat", tags=["chat"])
app.include_router(
    documents.router,
    prefix=f"{settings.prefix}/documents",
    tags=["documents"],
)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.name}",
        "version": settings.version,
    }
