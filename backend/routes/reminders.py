from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Reminder

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
    title: str
    note: str | None = None
    remind_at: str
    repeat: str | None = None


class ReminderUpdate(BaseModel):
    title: str | None = None
    note: str | None = None
    remind_at: str | None = None
    repeat: str | None = None
    triggered: bool | None = None


def reminder_to_dict(r: Reminder) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "note": r.note,
        "remind_at": r.remind_at.isoformat(),
        "repeat": r.repeat,
        "triggered": r.triggered,
        "created_at": r.created_at.isoformat(),
    }


@router.get("")
async def list_reminders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).order_by(Reminder.remind_at))
    reminders = result.scalars().all()
    return [reminder_to_dict(r) for r in reminders]


@router.post("")
async def create_reminder(body: ReminderCreate, db: AsyncSession = Depends(get_db)):
    try:
        remind_at = datetime.fromisoformat(body.remind_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid remind_at format (use ISO format)")

    reminder = Reminder(
        title=body.title,
        note=body.note,
        remind_at=remind_at,
        repeat=body.repeat,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder_to_dict(reminder)


@router.patch("/{reminder_id}")
async def update_reminder(reminder_id: int, body: ReminderUpdate, db: AsyncSession = Depends(get_db)):
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if body.title is not None:
        reminder.title = body.title
    if body.note is not None:
        reminder.note = body.note
    if body.remind_at is not None:
        reminder.remind_at = datetime.fromisoformat(body.remind_at)
    if body.repeat is not None:
        reminder.repeat = body.repeat
    if body.triggered is not None:
        reminder.triggered = body.triggered

    await db.commit()
    await db.refresh(reminder)
    return reminder_to_dict(reminder)


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: int, db: AsyncSession = Depends(get_db)):
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)
    await db.commit()
    return {"ok": True}
