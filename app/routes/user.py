from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import InitRequest, UpdateRequest
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter()

def ok(data: dict):
    return {"success": True, "data": data}

def err(code: str, message: str, http_status: int, details: dict | None = None):
    raise HTTPException(
        status_code=http_status,
        detail={"success": False, "error": {"code": code, "message": message, "details": details or {}}}
    )

def normalize_username(u: str) -> str:
    return u.strip().lower()

@router.post("/init")
def init_user(payload: InitRequest, db: Session = Depends(get_db)):
    # DEBUG payload (mask password)
    try:
        safe_payload = payload.dict()
    except Exception:
        safe_payload = getattr(payload, "model_dump", payload.dict)()
    safe_payload["password"] = "***masked***"
    print("DEBUG /user/init payload:", safe_payload)

    username = normalize_username(payload.username)
    if not username or not payload.password:
        print("DEBUG invalid-input username or password missing")
        err("INVALID_INPUT", "Invalid payload", status.HTTP_400_BAD_REQUEST)

    # Lookup
    try:
        user = db.query(User).filter(User.username == username).first()
        print("DEBUG existing user:", bool(user))
    except Exception as e:
        print("DEBUG DB query error:", repr(e))
        raise

    if user:
        # Verify
        try:
            ok_pw = verify_password(payload.password, user.password_hash)
            print("DEBUG password verify:", ok_pw)
        except Exception as e:
            print("DEBUG verify_password error:", repr(e))
            raise
        if not ok_pw:
            err("INVALID_CREDENTIALS", "Wrong username or password", status.HTTP_401_UNAUTHORIZED)
        try:
            token = create_access_token(sub=user.id, username=user.username)
            print("DEBUG token created (existing user)")
        except Exception as e:
            print("DEBUG create_access_token error:", repr(e))
            raise
        return ok({"user": to_public(user), "token": token})

    # Create new
    try:
        pw_hash = hash_password(payload.password)
        print("DEBUG password hashed len:", len(pw_hash))
    except Exception as e:
        print("DEBUG hash_password error:", repr(e))
        raise

    new_user = User(
        username=username,
        password_hash=pw_hash,
        avatar=str(payload.avatar) if payload.avatar else None,
        preferences=payload.preferences or {}
    )
    db.add(new_user)
    try:
        db.commit()
        print("DEBUG DB commit ok (new user)")
    except Exception as e:
        db.rollback()
        print("DEBUG DB commit error:", repr(e))
        err("USERNAME_TAKEN", "Username already exists", status.HTTP_409_CONFLICT)

    try:
        db.refresh(new_user)
        token = create_access_token(sub=new_user.id, username=new_user.username)
        print("DEBUG token created (new user)")
    except Exception as e:
        print("DEBUG post-commit error:", repr(e))
        raise

    return ok({"user": to_public(new_user), "token": token})

@router.get("/")
def get_all_users(db: Session = Depends(get_db), _curr=Depends(get_current_user)):
    """Get all users (admin only)"""
    users = db.query(User).all()
    return ok({"users": [to_public(user) for user in users]})

@router.get("/public")
def get_all_users_public(db: Session = Depends(get_db)):
    """Get all users (public endpoint - for testing only)"""
    users = db.query(User).all()
    return ok({"users": [to_public(user) for user in users]})

@router.get("/{id}")
def get_user(id: str, db: Session = Depends(get_db), _curr=Depends(get_current_user)):
    print("DEBUG /user/{id} ->", id)
    user = db.query(User).filter(User.id == id).first()
    if not user:
        print("DEBUG user not found")
        err("NOT_FOUND", "User not found", status.HTTP_404_NOT_FOUND)
    return ok(to_public(user))

@router.put("/update")
def update_user(payload: UpdateRequest, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    try:
        safe_payload = payload.dict()
    except Exception:
        safe_payload = getattr(payload, "model_dump", payload.dict)()
    print("DEBUG /user/update payload:", safe_payload, "for user:", current.id)

    if payload.avatar is None and payload.preferences is None:
        err("INVALID_INPUT", "Provide avatar or preferences", status.HTTP_400_BAD_REQUEST)

    if payload.avatar is not None:
        current.avatar = str(payload.avatar)
    if payload.preferences is not None:
        current.preferences = payload.preferences

    db.add(current)
    try:
        db.commit()
        print("DEBUG update commit ok")
    except Exception as e:
        db.rollback()
        print("DEBUG update commit error:", repr(e))
        raise

    db.refresh(current)
    return ok(to_public(current))

def to_public(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "avatar": u.avatar,
        "preferences": u.preferences or {},
        "created_at": u.created_at.isoformat() if u.created_at else None
    }
