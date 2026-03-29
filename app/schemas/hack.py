"""Pydantic schemas for the Hacks feature.

Defines request and response models used by the FastAPI endpoints. Response
models enable ORM mode to populate from SQLAlchemy objects.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class HackBase(BaseModel):
    """Fields shared by create and response models."""

    # Concise headline
    title: str = Field(..., min_length=1, max_length=200)

    # Main body text of the article/tip
    content: str = Field(..., min_length=1, max_length=20000)

    # Optional grouping label (e.g. productivity, wellness)
    category: Optional[str] = Field(None, max_length=50)

    # Optional tags list presented to clients; stored as CSV in DB
    tags: Optional[List[str]] = None


class HackCreate(HackBase):
    """Payload for creating a hack."""

    pass


class HackUpdate(BaseModel):
    """Partial update payload; only provided fields are updated."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None


class HackResponse(BaseModel):
    """Response model returned to clients."""

    id: int
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    # Enable reading from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)


class HackListResponse(BaseModel):
    """Standard list wrapper with pagination counters."""

    success: bool = True
    data: List[HackResponse]
    total: int
    limit: int
    offset: int


class HackSingleResponse(BaseModel):
    """Standard single-entity wrapper."""

    success: bool = True
    data: HackResponse
