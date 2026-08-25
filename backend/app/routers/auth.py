from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import RegisterRequest, LoginRequest, TokenResponse
from ..security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        text("SELECT 1 FROM users WHERE email = :email"), {"email": body.email}
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    row = db.execute(
        text(
            "INSERT INTO users (email, password_hash) VALUES (:email, :pw) RETURNING id"
        ),
        {"email": body.email, "pw": hash_password(body.password)},
    ).first()
    db.commit()

    token = create_access_token(str(row.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, password_hash FROM users WHERE email = :email"),
        {"email": body.email},
    ).first()
    if row is None or not verify_password(body.password, row.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(str(row.id))
    return TokenResponse(access_token=token)
