import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from backend.database import SessionLocal
from backend.email_sender import send_daily_report_email, send_reminder_email
from backend.models import Notification, Reminder, Task

scheduler = AsyncIOScheduler()


async def _check_reminders():
    async with SessionLocal() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(Reminder).where(
                Reminder.triggered == False,  # noqa: E712
                Reminder.remind_at <= now,
            )
        )
        reminders = result.scalars().all()
        for reminder in reminders:
            db.add(Notification(
                title=f"Reminder: {reminder.title}",
                body=reminder.note,
                type="reminder",
                reference_id=reminder.id,
            ))
            if reminder.repeat == "daily":
                reminder.remind_at += timedelta(days=1)
            elif reminder.repeat == "weekly":
                reminder.remind_at += timedelta(weeks=1)
            else:
                reminder.triggered = True

            await send_reminder_email(reminder.title, reminder.note, reminder.remind_at)

        if reminders:
            await db.commit()


async def _send_daily_report():
    from backend.agent import generate_daily_report

    async with SessionLocal() as db:
        tasks = (await db.execute(select(Task))).scalars().all()
        reminders = (await db.execute(select(Reminder))).scalars().all()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    report_text = await generate_daily_report(tasks, reminders, today)

    overdue = sum(1 for t in tasks if not t.completed and t.due_date and t.due_date.strftime("%Y-%m-%d") < today)
    stats = {
        "pending_tasks": sum(1 for t in tasks if not t.completed),
        "overdue_tasks": overdue,
        "completed_tasks": sum(1 for t in tasks if t.completed),
        "reminders_today": sum(1 for r in reminders if not r.triggered and r.remind_at.strftime("%Y-%m-%d") == today),
    }

    await send_daily_report_email(report_text, stats, today)
    print(f"[scheduler] Daily report email sent for {today}")


def start_scheduler():
    scheduler.add_job(_check_reminders, "interval", minutes=1, id="check_reminders")

    report_hour = int(os.getenv("DAILY_REPORT_HOUR", "6"))
    scheduler.add_job(_send_daily_report, "cron", hour=report_hour, minute=0, id="daily_report")

    scheduler.start()
    print(f"[scheduler] Started — daily report at {report_hour:02d}:00 UTC")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
