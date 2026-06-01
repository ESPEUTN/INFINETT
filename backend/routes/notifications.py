from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "type": n.type,
        "read": n.read,
        "reference_id": n.reference_id,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).order_by(Notification.created_at.desc()).limit(50)
    )
    return [_to_dict(n) for n in result.scalars().all()]


@router.patch("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.read == False))  # noqa: E712
    for n in result.scalars().all():
        n.read = True
    await db.commit()
    return {"ok": True}


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: int, db: AsyncSession = Depends(get_db)):
    notif = await db.get(Notification, notif_id)
    if notif:
        notif.read = True
        await db.commit()
    return {"ok": True}


@router.delete("")
async def clear_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification))
    for n in result.scalars().all():
        await db.delete(n)
    await db.commit()
    return {"ok": True}
