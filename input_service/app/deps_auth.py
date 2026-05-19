from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization.")
    try:
        payload = decode_token(credentials.credentials)
        return {"email": payload["sub"], "role": payload.get("role", "user")}
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc
