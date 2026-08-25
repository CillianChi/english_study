from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> str:
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    exists = db.execute(
        text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id}
    ).first()
    if exists is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return user_id
