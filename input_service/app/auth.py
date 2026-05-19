from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext

from .config import JWT_EXP_MINUTES, JWT_ISSUER, JWT_SECRET
from .db import create_user, get_user_by_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(email: str, role: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": email,
        "role": role,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXP_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISSUER)


def ensure_admin_user(email: str, password: str) -> None:
    existing = get_user_by_email(email)
    if existing:
        return
    create_user(
        user_id=uuid.uuid4().hex,
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
