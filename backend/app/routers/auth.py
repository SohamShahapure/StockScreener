"""
Phase 11 auth endpoints. The login is "register-or-login" in one call: a
brand-new username creates the account, an existing one logs in. Passphrase
rules:
- New user + passphrase given -> account is created *with* that passphrase.
- New user, no passphrase   -> open account (anyone who types that username
  is that user - the low-friction identifier model the project chose).
- Existing user *with* a passphrase -> the passphrase must match.
- Existing user *without* one, passphrase given -> they "claim" it now.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import crud, models
from app.db.database import get_db
from app.models.schemas import AuthResponse, LoginRequest, PreferencesUpdate, UserResponse
from app.services import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="Username can't be empty.")
    if len(username) > 40:
        raise HTTPException(status_code=422, detail="Username must be 40 characters or fewer.")

    user = crud.get_user_by_username(db, username)
    is_new = user is None

    if user is None:
        user = crud.create_user(db, username, passphrase=payload.passphrase)
    elif user.passphrase_hash:
        # Protected account - the passphrase must match.
        if not payload.passphrase or not auth.verify_passphrase(payload.passphrase, user.passphrase_hash):
            raise HTTPException(status_code=401, detail="Incorrect passphrase for this username.")
    elif payload.passphrase:
        # Open account, user is now setting a passphrase - let them claim it.
        crud.set_user_passphrase(db, user, payload.passphrase)

    token = auth.create_token(user.id, user.username)
    return AuthResponse(token=token, username=user.username, has_passphrase=bool(user.passphrase_hash), is_new=is_new)


@router.get("/me", response_model=UserResponse)
def me(user: models.User = Depends(get_current_user)):
    return UserResponse(
        username=user.username,
        has_passphrase=bool(user.passphrase_hash),
        preferences=json.loads(user.preferences) if user.preferences else {},
    )


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: PreferencesUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.update_user_preferences(db, user, payload.preferences)
    return UserResponse(username=user.username, has_passphrase=bool(user.passphrase_hash), preferences=payload.preferences)
