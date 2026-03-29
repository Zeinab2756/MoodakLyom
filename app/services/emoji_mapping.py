"""Utility helpers for mapping emoji selections to emotion names."""

from typing import Dict, List

EMOJI_EMOTIONS: Dict[str, str] = {
    "😀": "happy",
    "😢": "sad",
    "😡": "angry",
    "😱": "fear",
    "😐": "neutral",
    "😰": "anxious",
    "😍": "love",
    "🤩": "excited",
    "😴": "tired",
    "🤒": "unwell",
    "😇": "calm",
    "🤔": "thoughtful",
}


def emoji_options() -> List[dict]:
    """Return emoji/emotion pairs for client display."""
    return [{"emoji": emoji, "emotion": emotion} for emoji, emotion in EMOJI_EMOTIONS.items()]


def resolve_emotion_from_emoji(emoji: str | None) -> str | None:
    """Return the emotion mapped to the provided emoji, if available."""
    if not emoji:
        return None
    return EMOJI_EMOTIONS.get(emoji)