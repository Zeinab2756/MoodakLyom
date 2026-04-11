import os
import tempfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.voice import TranscriptionResponse
from app.services.transcription import transcribe_audio_file

router = APIRouter()


def _extract_multipart_parts(content_type: str, body: bytes) -> tuple[bytes | None, str | None, str | None]:
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )

    audio_bytes = None
    filename = None
    language = None
    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if field_name == "language":
            payload = part.get_payload(decode=True) or b""
            language = payload.decode("utf-8", errors="ignore").strip() or None
            continue

        if field_name == "audio_file":
            audio_bytes = part.get_payload(decode=True)
            filename = part.get_filename()

    return audio_bytes, filename, language


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_voice(
    request: Request,
    _current_user: User = Depends(get_current_user),
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return TranscriptionResponse(success=False, text=None, message="Expected multipart/form-data")

    body = await request.body()
    audio_bytes, filename, language = _extract_multipart_parts(content_type, body)
    if not audio_bytes:
        return TranscriptionResponse(success=False, text=None, message="Missing audio_file field")

    suffix = Path(filename or "audio.m4a").suffix or ".m4a"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        success, text, message = transcribe_audio_file(temp_path, language=language)
        return TranscriptionResponse(success=success, text=text, message=message)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
