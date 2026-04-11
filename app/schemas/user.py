from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class Preferences(BaseModel):
    model_config = ConfigDict(extra="allow")


class UserPublic(BaseModel):
    id: str
    username: str
    avatar: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    createdAt: str = Field(..., alias="created_at")

    model_config = ConfigDict(populate_by_name=True)


class InitRequest(BaseModel):
    username: str
    password: str
    avatar: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UpdateRequest(BaseModel):
    avatar: Optional[str] = None
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
