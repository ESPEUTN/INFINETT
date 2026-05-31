from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from backend.database import SessionLocal
from backend.email_sender import send_reminder_email
from backend.models import Notification, Reminder

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
            notif = Notification(
                title=f"Reminder: {reminder.title}",
                body=reminder.note,
                type="reminder",
                reference_id=reminder.id,
            )
            db.add(notif)

            if reminder.repeat == "daily":
                reminder.remind_at = reminder.remind_at + timedelta(days=1)
            elif reminder.repeat == "weekly":
                reminder.remind_at = reminder.remind_at + timedelta(weeks=1)
            else:
                reminder.triggered = True

            await send_reminder_email(reminder.title, reminder.note, reminder.remind_at)

        if reminders:
            await db.commit()


def start_scheduler():
    scheduler.add_job(_check_reminders, "interval", minutes=1, id="check_reminders")
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
