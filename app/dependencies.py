from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

from app.database import get_db
from app.models.user import User

load_dotenv()

# Use auto_error=False to let us return our own consistent error JSON when header is missing
security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")     # <-- safe default for dev
ALGORITHM = os.getenv("ALGORITHM", "HS256")            # <-- default to HS256

def _unauthorized(code: str, message: str = "Invalid authentication credentials"):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
        detail={"success": False, "error": {"code": code, "message": message, "details": {}}}
    )

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    # No Authorization header
    if credentials is None or not credentials.scheme or not credentials.credentials:
        _unauthorized("UNAUTHORIZED", "Missing bearer token")

    token = credentials.credentials
    try:
        # jose expects a list for algorithms
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        # Do NOT cast to int unless your primary key is an integer.
        if not user_id:
            _unauthorized("UNAUTHORIZED", "Token missing subject (sub) claim")
    except JWTError:
        _unauthorized("UNAUTHORIZED", "Invalid or expired token")

    # Look up user
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        _unauthorized("UNAUTHORIZED", "User not found")

    return user
