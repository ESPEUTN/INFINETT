from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Task, Reminder
from backend.agent import generate_daily_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily")
async def daily_report(db: AsyncSession = Depends(get_db)):
    tasks_result = await db.execute(select(Task))
    tasks = tasks_result.scalars().all()

    reminders_result = await db.execute(select(Reminder))
    reminders = reminders_result.scalars().all()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    report = await generate_daily_report(tasks, reminders, today)

    return {
        "date": today,
        "report": report,
        "stats": {
            "total_tasks": len(tasks),
            "pending_tasks": sum(1 for t in tasks if not t.completed),
            "completed_tasks": sum(1 for t in tasks if t.completed),
            "overdue_tasks": sum(
                1 for t in tasks
                if not t.completed and t.due_date and t.due_date.strftime("%Y-%m-%d") < today
            ),
            "reminders_today": sum(
                1 for r in reminders
                if not r.triggered and r.remind_at.strftime("%Y-%m-%d") == today
            ),
        },
    }
