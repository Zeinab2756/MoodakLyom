"""Utility helpers for mapping emoji selections to emotion names."""

from typing import Dict, List

DISPLAY_EMOJI_OPTIONS: List[tuple[str, str]] = [
    ("😀", "happy"),
    ("😄", "happy"),
    ("☺️", "happy"),
    ("🙂", "content"),
    ("😎", "confident"),
    ("🤭", "playful"),
    ("😢", "sad"),
    ("😣", "frustrated"),
    ("😥", "anxious"),
    ("😕", "confused"),
    ("😐", "neutral"),
    ("😡", "angry"),
    ("😱", "fear"),
    ("😰", "anxious"),
    ("😍", "love"),
    ("🤩", "excited"),
    ("😴", "tired"),
    ("🤒", "unwell"),
    ("😇", "calm"),
    ("🤔", "thoughtful"),
]

EMOJI_EMOTIONS: Dict[str, str] = {emoji: emotion for emoji, emotion in DISPLAY_EMOJI_OPTIONS}


def _normalize_emoji(value: str | None) -> str | None:
    if not value:
        return None

    candidate = value.strip()
    try:
        candidate = candidate.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    return candidate.replace("\ufe0f", "")


def emoji_options() -> List[dict]:
    """Return emoji/emotion pairs for client display."""
    return [{"emoji": emoji, "emotion": emotion} for emoji, emotion in DISPLAY_EMOJI_OPTIONS]


def resolve_emotion_from_emoji(emoji: str | None) -> str | None:
    """Return the emotion mapped to the provided emoji, if available."""
    normalized = _normalize_emoji(emoji)
    if not normalized:
        return None

    direct = EMOJI_EMOTIONS.get(normalized)
    if direct:
        return direct

    for known_emoji, emotion in EMOJI_EMOTIONS.items():
        if known_emoji.replace("\ufe0f", "") == normalized:
            return emotion

    return None
