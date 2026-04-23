from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.emotion_schemas import EmotionDistribution


class MoodAnalyzeResponse(BaseModel):
    mood: str
    confidence: float
    distribution: dict[str, float] = Field(default_factory=dict)
    transcript: str | None = None
    text_emotion: EmotionDistribution | None = None
    acoustic_emotion: EmotionDistribution | None = None
    sarcasm_suspected: bool = False
    language: str | None = None
    processing_ms: int
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)
