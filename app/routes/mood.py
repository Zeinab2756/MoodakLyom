from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, List
from datetime import date, datetime, timedelta
from collections import Counter

from app.database import get_db
from app.dependencies import get_current_user
from app.models.mood import Mood
from app.models.user import User
from app.schemas.mood import MoodCreate, MoodResponse, MoodSummary, MoodListResponse, EmojiEmotionList
from app.services.emoji_mapping import EMOJI_EMOTIONS, emoji_options, resolve_emotion_from_emoji

router = APIRouter()

@router.post("/add", response_model=MoodResponse, status_code=status.HTTP_201_CREATED)
async def add_mood(
    mood_data: MoodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new mood entry for the authenticated user.
    
    - **date**: Date for the mood entry (YYYY-MM-DD format)
    - **moodLevel**: Mood level from 1-5 (1=very bad, 5=excellent)
    - **tags**: Optional list of tags (max 10, each max 20 chars)
    - **notes**: Optional notes (max 1000 chars)
    
    Returns 201 if created successfully, 400 if entry already exists for that date.
    """
    # Check if entry already exists for this user and date
    existing_mood = db.query(Mood).filter(
        and_(Mood.user_id == current_user.id, Mood.date == mood_data.date)
    ).first()
    
    if existing_mood:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Mood entry already exists for this date"}
        )
    
    # Convert tags list to comma-separated string
    tags_string = None
    if mood_data.tags:
        tags_string = ",".join(mood_data.tags)
    
    # Determine the stored emotion based on emoji selection
    emoji_emotion = resolve_emotion_from_emoji(mood_data.emoji)

    if mood_data.emotion:
        # Ensure provided emotion aligns with emoji mapping when both are supplied
        if emoji_emotion and mood_data.emotion != emoji_emotion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Emoji does not match the provided emotion"}
            )
        # Ensure the emotion is supported by at least one emoji
        if mood_data.emotion not in EMOJI_EMOTIONS.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Unsupported emotion selection"}
            )

    # Accept any emoji — fallback if not recognized
    if mood_data.emoji and not emoji_emotion:
        emoji_emotion = "neutral"

    stored_emotion = mood_data.emotion or emoji_emotion or "neutral"

    # Create new mood entry
    new_mood = Mood(
        user_id=current_user.id,
        date=mood_data.date,
        mood_level=mood_data.moodLevel,
        emoji=mood_data.emoji,
        emotion=stored_emotion,
        tags=tags_string,
        notes=mood_data.notes
    )
    
    db.add(new_mood)
    db.commit()
    db.refresh(new_mood)
    
    # Convert tags back to list for response
    tags_list = None
    if new_mood.tags:
        tags_list = [tag.strip() for tag in new_mood.tags.split(',') if tag.strip()]
    
    return MoodResponse(
        id=new_mood.id,
        user_id=new_mood.user_id,
        date=new_mood.date,
        mood_level=new_mood.mood_level,
        emoji=new_mood.emoji,
        emotion=new_mood.emotion,
        tags=tags_list,
        notes=new_mood.notes
    )

@router.get("/all", response_model=MoodListResponse)
async def get_all_moods(
    from_date: Optional[date] = Query(None, alias="from", description="Start date filter"),
    to_date: Optional[date] = Query(None, alias="to", description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all mood entries for the authenticated user.
    
    - **from**: Optional start date filter (YYYY-MM-DD)
    - **to**: Optional end date filter (YYYY-MM-DD)
    - **limit**: Number of entries to return (1-1000, default 100)
    - **offset**: Number of entries to skip for pagination (default 0)
    
    Returns paginated list of mood entries ordered by date ascending.
    """
    query = db.query(Mood).filter(Mood.user_id == current_user.id)
    
    # Apply date filters
    if from_date:
        query = query.filter(Mood.date >= from_date)
    if to_date:
        query = query.filter(Mood.date <= to_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    moods = query.order_by(Mood.date.asc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    mood_responses = []
    for mood in moods:
        tags_list = None
        if mood.tags:
            tags_list = [tag.strip() for tag in mood.tags.split(',') if tag.strip()]
        
        mood_responses.append(MoodResponse(
            id=mood.id,
            user_id=mood.user_id,
            date=mood.date,
            mood_level=mood.mood_level,
            emoji=mood.emoji,
            emotion=mood.emotion,
            tags=tags_list,
            notes=mood.notes
        ))
    
    return MoodListResponse(
        moods=mood_responses,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/summary", response_model=MoodSummary)
async def get_mood_summary(
    range_type: Optional[str] = Query(None, alias="range", description="Time range: 'week' or 'month'"),
    from_date: Optional[date] = Query(None, alias="from", description="Custom start date"),
    to_date: Optional[date] = Query(None, alias="to", description="Custom end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get mood statistics and summary for the authenticated user.
    
    - **range**: Time range - 'week' (last 7 days) or 'month' (last 30 days)
    - **from**: Custom start date (overrides range if provided)
    - **to**: Custom end date (overrides range if provided)
@@ -236,28 +268,36 @@ async def get_mood_by_date(
    
    - **mood_date**: Date to retrieve mood for (YYYY-MM-DD format)
    
    Returns 404 if no entry exists for that date.
    """
    # Check last mood time (6-hour rule)
    last_mood = db.query(Mood).filter(
    Mood.user_id == current_user.id
    ).order_by(Mood.id.desc()).first()

    if last_mood:
        now = datetime.utcnow()

    last_time = getattr(last_mood, "created_at", None)

    if last_time is None:
        last_time = datetime.combine(last_mood.date, datetime.min.time())

    if now - last_time < timedelta(hours=6):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "You can only add a mood every 6 hours"}
        )
    
    if not mood:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No mood entry found for this date"}
        )
    
    # Convert tags back to list for response
    tags_list = None
    if mood.tags:
        tags_list = [tag.strip() for tag in mood.tags.split(',') if tag.strip()]
    
    return MoodResponse(
        id=mood.id,
        user_id=mood.user_id,
        date=mood.date,
        mood_level=mood.mood_level,
        emoji=mood.emoji,
        emotion=mood.emotion,
        tags=tags_list,
        notes=mood.notes
    )


@router.get("/emoji-options", response_model=EmojiEmotionList)
async def list_emoji_options():
    """List available emoji/emotion pairs for mood selection."""
    return EmojiEmotionList(options=emoji_options())