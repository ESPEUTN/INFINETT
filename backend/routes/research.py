from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import ResearchEntry
from backend.agent import research_topic

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str


def entry_to_dict(e: ResearchEntry) -> dict:
    return {
        "id": e.id,
        "query": e.query,
        "summary": e.summary,
        "created_at": e.created_at.isoformat(),
    }


@router.get("")
async def list_research(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchEntry).order_by(ResearchEntry.created_at.desc()))
    return [entry_to_dict(e) for e in result.scalars().all()]


@router.post("")
async def do_research(body: ResearchRequest, db: AsyncSession = Depends(get_db)):
    summary = await research_topic(body.query)
    entry = ResearchEntry(query=body.query, summary=summary)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry_to_dict(entry)


@router.delete("/{entry_id}")
async def delete_research(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(ResearchEntry, entry_id)
    if entry:
        await db.delete(entry)
        await db.commit()
    return {"ok": True}
