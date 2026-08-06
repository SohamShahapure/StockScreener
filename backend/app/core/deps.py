"""
Shared FastAPI dependencies. `get_current_user` is the auth gate: it reads
the Bearer token, verifies its HMAC signature, and loads the matching user -
raising a clean 401 (never a 500) on anything missing, malformed, or forged.
Any router that depends on it becomes per-user automatically.
"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import crud, models
from app.db.database import get_db
from app.services import auth


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated - sign in first.")

    token = authorization.split(" ", 1)[1].strip()
    payload = auth.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session - sign in again.")

    user = crud.get_user_by_id(db, payload.get("uid"))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists - sign in again.")

    return user
