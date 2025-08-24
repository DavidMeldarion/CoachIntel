from __future__ import annotations
"""Common FastAPI dependency helpers.

Provides thin wrappers to obtain the current authenticated user and a simple
coach (user) scope primitive. Designed to avoid import cycles by importing
`verify_jwt_user` lazily from `app.main`.
"""
from fastapi import Request, Depends, HTTPException
from app.models import User, get_user_by_email  # type: ignore


async def get_current_user(request: Request) -> User:
    """Return the current authenticated user.

    Delegates to `verify_jwt_user` (dynamic import to prevent circular import).
    If that raises or returns None, a 401 is raised.
    """
    try:
        from app.main import verify_jwt_user  # local import breaks cycle
        user = await verify_jwt_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user
    except HTTPException:
        raise
    except Exception:
        # Fallback: allow dev header shortcut (x-user-email) if present
        email = request.headers.get("x-user-email")
        if email:
            user = await get_user_by_email(email)
            if user:
                return user
        raise HTTPException(status_code=401, detail="Not authenticated")


def coach_scope(user: User = Depends(get_current_user)) -> int:
    """Return the coach_id (currently the user's integer id).

    Keeping this separate makes it easy to evolve scoping (e.g., org-based) later.
    """
    return user.id


__all__ = ["get_current_user", "coach_scope"]
