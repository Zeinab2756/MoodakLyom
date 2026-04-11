from sqlalchemy.orm import Session

from app.models.hack import Hack

DEFAULT_WELLNESS_TIPS = [
    {
        "title": "Take a 5-minute walk",
        "content": "A short walk can reset your focus, lower stress, and improve your mood.",
        "category": "wellness",
        "tags": ["movement", "stress"],
    },
    {
        "title": "Write one small next step",
        "content": "When tasks feel heavy, define the smallest next action and do only that.",
        "category": "productivity",
        "tags": ["focus", "planning"],
    },
    {
        "title": "Hydrate before you push through",
        "content": "Energy dips often get worse when you are dehydrated. Drink water first.",
        "category": "wellness",
        "tags": ["energy", "habit"],
    },
    {
        "title": "Use a 25-minute focus block",
        "content": "Set a timer, remove distractions, and work on one task until the timer ends.",
        "category": "productivity",
        "tags": ["focus", "time"],
    },
    {
        "title": "Name what you are feeling",
        "content": "Labeling an emotion can make it easier to respond instead of react.",
        "category": "mindfulness",
        "tags": ["emotion", "reflection"],
    },
]


def _tags_to_string(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    return ",".join(cleaned) if cleaned else None


def parse_tags(tags: str | None) -> list[str] | None:
    if not tags:
        return None
    parsed = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return parsed or None


def ensure_default_hacks(db: Session) -> None:
    if db.query(Hack).count() > 0:
        return

    for item in DEFAULT_WELLNESS_TIPS:
        db.add(
            Hack(
                title=item["title"],
                content=item["content"],
                category=item["category"],
                tags=_tags_to_string(item["tags"]),
            )
        )
    db.commit()
