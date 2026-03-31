import hashlib
import hmac
import secrets
from typing import Optional


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    Stored format: salt$hash
    """
    salt = salt or secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_value: str) -> bool:
    try:
        salt, stored_hash = stored_value.split("$", 1)
    except ValueError:
        return False

    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()

    return hmac.compare_digest(candidate_hash, stored_hash)