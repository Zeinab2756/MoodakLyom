from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.mood import Mood
from app.models.task import Task
from app.models.user import User

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    avatar: str | None = None
    preferences: dict[str, Any] | None = None
    theme: str | None = None
    notification_style: str | None = None
    reminder_frequency: str | None = None
    privacy_toggle: str | None = None


@router.get("/get")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    preferences = user.preferences or {}
    return {
        "username": user.username,
        "avatar": user.avatar,
        "preferences": preferences,
        "profile": {
            "theme": preferences.get("theme", "light"),
            "notification_style": preferences.get("notification_style", "default"),
            "reminder_frequency": preferences.get("reminder_frequency", "daily"),
            "privacy_toggle": preferences.get("privacy_toggle", "public"),
        },
    }


@router.put("/update")
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.avatar is not None:
        user.avatar = payload.avatar

    updated_preferences = user.preferences or {}
    if payload.preferences:
        updated_preferences.update(payload.preferences)
    if payload.theme is not None:
        updated_preferences["theme"] = payload.theme
    if payload.notification_style is not None:
        updated_preferences["notification_style"] = payload.notification_style
    if payload.reminder_frequency is not None:
        updated_preferences["reminder_frequency"] = payload.reminder_frequency
    if payload.privacy_toggle is not None:
        updated_preferences["privacy_toggle"] = payload.privacy_toggle

    user.preferences = updated_preferences
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "avatar": user.avatar,
            "preferences": user.preferences,
        },
    }


@router.get("/export")
def export_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    moods = db.query(Mood).filter(Mood.user_id == user.id).all()
    tasks = db.query(Task).filter(Task.user_id == user.id).all()
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": user.preferences or {},
        "moods": [
            {
                "date": mood.date.isoformat(),
                "mood_level": mood.mood_level,
                "emoji": mood.emoji,
                "emotion": mood.emotion,
                "tags": mood.tags,
                "notes": mood.notes,
            }
            for mood in moods
        ],
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "is_completed": task.is_completed,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "priority": task.priority.value,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            for task in tasks
        ],
    }
