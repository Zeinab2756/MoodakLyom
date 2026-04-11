from typing import Optional

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    message: Optional[str] = None
