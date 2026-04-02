from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date as Date

class MoodCreate(BaseModel):
    """Schema for creating a new mood entry"""
    date: Date = Field(..., description="Date for the mood entry")
    moodLevel: int = Field(..., ge=1, le=5, description="Mood level from 1-5")
    emoji: Optional[str] = Field(None, description="Emoji representing the user's emotion")
    emotion: Optional[str] = Field(None, description="Named emotion linked to the selected emoji")
    tags: Optional[List[str]] = Field(None, description="List of tags (max 10)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes (max 1000 chars)")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is None:
            return v
        # Filter out empty or whitespace-only tags
        filtered_tags = [tag.strip() for tag in v if tag.strip()]
        # Validate each tag length and limit to 10 tags
        if len(filtered_tags) > 10:
            raise ValueError('Maximum 10 tags allowed')
        for tag in filtered_tags:
            if len(tag) > 20:
                raise ValueError('Each tag must be 20 characters or less')
        return filtered_tags

class MoodResponse(BaseModel):
    """Schema for mood entry response"""
    id: int
    userId: str = Field(..., alias="user_id")
    date: Date
    moodLevel: int = Field(..., alias="mood_level")
    emoji: Optional[str] = None
    emotion: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [tag.strip() for tag in v.split(',') if tag.strip()]
        return v

class MoodSummary(BaseModel):
    """Schema for mood summary response"""
    total: int
    average: float
    byDay: List[dict] = Field(..., alias="by_day")
    topTags: List[str] = Field(..., alias="top_tags")
    trend: str = Field(..., alias="trend")

    model_config = {"from_attributes": True}

class MoodListResponse(BaseModel):
    """Schema for paginated mood list response"""
    moods: List[MoodResponse]
    total: int
    limit: int
    offset: int


class EmojiEmotion(BaseModel):
    emoji: str
    emotion: str


class EmojiEmotionList(BaseModel):
    options: List[EmojiEmotion]