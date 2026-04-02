from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional, Dict, Any

class Preferences(BaseModel):
    # Free schema; accept any keys
    model_config = ConfigDict(extra="allow")

class UserPublic(BaseModel):
    id: str
    username: str
    avatar: Optional[str] = None
    preferences: Dict[str, Any] = {}
    createdAt: str = Field(..., alias="created_at")

    model_config = ConfigDict(populate_by_name=True)

class InitRequest(BaseModel):
    username: str
    password: str
    avatar: Optional[HttpUrl] = None
    preferences: Optional[Dict[str, Any]] = None

class UpdateRequest(BaseModel):
    avatar: Optional[HttpUrl] = None
    preferences: Optional[Dict[str, Any]] = None

class TokenResponse(BaseModel):
    user: UserPublic
    token: str

class ApiSuccess(BaseModel):
    success: bool = True
    data: dict

class ApiError(BaseModel):
    success: bool = False
    error: Dict[str, Any]
