import asyncio

from app.services import text_emotion


def test_predict_text_emotion_uses_bert_first(monkeypatch):
    monkeypatch.setattr(
        text_emotion.emotion_classifier,
        "predict_emotion",
        lambda text: {
            "primary_emotion": "joy",
            "confidence": 0.9,
            "distribution": {"joy": 0.9, "surprise": 0.1},
        },
    )

    result = asyncio.run(text_emotion.predict_text_emotion_async("great day"))

    assert result.label == "joy"
    assert result.source == "bert"


def test_predict_text_emotion_falls_through_to_external_api(monkeypatch):
    def raise_from_bert(_text):
        raise RuntimeError("bert unavailable")

    async def external_result(_text):
        return {
            "emotion": "sad",
            "confidence": 0.75,
            "distribution": {"sad": 0.75, "neutral": 0.25},
        }

    monkeypatch.setattr(text_emotion.emotion_classifier, "predict_emotion", raise_from_bert)
    monkeypatch.setattr(text_emotion, "predict_external_emotion", external_result)

    result = asyncio.run(text_emotion.predict_text_emotion_async("not great"))

    assert result.label == "sad"
    assert result.source == "external"


def test_predict_text_emotion_uses_keyword_fallback_after_external_failure(monkeypatch):
    def raise_from_bert(_text):
        raise RuntimeError("bert unavailable")

    async def raise_from_external(_text):
        raise RuntimeError("external unavailable")

    monkeypatch.setattr(text_emotion.emotion_classifier, "predict_emotion", raise_from_bert)
    monkeypatch.setattr(text_emotion, "predict_external_emotion", raise_from_external)
    monkeypatch.setattr(
        text_emotion,
        "predict_keyword_emotion",
        lambda text: {
            "emotion": "anxious",
            "confidence": 0.6,
            "distribution": {"anxious": 0.6, "neutral": 0.4},
        },
    )

    result = asyncio.run(text_emotion.predict_text_emotion_async("I am worried"))

    assert result.label == "anxious"
    assert result.source == "keyword"


def test_predict_text_emotion_returns_empty_result_for_blank_text():
    result = asyncio.run(text_emotion.predict_text_emotion_async("   "))

    assert result.label == "neutral"
    assert result.confidence == 0.0
    assert result.distribution == {}


def test_to_emotion_distribution_normalizes_alternative_shapes():
    result = text_emotion._to_emotion_distribution(
        {
            "alternative_emotions": [
                {"emotion": "Joy", "probability": 2},
                {"emotion": "Surprise", "probability": 1},
            ]
        },
        source="external",
    )

    assert result.label == "joy"
    assert result.distribution["joy"] == 2 / 3


def test_predict_text_emotion_sync_wrapper_runs_without_event_loop(monkeypatch):
    monkeypatch.setattr(
        text_emotion.emotion_classifier,
        "predict_emotion",
        lambda text: {
            "primary_emotion": "joy",
            "confidence": 0.8,
            "distribution": {"joy": 0.8, "surprise": 0.2},
        },
    )

    result = text_emotion.predict_text_emotion("works")

    assert result.label == "joy"
    assert result.source == "bert"
