"""FastAPI dependencies: current user and role enforcement.

Role checks live here as reusable dependencies (Section H: "role
enforcement as a FastAPI dependency, not scattered inline checks") rather
than being duplicated inline in each route handler. Row-level scoping
that goes beyond a simple role check (a lecturer seeing only their own
courses' students, an adviser only their assigned students, a student
only themself) lives in the service layer, applied on top of these.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import JWTError, decode_access_token
from app.db.session import get_session
from app.models import User
from app.models.enums import UserRole

_settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{_settings.api_v1_prefix}/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        raise credentials_exception
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    """Dependency factory: 403s unless the current user's role is one of `roles`."""
    allowed = set(roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to access this endpoint.",
            )
        return current_user

    return _checker


require_admin = require_roles(UserRole.ADMIN)
require_admin_or_lecturer = require_roles(UserRole.ADMIN, UserRole.LECTURER)
require_admin_or_adviser = require_roles(UserRole.ADMIN, UserRole.ADVISER)
require_any_staff = require_roles(UserRole.ADMIN, UserRole.LECTURER, UserRole.ADVISER)
require_any_role = require_roles(UserRole.ADMIN, UserRole.LECTURER, UserRole.ADVISER, UserRole.STUDENT)
