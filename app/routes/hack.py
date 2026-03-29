"""FastAPI routes for Hacks feature (CRUD + list).

Routes are authenticated by default (consistent with /tasks). If you want the
page to be publicly readable, we can drop auth from the GET endpoints later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.hack import Hack
from app.schemas.hack import (
    HackCreate,
    HackUpdate,
    HackResponse,
    HackListResponse,
    HackSingleResponse,
)


router = APIRouter()


@router.post("/", response_model=HackSingleResponse)
def create_hack(
    hack: HackCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new hack/article.

    Requires auth; converts tags list to a CSV string for storage.
    """

    tags_str = ",".join(hack.tags) if hack.tags else None
    db_hack = Hack(
        title=hack.title,
        content=hack.content,
        category=hack.category,
        tags=tags_str,
    )
    db.add(db_hack)
    db.commit()
    db.refresh(db_hack)

    return HackSingleResponse(data=_to_response(db_hack))


@router.get("/", response_model=HackListResponse)
def get_hacks(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag (contains match)"),
    search: Optional[str] = Query(None, description="Search title/content (contains)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List hacks with optional filtering and pagination.

    - category: exact match on category
    - tag: substring match on the CSV tags field
    - search: substring match on title or content
    """

    query = db.query(Hack)

    if category:
        query = query.filter(Hack.category == category)
    if tag:
        # Simple contains-based tag filter on comma-separated tags
        like = f"%{tag}%"
        query = query.filter(Hack.tags.like(like))
    if search:
        like = f"%{search}%"
        query = query.filter((Hack.title.like(like)) | (Hack.content.like(like)))

    total = query.count()
    hacks = query.order_by(Hack.created_at.desc()).offset(offset).limit(limit).all()

    return HackListResponse(
        data=[_to_response(h) for h in hacks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{hack_id}", response_model=HackSingleResponse)
def get_hack(
    hack_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single hack by id."""

    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")
    return HackSingleResponse(data=_to_response(hack))


@router.put("/{hack_id}", response_model=HackSingleResponse)
def update_hack(
    hack_id: int,
    hack_update: HackUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update fields of an existing hack (full/partial)."""

    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")

    # Only update provided fields; convert tags list to CSV if present
    update = hack_update.model_dump(exclude_unset=True)
    if "tags" in update:
        update["tags"] = ",".join(update["tags"]) if update["tags"] else None
    for k, v in update.items():
        setattr(hack, k, v)

    db.add(hack)
    db.commit()
    db.refresh(hack)
    return HackSingleResponse(data=_to_response(hack))


@router.delete("/{hack_id}")
def delete_hack(
    hack_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a hack by id."""

    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")
    db.delete(hack)
    db.commit()
    return {"success": True, "message": "Hack deleted successfully"}


def _to_response(h: Hack) -> HackResponse:
    """Convert a Hack ORM object to a HackResponse with list tags."""

    tags_list: Optional[List[str]] = None
    if h.tags:
        tags_list = [t.strip() for t in h.tags.split(",") if t.strip()]
    return HackResponse(
        id=h.id,
        title=h.title,
        content=h.content,
        category=h.category,
        tags=tags_list,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )
