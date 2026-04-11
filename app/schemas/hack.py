from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HackCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[list[str]] = None


class HackUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[list[str]] = None


class HackResponse(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HackSingleResponse(BaseModel):
    success: bool = True
    data: HackResponse


class HackListResponse(BaseModel):
    success: bool = True
    data: list[HackResponse]
    total: int
    limit: int
    offset: int


class WellnessTip(BaseModel):
    id: int
    title: str
    description: str
    category: Optional[str] = None
    tags: Optional[list[str]] = None
