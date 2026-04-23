from __future__ import annotations

import uuid
import wave
from pathlib import Path

from app.schemas.emotion_schemas import EmotionDistribution

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _issue_token(client) -> str:
    response = client.post(
        "/user/init",
        json={
            "username": f"tester_{uuid.uuid4().hex[:8]}",
            "password": "secret123",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _frame_count(audio_path: str | Path) -> int:
    with wave.open(str(audio_path), "rb") as wav_file:
        return wav_file.getnframes()


def _patch_pipeline(monkeypatch):
    def fake_transcribe(audio_path: str, language: str | None = None):
        frames = _frame_count(audio_path)
        if frames <= 2000:
            return True, "I feel happy today", None
        if frames <= 4000:
            return True, "I feel happy today", None
        return False, None, "mock transcription failed"

    def fake_text_emotion(transcript: str):
        if "happy" in transcript:
            return EmotionDistribution(
                label="joy",
                confidence=0.91,
                distribution={"joy": 0.91, "surprise": 0.09},
                source="bert",
            )
        return EmotionDistribution(
            label="neutral",
            confidence=0.55,
            distribution={"neutral": 0.55, "sad": 0.45},
            source="bert",
        )

    def fake_acoustic_emotion(audio_path: str):
        frames = _frame_count(audio_path)
        if frames <= 2000:
            return EmotionDistribution(
                label="happy",
                confidence=0.84,
                distribution={"happy": 0.84, "neutral": 0.16},
                source="acoustic",
            )
        if frames <= 4000:
            return EmotionDistribution(
                label="angry",
                confidence=0.89,
                distribution={"angry": 0.89, "neutral": 0.11},
                source="acoustic",
            )
        return EmotionDistribution(
            label="neutral",
            confidence=0.7,
            distribution={"neutral": 0.7, "sad": 0.3},
            source="acoustic",
        )

    monkeypatch.setattr("app.routes.mood_routes.transcribe_audio_file", fake_transcribe)
    monkeypatch.setattr("app.routes.mood_routes.predict_text_emotion", fake_text_emotion)
    monkeypatch.setattr("app.routes.mood_routes.predict_acoustic_emotion", fake_acoustic_emotion)


def _post_audio(client, token: str, fixture_name: str):
    file_path = FIXTURES_DIR / fixture_name
    with file_path.open("rb") as audio_file:
        return client.post(
            "/mood/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"language": "en"},
            files={"audio_file": (file_path.name, audio_file, "audio/wav")},
        )


def test_mood_analyze_returns_fused_happy_result(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    token = _issue_token(client)

    response = _post_audio(client, token, "happy_short.wav")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mood"] == "happy"
    assert payload["sarcasm_suspected"] is False
    assert payload["degraded"] is False
    assert payload["transcript"] == "I feel happy today"


def test_mood_analyze_flags_sarcasm_when_text_and_tone_disagree(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    token = _issue_token(client)

    response = _post_audio(client, token, "sarcastic_medium.wav")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sarcasm_suspected"] is True
    assert payload["text_emotion"]["label"] == "joy"
    assert payload["acoustic_emotion"]["label"] == "angry"


def test_mood_analyze_returns_partial_results_when_transcription_fails(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    token = _issue_token(client)

    response = _post_audio(client, token, "acoustic_only_long.wav")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert payload["text_emotion"] is None
    assert payload["acoustic_emotion"]["label"] == "neutral"
    assert "mock transcription failed" in payload["warnings"]
