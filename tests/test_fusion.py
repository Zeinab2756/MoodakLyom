from app.schemas.emotion_schemas import EmotionDistribution
from app.services.fusion import fuse


def test_fuse_agreement_prefers_shared_label():
    acoustic = EmotionDistribution(
        label="happy",
        confidence=0.85,
        distribution={"happy": 0.85, "neutral": 0.15},
        source="acoustic",
    )
    text = EmotionDistribution(
        label="joy",
        confidence=0.9,
        distribution={"joy": 0.9, "surprise": 0.1},
        source="bert",
    )

    fused = fuse(acoustic, text)

    assert fused.label == "happy"
    assert fused.confidence > 0.8
    assert fused.sarcasm_suspected is False


def test_fuse_flags_sarcasm_when_modalities_disagree_with_high_confidence():
    acoustic = EmotionDistribution(
        label="angry",
        confidence=0.92,
        distribution={"angry": 0.92, "neutral": 0.08},
        source="acoustic",
    )
    text = EmotionDistribution(
        label="joy",
        confidence=0.88,
        distribution={"joy": 0.88, "love": 0.12},
        source="bert",
    )

    fused = fuse(acoustic, text)

    assert fused.sarcasm_suspected is True
    assert fused.label in {"happy", "angry"}


def test_fuse_uses_single_modality_when_text_is_missing():
    acoustic = EmotionDistribution(
        label="calm",
        confidence=0.7,
        distribution={"calm": 0.7, "neutral": 0.3},
        source="acoustic",
    )

    fused = fuse(acoustic, None)

    assert fused.label == "neutral"
    assert fused.sarcasm_suspected is False
    assert fused.distribution["neutral"] == 1.0


def test_fuse_returns_neutral_when_no_modalities_are_available():
    fused = fuse(None, None)

    assert fused.label == "neutral"
    assert fused.confidence == 0.0
    assert sum(fused.distribution.values()) == 0.0
