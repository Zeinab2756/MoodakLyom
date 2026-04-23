from __future__ import annotations

import asyncio
from typing import Any

from app.models.emotion_model import emotion_classifier
from app.schemas.emotion_schemas import EmotionDistribution
from app.services.emotion_detection import predict_external_emotion, predict_keyword_emotion


def _normalize_label(label: str | None) -> str | None:
    if not label:
        return None
    return label.strip().lower()


def _normalize_distribution(distribution: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for label, probability in distribution.items():
        normalized_label = _normalize_label(str(label))
        if not normalized_label:
            continue
        try:
            normalized[normalized_label] = max(float(probability), 0.0)
        except (TypeError, ValueError):
            continue

    total = sum(normalized.values())
    if total > 0:
        normalized = {
            label: probability / total
            for label, probability in normalized.items()
        }
    return normalized


def _distribution_from_result(result: dict[str, Any], label: str | None, confidence: float) -> dict[str, float]:
    raw_distribution = result.get("distribution")
    if isinstance(raw_distribution, dict):
        distribution = _normalize_distribution(raw_distribution)
    else:
        distribution = {}

    alternatives = result.get("alternative_emotions")
    if not distribution and isinstance(alternatives, list):
        distribution = _normalize_distribution(
            {
                item.get("emotion"): item.get("probability")
                for item in alternatives
                if isinstance(item, dict)
            }
        )

    emotion_probs = result.get("emotions")
    if not distribution and isinstance(emotion_probs, dict):
        distribution = _normalize_distribution(emotion_probs)

    if label and confidence > 0 and label not in distribution:
        distribution[label] = confidence
        distribution = _normalize_distribution(distribution)

    return distribution


def _to_emotion_distribution(result: dict[str, Any], source: str) -> EmotionDistribution:
    label = _normalize_label(
        result.get("label") or result.get("primary_emotion") or result.get("emotion")
    )
    confidence = float(result.get("confidence") or 0.0)
    distribution = _distribution_from_result(result, label, confidence)

    if label is None and distribution:
        label, confidence = max(distribution.items(), key=lambda item: item[1])
    elif label is not None and distribution:
        confidence = distribution.get(label, confidence)

    if label is None:
        raise ValueError("Emotion result did not include a usable label")

    return EmotionDistribution(
        label=label,
        confidence=confidence,
        distribution=distribution,
        source=source,
    )


async def predict_text_emotion_async(text: str) -> EmotionDistribution:
    normalized_text = text.strip()
    if not normalized_text:
        return EmotionDistribution(label="neutral", confidence=0.0, distribution={}, source="empty")

    try:
        bert_result = emotion_classifier.predict_emotion(normalized_text)
        emotion = _to_emotion_distribution(bert_result, source="bert")
        if emotion.confidence > 0:
            return emotion
    except Exception:
        pass

    try:
        external_result = await predict_external_emotion(normalized_text)
        return _to_emotion_distribution(external_result, source="external")
    except Exception:
        keyword_result = predict_keyword_emotion(normalized_text)
        return _to_emotion_distribution(keyword_result, source="keyword")


def predict_text_emotion(text: str) -> EmotionDistribution:
    """
    Synchronous wrapper for code paths that run text emotion prediction in a worker thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(predict_text_emotion_async(text))
    raise RuntimeError("predict_text_emotion() must not be called from an active event loop")
