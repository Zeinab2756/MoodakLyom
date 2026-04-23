from __future__ import annotations

import asyncio
import os
import time
from functools import partial

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.user import User
from app.routes.voice import _extract_multipart_parts, _save_temp_audio_file
from app.schemas.mood_analysis import MoodAnalyzeResponse
from app.schemas.emotion_schemas import EmotionDistribution
from app.services.acoustic_emotion import predict_acoustic_emotion
from app.services.fusion import fuse
from app.services.text_emotion import predict_text_emotion
from app.services.transcription import transcribe_audio_file

router = APIRouter(prefix="/mood", tags=["Mood Analysis"])


def _format_warning(prefix: str, exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return f"{prefix}: {message}"


@router.post("/analyze", response_model=MoodAnalyzeResponse)
async def analyze_mood(
    request: Request,
    _current_user: User = Depends(get_current_user),
):
    started_at = time.perf_counter()
    warnings: list[str] = []
    degraded = False
    transcript: str | None = None
    text_emotion: EmotionDistribution | None = None
    acoustic_emotion: EmotionDistribution | None = None

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected multipart/form-data",
        )

    body = await request.body()
    audio_bytes, filename, language = _extract_multipart_parts(content_type, body)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing audio_file field",
        )

    temp_path = _save_temp_audio_file(audio_bytes, filename)
    try:
        loop = asyncio.get_running_loop()
        try:
            transcribe_result = await loop.run_in_executor(
                None,
                partial(transcribe_audio_file, temp_path, language=language),
            )
        except Exception as exc:
            transcribe_result = (False, None, _format_warning("Transcription failed", exc))

        transcribe_success, transcript, transcription_message = transcribe_result
        if transcription_message:
            warnings.append(transcription_message)
            degraded = True

        branch_tasks = [
            loop.run_in_executor(None, partial(predict_acoustic_emotion, temp_path)),
        ]
        branch_names = ["acoustic"]

        if transcribe_success and transcript:
            branch_tasks.append(
                loop.run_in_executor(None, partial(predict_text_emotion, transcript))
            )
            branch_names.append("text")
        else:
            warnings.append("Text emotion skipped because transcription did not produce text")
            degraded = True

        branch_results = await asyncio.gather(*branch_tasks, return_exceptions=True)
        for branch_name, branch_result in zip(branch_names, branch_results):
            if isinstance(branch_result, Exception):
                warnings.append(_format_warning(f"{branch_name.title()} emotion failed", branch_result))
                degraded = True
                continue

            if branch_name == "acoustic":
                acoustic_emotion = branch_result
            elif branch_name == "text":
                text_emotion = branch_result

        fused = fuse(acoustic_emotion, text_emotion)
        if acoustic_emotion is None and text_emotion is None:
            degraded = True
            warnings.append("No emotion branch completed successfully")

        return MoodAnalyzeResponse(
            mood=fused.label,
            confidence=fused.confidence,
            distribution=fused.distribution,
            transcript=transcript,
            text_emotion=text_emotion,
            acoustic_emotion=acoustic_emotion,
            sarcasm_suspected=fused.sarcasm_suspected,
            language=language,
            processing_ms=int((time.perf_counter() - started_at) * 1000),
            degraded=degraded,
            warnings=warnings,
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
