"""Password hashing with Argon2id. Plaintext passwords are never stored or logged."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()
# Verified when an account does not exist, so a response time does not reveal which emails exist.
_DUMMY_HASH = _hasher.hash("finguard-account-does-not-exist")


def hash_password(password: str) -> str:
    """Return a salted Argon2id hash."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True if the password matches. Any failure, including a damaged hash, is False."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_against_dummy(password: str) -> None:
    """Spend the same time as a real check, for an account that does not exist."""
    verify_password(_DUMMY_HASH, password)
