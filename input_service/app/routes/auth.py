from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from ..auth import create_access_token, ensure_admin_user, verify_password
from ..config import ADMIN_EMAIL, ADMIN_PASSWORD
from ..db import get_user_by_email


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    ensure_admin_user(ADMIN_EMAIL, ADMIN_PASSWORD)
    user = get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = create_access_token(user["email"], user["role"])
    return TokenResponse(access_token=token)
