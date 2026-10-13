import os
from typing import Optional

from fastapi import Request
from itsdangerous import URLSafeSerializer
from sqlalchemy.orm import Session

from .database import verify_password
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-in-production")
serializer = URLSafeSerializer(SECRET_KEY)


def login_user(username: str, password: str, db: Session) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_session_token(user: User) -> str:
    return serializer.dumps({"user_id": user.id, "username": user.username})


def get_current_user(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        data = serializer.loads(token)
        return db.query(User).filter(User.id == data["user_id"]).first()
    except Exception:
        return None
