from collections import Counter
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.mood import Mood
from app.models.user import User
from app.schemas.mood import EmojiEmotionList, MoodCreate, MoodListResponse, MoodResponse, MoodSummary
from app.services.emoji_mapping import EMOJI_EMOTIONS, emoji_options, resolve_emotion_from_emoji

router = APIRouter()


def _mood_to_response(mood: Mood) -> MoodResponse:
    tags_list = None
    if mood.tags:
        tags_list = [tag.strip() for tag in mood.tags.split(",") if tag.strip()]

    return MoodResponse(
        id=mood.id,
        user_id=mood.user_id,
        date=mood.date,
        mood_level=mood.mood_level,
        emoji=mood.emoji,
        emotion=mood.emotion,
        tags=tags_list,
        notes=mood.notes,
    )


def _resolve_date_range(range_name: str | None) -> tuple[date | None, date | None]:
    if not range_name:
        return None, None

    today = date.today()
    normalized = range_name.strip().lower()
    if normalized == "week":
        return today - timedelta(days=6), today
    if normalized == "month":
        return today - timedelta(days=29), today
    if normalized == "year":
        return today - timedelta(days=364), today
    return None, None


@router.post("/add", response_model=MoodResponse, status_code=status.HTTP_201_CREATED)
async def add_mood(
    mood_data: MoodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_mood = db.query(Mood).filter(
        and_(Mood.user_id == current_user.id, Mood.date == mood_data.date)
    ).first()
    if existing_mood:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Mood entry already exists for this date"},
        )

    tags_string = None
    if mood_data.tags:
        tags_string = ",".join(mood_data.tags)

    emoji_emotion = resolve_emotion_from_emoji(mood_data.emoji)
    if mood_data.emotion:
        if emoji_emotion and mood_data.emotion != emoji_emotion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Emoji does not match the provided emotion"},
            )
        if mood_data.emotion not in EMOJI_EMOTIONS.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Unsupported emotion selection"},
            )

    new_mood = Mood(
        user_id=current_user.id,
        date=mood_data.date,
        mood_level=mood_data.moodLevel,
        emoji=mood_data.emoji,
        emotion=mood_data.emotion or emoji_emotion,
        tags=tags_string,
        notes=mood_data.notes,
    )
    db.add(new_mood)
    db.commit()
    db.refresh(new_mood)
    return _mood_to_response(new_mood)


@router.get("/all", response_model=MoodListResponse)
async def get_all_moods(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Mood).filter(Mood.user_id == current_user.id)
    if from_date:
        query = query.filter(Mood.date >= from_date)
    if to_date:
        query = query.filter(Mood.date <= to_date)

    total = query.count()
    moods = query.order_by(Mood.date.asc()).offset(offset).limit(limit).all()
    return MoodListResponse(
        moods=[_mood_to_response(mood) for mood in moods],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=MoodSummary)
async def get_mood_summary(
    range_name: Optional[str] = Query(None, alias="range"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_from, resolved_to = _resolve_date_range(range_name)
    start_date = from_date or resolved_from
    end_date = to_date or resolved_to

    query = db.query(Mood).filter(Mood.user_id == current_user.id)
    if start_date:
        query = query.filter(Mood.date >= start_date)
    if end_date:
        query = query.filter(Mood.date <= end_date)

    moods = query.order_by(Mood.date.asc()).all()
    if not moods:
        return MoodSummary(total=0, average=0.0, by_day=[], top_tags=[], trend="stable")

    total = len(moods)
    average = round(sum(mood.mood_level for mood in moods) / total, 2)
    tag_counter = Counter()
    for mood in moods:
        if mood.tags:
            tag_counter.update(tag.strip() for tag in mood.tags.split(",") if tag.strip())

    midpoint = max(total // 2, 1)
    first_half = moods[:midpoint]
    second_half = moods[midpoint:] or moods[-1:]
    first_avg = sum(item.mood_level for item in first_half) / len(first_half)
    second_avg = sum(item.mood_level for item in second_half) / len(second_half)
    if second_avg - first_avg >= 0.3:
        trend = "improving"
    elif first_avg - second_avg >= 0.3:
        trend = "declining"
    else:
        trend = "stable"

    return MoodSummary(
        total=total,
        average=average,
        by_day=[{"date": mood.date.isoformat(), "mood": mood.mood_level} for mood in moods],
        top_tags=[tag for tag, _count in tag_counter.most_common(5)],
        trend=trend,
    )


@router.get("/emoji-options", response_model=EmojiEmotionList)
async def list_emoji_options():
    return EmojiEmotionList(options=emoji_options())


@router.get("/{mood_date}", response_model=MoodResponse)
async def get_mood_by_date(
    mood_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mood = db.query(Mood).filter(
        and_(Mood.user_id == current_user.id, Mood.date == mood_date)
    ).first()
    if not mood:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No mood entry found for this date"},
        )
    return _mood_to_response(mood)
