from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from icalendar import Calendar, Event, Todo, vText
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Reminder, Task

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

_PRIORITY = {"high": 1, "medium": 5, "low": 9}


@router.get("/export.ics")
async def export_ical(db: AsyncSession = Depends(get_db)):
    cal = Calendar()
    cal.add("prodid", "-//INFINETT Life Agent//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "INFINETT Life Agent")
    cal.add("x-wr-timezone", "UTC")

    reminders_result = await db.execute(
        select(Reminder).where(Reminder.triggered == False)  # noqa: E712
    )
    for r in reminders_result.scalars().all():
        event = Event()
        event.add("summary", r.title)
        event.add("dtstart", r.remind_at)
        event.add("dtend", r.remind_at + timedelta(hours=1))
        if r.note:
            event.add("description", r.note)
        event["uid"] = vText(f"reminder-{r.id}@infinett")
        cal.add_component(event)

    tasks_result = await db.execute(
        select(Task).where(Task.completed == False)  # noqa: E712
    )
    for t in tasks_result.scalars().all():
        todo = Todo()
        todo.add("summary", t.title)
        if t.due_date:
            todo.add("due", t.due_date)
        if t.description:
            todo.add("description", t.description)
        todo.add("priority", _PRIORITY.get(t.priority, 5))
        todo["uid"] = vText(f"task-{t.id}@infinett")
        cal.add_component(todo)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="infinett.ics"'},
    )
