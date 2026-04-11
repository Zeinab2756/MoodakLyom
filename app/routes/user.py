import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import InitRequest, UpdateRequest

router = APIRouter()
ALLOW_PUBLIC_USER_LIST = os.getenv("ALLOW_PUBLIC_USER_LIST", "false").lower() == "true"


def ok(data: dict):
    return {"success": True, "data": data}


def err(code: str, message: str, http_status: int, details: dict | None = None):
    raise HTTPException(
        status_code=http_status,
        detail={"success": False, "error": {"code": code, "message": message, "details": details or {}}},
    )


def normalize_username(value: str) -> str:
    return value.strip().lower()


def to_public(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "preferences": user.preferences or {},
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/init")
def init_user(payload: InitRequest, db: Session = Depends(get_db)):
    username = normalize_username(payload.username)
    if not username or not payload.password:
        err("INVALID_INPUT", "Invalid payload", status.HTTP_400_BAD_REQUEST)

    user = db.query(User).filter(User.username == username).first()
    if user:
        if not verify_password(payload.password, user.password_hash):
            err("INVALID_CREDENTIALS", "Wrong username or password", status.HTTP_401_UNAUTHORIZED)
        token = create_access_token(sub=user.id, username=user.username)
        return ok({"user": to_public(user), "token": token})

    new_user = User(
        username=username,
        password_hash=hash_password(payload.password),
        avatar=payload.avatar,
        preferences=payload.preferences or {},
    )
    db.add(new_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        err("USERNAME_TAKEN", "Username already exists", status.HTTP_409_CONFLICT)

    db.refresh(new_user)
    token = create_access_token(sub=new_user.id, username=new_user.username)
    return ok({"user": to_public(new_user), "token": token})


@router.get("/")
def get_all_users(db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)):
    users = db.query(User).all()
    return ok({"users": [to_public(user) for user in users]})


@router.get("/public")
def get_all_users_public(db: Session = Depends(get_db)):
    if not ALLOW_PUBLIC_USER_LIST:
        err("NOT_FOUND", "Endpoint disabled", status.HTTP_404_NOT_FOUND)
    users = db.query(User).all()
    return ok({"users": [to_public(user) for user in users]})


@router.get("/{id}")
def get_user(id: str, db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        err("NOT_FOUND", "User not found", status.HTTP_404_NOT_FOUND)
    return ok(to_public(user))


@router.put("/update")
def update_user(
    payload: UpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.avatar is None and payload.preferences is None:
        err("INVALID_INPUT", "Provide avatar or preferences", status.HTTP_400_BAD_REQUEST)

    if payload.avatar is not None:
        current_user.avatar = payload.avatar
    if payload.preferences is not None:
        current_user.preferences = {**(current_user.preferences or {}), **payload.preferences}

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return ok(to_public(current_user))
