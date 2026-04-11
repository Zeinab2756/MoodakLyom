from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.hack import Hack
from app.models.user import User
from app.schemas.hack import HackCreate, HackListResponse, HackResponse, HackSingleResponse, HackUpdate
from app.services.wellness_tips import ensure_default_hacks, parse_tags

router = APIRouter()


def _to_tag_string(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    return ",".join(cleaned) if cleaned else None


def _to_hack_response(hack: Hack) -> HackResponse:
    return HackResponse(
        id=hack.id,
        title=hack.title,
        content=hack.content,
        category=hack.category,
        tags=parse_tags(hack.tags),
        created_at=hack.created_at,
        updated_at=hack.updated_at,
    )


@router.get("/", response_model=HackListResponse)
def list_hacks(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _current_user: User = Depends(get_current_user),
):
    ensure_default_hacks(db)
    query = db.query(Hack).order_by(Hack.created_at.desc(), Hack.id.desc())
    total = query.count()
    hacks = query.offset(offset).limit(limit).all()
    return HackListResponse(
        data=[_to_hack_response(hack) for hack in hacks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=HackSingleResponse)
def create_hack(
    payload: HackCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    hack = Hack(
        title=payload.title.strip(),
        content=payload.content.strip(),
        category=payload.category.strip() if payload.category else None,
        tags=_to_tag_string(payload.tags),
    )
    db.add(hack)
    db.commit()
    db.refresh(hack)
    return HackSingleResponse(data=_to_hack_response(hack))


@router.get("/{hack_id}", response_model=HackSingleResponse)
def get_hack(
    hack_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    ensure_default_hacks(db)
    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")
    return HackSingleResponse(data=_to_hack_response(hack))


@router.put("/{hack_id}", response_model=HackSingleResponse)
def update_hack(
    hack_id: int,
    payload: HackUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] is not None:
        hack.title = update_data["title"].strip()
    if "content" in update_data and update_data["content"] is not None:
        hack.content = update_data["content"].strip()
    if "category" in update_data:
        hack.category = update_data["category"].strip() if update_data["category"] else None
    if "tags" in update_data:
        hack.tags = _to_tag_string(update_data["tags"])

    db.commit()
    db.refresh(hack)
    return HackSingleResponse(data=_to_hack_response(hack))


@router.delete("/{hack_id}")
def delete_hack(
    hack_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    hack = db.query(Hack).filter(Hack.id == hack_id).first()
    if not hack:
        raise HTTPException(status_code=404, detail="Hack not found")

    db.delete(hack)
    db.commit()
    return {"success": True, "data": {"message": "Hack deleted successfully"}}
