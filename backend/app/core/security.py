"""Password hashing utility.

Deliberately minimal: only what the Phase 1 seeder needs to store usable
password hashes for demo accounts. JWT issuance/verification and the auth
API belong to Phase 5 and are not implemented here.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return _pwd_context.verify(plain_password, password_hash)
