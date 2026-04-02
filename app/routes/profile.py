from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.mood import Mood      # ✅ import these models
from app.models.task import Task
from app.dependencies import get_current_user  # ✅ JWT auth dependency

router = APIRouter(prefix="/profile", tags=["Profile"])

# ✅ GET /profile/get
@router.get("/get")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return the user's profile settings."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user.username,
        "avatar": user.avatar,
        "preferences": user.preferences,
        "profile": {
            "theme": user.preferences.get("theme", "light"),
            "notification_style": user.preferences.get("notification_style", "default"),
            "reminder_frequency": user.preferences.get("reminder_frequency", "daily"),
            "privacy_toggle": user.preferences.get("privacy_toggle", "public"),
        }
    }

# ✅ PUT /profile/update
@router.put("/update")
def update_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    avatar: str = None,
    preferences: dict = None,
    theme: str = None,
    notification_style: str = None,
    reminder_frequency: str = None,
    privacy_toggle: str = None
):
    """
    Update profile settings.
    Allows editing avatar and preferences in addition to other options.
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update avatar if provided
    if avatar:
        user.avatar = avatar

    # Update preferences dictionary
    updated_preferences = user.preferences or {}
    if preferences:
        updated_preferences.update(preferences)
    if theme:
        updated_preferences["theme"] = theme
    if notification_style:
        updated_preferences["notification_style"] = notification_style
    if reminder_frequency:
        updated_preferences["reminder_frequency"] = reminder_frequency
    if privacy_toggle:
        updated_preferences["privacy_toggle"] = privacy_toggle

    user.preferences = updated_preferences
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "avatar": user.avatar,
            "preferences": user.preferences
        }
    }

# ✅ GET /profile/export (Improved)
@router.get("/export")
def export_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all user-related data (user info, profile, moods, and tasks)."""
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
            "created_at": user.created_at,
        },
        "profile": user.preferences,
        "moods": [
            {
                "date": m.date,
                "mood_level": m.mood_level,
                "tags": m.tags,
                "notes": m.notes
            }
            for m in moods
        ],
        "tasks": [
            {
                "title": t.title,
                "status": t.status,
                "deadline": t.deadline,
                "priority": t.priority
            }
            for t in tasks
        ]
    }
