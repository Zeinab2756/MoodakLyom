from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hack import Hack
from app.schemas.hack import WellnessTip
from app.services.wellness_tips import ensure_default_hacks, parse_tags

router = APIRouter()


@router.get("/wellness", response_model=list[WellnessTip])
def get_wellness_tips(db: Session = Depends(get_db)):
    ensure_default_hacks(db)
    hacks = db.query(Hack).order_by(Hack.created_at.desc(), Hack.id.desc()).all()
    return [
        WellnessTip(
            id=hack.id,
            title=hack.title,
            description=hack.content,
            category=hack.category,
            tags=parse_tags(hack.tags),
        )
        for hack in hacks
    ]
