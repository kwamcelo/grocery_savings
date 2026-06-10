import os
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import User


@dataclass
class AuthenticatedUser:
    id: str
    email: str | None = None
    display_name: str | None = None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = bearer_token_from_request(request)
    claims = verify_supabase_token(token)
    user = sync_user(db, claims)
    return user


def bearer_token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return token


def verify_supabase_token(token: str) -> AuthenticatedUser:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase auth is not configured on the server.",
        )

    try:
        response = httpx.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "apikey": supabase_key,
                "authorization": f"Bearer {token}",
            },
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not verify your sign-in. Please try again.",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=401,
            detail="Could not verify your account.",
        )

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not verify your account.")

    metadata = data.get("user_metadata") or {}
    return AuthenticatedUser(
        id=user_id,
        email=data.get("email"),
        display_name=metadata.get("full_name") or metadata.get("name"),
    )


def sync_user(db: Session, authenticated_user: AuthenticatedUser) -> User:
    user = db.get(User, authenticated_user.id)
    if user:
        user.email = authenticated_user.email
        user.display_name = authenticated_user.display_name
        db.flush()
        return user

    user = User(
        id=authenticated_user.id,
        email=authenticated_user.email,
        display_name=authenticated_user.display_name,
    )
    db.add(user)
    db.flush()
    return user
