"""Authentication business logic."""

from sqlmodel import Session, select

from app.core.security import verify_password
from app.models import User


def authenticate(session: Session, email: str, password: str) -> User | None:
    """Return the matching active user if the credentials are valid, else None."""
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
