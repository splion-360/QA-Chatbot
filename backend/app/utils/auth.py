"""Simple helpers for verifying user-scoped requests."""

from fastapi import HTTPException, status


def ensure_user_access(requested_user_id: str, header_user_id: str | None) -> str:
    """Validate that the caller is authorized to act on behalf of the user."""
    if not header_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )

    if requested_user_id != header_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to act on behalf of this user",
        )

    return requested_user_id
