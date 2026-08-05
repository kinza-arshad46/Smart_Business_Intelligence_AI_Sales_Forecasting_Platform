"""
Password hashing and JWT token utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import hashlib
import hmac
import base64
import json

from app.core.config import settings

# --- Password hashing -------------------------------------------------
# Uses passlib[bcrypt] when available; falls back to a salted PBKDF2
# implementation from the standard library so the app never hard-fails
# if bcrypt isn't installed in a given environment.
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

except ImportError:
    import os as _os

    def hash_password(password: str) -> str:
        salt = _os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return "pbkdf2$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            _, salt_b64, dk_b64 = hashed_password.split("$")
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(dk_b64)
            dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, 100_000)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False


# --- JWT ----------------------------------------------------------------
try:
    from jose import jwt, JWTError

    def create_access_token(subject: str, extra_claims: Optional[dict] = None,
                             expires_minutes: Optional[int] = None) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode = {"sub": subject, "exp": expire, "type": "access"}
        if extra_claims:
            to_encode.update(extra_claims)
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_refresh_token(subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return None

except ImportError:
    # Minimal pure-python JWT fallback (HS256) so the module still works
    # without python-jose installed. Not for production use.
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _sign(msg: bytes) -> str:
        sig = hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).digest()
        return _b64url(sig)

    def create_access_token(subject: str, extra_claims: Optional[dict] = None,
                             expires_minutes: Optional[int] = None) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"sub": subject, "exp": int(expire.timestamp()), "type": "access"}
        if extra_claims:
            payload.update(extra_claims)
        h = _b64url(json.dumps(header).encode())
        p = _b64url(json.dumps(payload).encode())
        s = _sign(f"{h}.{p}".encode())
        return f"{h}.{p}.{s}"

    def create_refresh_token(subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return create_access_token(subject, {"type": "refresh"},
                                    expires_minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)

    def decode_token(token: str) -> Optional[dict]:
        try:
            h, p, s = token.split(".")
            expected_sig = _sign(f"{h}.{p}".encode())
            if not hmac.compare_digest(expected_sig, s):
                return None
            padded = p + "=" * (-len(p) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
                return None
            return payload
        except Exception:
            return None
