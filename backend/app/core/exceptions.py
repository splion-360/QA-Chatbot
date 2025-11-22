from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from postgrest.exceptions import APIError

from app.config import setup_logger


logger = setup_logger("exceptions")

F = TypeVar("F", bound=Callable[..., Any])


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        log_error: bool = True
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.log_error = log_error
        super().__init__(detail)


class DocumentProcessingError(AppException):
    def __init__(self, document_id: str, user_id: str, reason: str) -> None:
        self.document_id = document_id
        self.user_id = user_id
        self.reason = reason
        super().__init__(
            status_code=500,
            detail=f"Document processing failed: {reason}"
        )


class VectorizationError(AppException):
    def __init__(self, document_id: str, reason: str) -> None:
        self.document_id = document_id
        self.reason = reason
        super().__init__(
            status_code=500,
            detail=f"Vectorization failed: {reason}"
        )


class DatabaseError(AppException):
    def __init__(self, operation: str, table: str, reason: str) -> None:
        self.operation = operation
        self.table = table
        self.reason = reason
        super().__init__(
            status_code=500,
            detail=f"Database {operation} on {table} failed: {reason}"
        )


class ModelError(AppException):
    def __init__(self, model: str, reason: str) -> None:
        self.model = model
        self.reason = reason
        super().__init__(
            status_code=503,
            detail=f"Model {model} failed: {reason}"
        )


class ToolExecutionError(AppException):
    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(
            status_code=500,
            detail=f"Tool {tool_name} execution failed: {reason}"
        )


def handle_exceptions(func: F) -> F:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except AppException as e:
            if e.log_error:
                logger.error(f"{func.__name__}: {e.detail}")
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except APIError as e:
            logger.error(f"{func.__name__}: Database error - {e.message}")
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"{func.__name__}: Unexpected error - {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper
