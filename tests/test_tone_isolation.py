"""Tone-isolation checks for the acoustic branch using committed human speech fixtures.

These fixtures are sourced from RAVDESS, which uses emotionally acted but lexically neutral
sentences. The "inverted" cases therefore validate branch disagreement rather than literal
positive-vs-negative sentiment inversion.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import SHARED_EMOTION_TAXONOMY
from app.services.acoustic_emotion import predict_acoustic_emotion
from app.services.fusion import fuse
from app.services.text_emotion import predict_text_emotion
from app.services.transcription import transcribe_audio_file

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "validation"


def _fixture(name: str) -> Path:
    return FIXTURE_DIR / name


def _top_k(distribution: dict[str, float], k: int) -> list[str]:
    return [
        label
        for label, _probability in sorted(
            distribution.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:k]
    ]


def _l1_distance(left: dict[str, float], right: dict[str, float]) -> float:
    return sum(
        abs(left.get(label, 0.0) - right.get(label, 0.0))
        for label in SHARED_EMOTION_TAXONOMY
    )


def _full_pipeline(audio_name: str):
    success, transcript, _warning = transcribe_audio_file(_fixture(audio_name), language="en")
    assert success is True
    assert transcript
    text_emotion = predict_text_emotion(transcript)
    acoustic_emotion = predict_acoustic_emotion(_fixture(audio_name))
    fused = fuse(acoustic_emotion, text_emotion)
    return transcript, text_emotion, acoustic_emotion, fused


def test_same_text_1_triplet_separates_happy_sad_and_angry():
    happy = predict_acoustic_emotion(_fixture("same_text_1_happy.wav"))
    sad = predict_acoustic_emotion(_fixture("same_text_1_sad.wav"))
    angry = predict_acoustic_emotion(_fixture("same_text_1_angry.wav"))

    assert _l1_distance(happy.distribution, sad.distribution) >= 0.4
    assert _l1_distance(happy.distribution, angry.distribution) >= 0.4
    assert _l1_distance(sad.distribution, angry.distribution) >= 0.4

    assert "happy" in _top_k(happy.distribution, 2)
    assert "sad" in _top_k(sad.distribution, 2)
    assert "angry" in _top_k(angry.distribution, 2)


def test_same_text_2_triplet_separates_happy_sad_and_neutral():
    happy = predict_acoustic_emotion(_fixture("same_text_2_happy.wav"))
    sad = predict_acoustic_emotion(_fixture("same_text_2_sad.wav"))
    neutral = predict_acoustic_emotion(_fixture("same_text_2_neutral.wav"))

    assert _l1_distance(happy.distribution, sad.distribution) >= 0.4
    assert _l1_distance(happy.distribution, neutral.distribution) >= 0.4
    assert _l1_distance(sad.distribution, neutral.distribution) >= 0.4

    assert "happy" in _top_k(happy.distribution, 2)
    assert "sad" in _top_k(sad.distribution, 2)
    assert "neutral" in _top_k(neutral.distribution, 2)


def test_same_text_3_triplet_separates_happy_sad_and_angry():
    happy = predict_acoustic_emotion(_fixture("same_text_3_happy.wav"))
    sad = predict_acoustic_emotion(_fixture("same_text_3_sad.wav"))
    angry = predict_acoustic_emotion(_fixture("same_text_3_angry.wav"))

    assert _l1_distance(happy.distribution, sad.distribution) >= 0.4
    assert _l1_distance(happy.distribution, angry.distribution) >= 0.4
    assert _l1_distance(sad.distribution, angry.distribution) >= 0.4

    assert "happy" in _top_k(happy.distribution, 2)
    assert "sad" in _top_k(sad.distribution, 2)
    assert "angry" in _top_k(angry.distribution, 2)


def test_inverted_proxy_cases_show_branch_disagreement():
    for fixture_name in ("inverted_01.wav", "inverted_02.wav", "inverted_03.wav"):
        _transcript, text_emotion, acoustic_emotion, fused = _full_pipeline(fixture_name)
        assert fused.sarcasm_suspected or acoustic_emotion.label != text_emotion.label


def test_happy_intensity_proxy_increases_happy_confidence_monotonically():
    mild = predict_acoustic_emotion(_fixture("intensity_happy_mild.wav"))
    moderate = predict_acoustic_emotion(_fixture("intensity_happy_moderate.wav"))
    exuberant = predict_acoustic_emotion(_fixture("intensity_happy_exuberant.wav"))

    assert mild.distribution["happy"] < moderate.distribution["happy"] < exuberant.distribution["happy"]


def test_angry_intensity_proxy_increases_angry_confidence_monotonically():
    mild = predict_acoustic_emotion(_fixture("intensity_angry_mild.wav"))
    frustrated = predict_acoustic_emotion(_fixture("intensity_angry_frustrated.wav"))
    shouting = predict_acoustic_emotion(_fixture("intensity_angry_shouting.wav"))

    assert mild.distribution["angry"] < frustrated.distribution["angry"] < shouting.distribution["angry"]
