from typing import List

from pydantic import BaseModel, Field

# just for reference
class EmotionRequest(BaseModel):
    text: str

class EmotionAlternative(BaseModel):
    emotion: str
    probability: float


class EmotionResponse(BaseModel):
    primary_emotion: str
    confidence: float
    alternative_emotions: List[EmotionAlternative]


class EmotionDistribution(BaseModel):
    label: str
    confidence: float
    distribution: dict[str, float] = Field(default_factory=dict)
    source: str = "unknown"
