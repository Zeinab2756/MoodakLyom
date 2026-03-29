"""
Schemas for voice analysis endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class VoiceAnalysisResponse(BaseModel):
    """Response schema for voice analysis endpoint"""
    success: bool = Field(..., description="Whether the analysis was successful")
    transcribed_text: str = Field(..., description="The transcribed text from the audio")
    emotion: str = Field(..., description="Primary detected emotion")
    emotion_level: int = Field(..., ge=1, le=10, description="Emotion intensity level (1-10)")
    emotions: List[str] = Field(default_factory=list, description="Detected emotions (list format)")
    mood_level: int = Field(..., ge=1, le=5, description="Detected mood level (1-5) - converted from emotion_level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1) - derived from emotion_level")
    tags: List[str] = Field(default_factory=list, description="Generated tags based on emotions")
    mood_entry: Optional[dict] = Field(None, description="Created mood entry if saved")
    message: Optional[str] = Field(None, description="Additional message")


class VoiceAnalysisRequest(BaseModel):
    """Request schema for voice analysis (optional, mainly for documentation)"""
    save_to_mood: bool = Field(True, description="Whether to automatically save as mood entry")
    date: Optional[str] = Field(None, description="Date for mood entry (YYYY-MM-DD format, defaults to today)")

