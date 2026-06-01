import asyncio
import os
import smtplib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_executor = ThreadPoolExecutor(max_workers=2)

_EMAIL_FOOTER = '<hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;"><p style="color:#aaa;font-size:11px;">Sent by your INFINETT Life Agent</p>'


def _smtp_send(to: str, subject: str, html: str, text: str):
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)

    if not all([host, user, password]):
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, to, msg.as_string())


async def _send(to: str, subject: str, html: str, text: str):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(_executor, _smtp_send, to, subject, html, text)
    except Exception as exc:
        print(f"[email] Send failed: {exc}")


async def send_reminder_email(title: str, note: str | None, remind_at: datetime):
    to = os.getenv("NOTIFY_EMAIL", "")
    if not to:
        return

    subject = f"⏰ Reminder: {title}"
    text = f"Reminder: {title}\n\n{note or ''}\n\nScheduled for: {remind_at.strftime('%B %d, %Y at %H:%M UTC')}"
    html = f"""
<div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:24px;background:#f9f9f9;border-radius:12px;">
  <h2 style="color:#7c6af7;margin-bottom:6px;">⏰ Reminder</h2>
  <h3 style="margin:0 0 12px;">{title}</h3>
  {f'<p style="color:#444;">{note}</p>' if note else ''}
  <p style="color:#888;font-size:13px;">Scheduled for: {remind_at.strftime('%B %d, %Y at %H:%M UTC')}</p>
  {_EMAIL_FOOTER}
</div>"""

    await _send(to, subject, html, text)


async def send_daily_report_email(report_text: str, stats: dict, date: str):
    to = os.getenv("NOTIFY_EMAIL", "")
    if not to:
        return

    subject = f"📊 Daily Life Report — {date}"

    overdue_block = f'<div style="background:#fff3f3;border-left:4px solid #f87171;padding:10px 14px;border-radius:4px;margin-bottom:12px;"><strong style="color:#f87171;">⚠ {stats["overdue_tasks"]} overdue task{"s" if stats["overdue_tasks"] != 1 else ""}</strong></div>' if stats.get("overdue_tasks") else ""

    html = f"""
<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:28px;">
  <h2 style="color:#7c6af7;margin-bottom:4px;">📊 Daily Life Report</h2>
  <p style="color:#888;margin-bottom:20px;">{date}</p>

  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
    <div style="background:#f5f5f5;border-radius:8px;padding:14px;text-align:center;">
      <div style="font-size:26px;font-weight:700;color:#7c6af7;">{stats.get("pending_tasks", 0)}</div>
      <div style="font-size:11px;color:#888;">Pending</div>
    </div>
    <div style="background:#fff3f3;border-radius:8px;padding:14px;text-align:center;">
      <div style="font-size:26px;font-weight:700;color:#f87171;">{stats.get("overdue_tasks", 0)}</div>
      <div style="font-size:11px;color:#888;">Overdue</div>
    </div>
    <div style="background:#f0fdf4;border-radius:8px;padding:14px;text-align:center;">
      <div style="font-size:26px;font-weight:700;color:#34d399;">{stats.get("completed_tasks", 0)}</div>
      <div style="font-size:11px;color:#888;">Completed</div>
    </div>
    <div style="background:#fffbeb;border-radius:8px;padding:14px;text-align:center;">
      <div style="font-size:26px;font-weight:700;color:#fbbf24;">{stats.get("reminders_today", 0)}</div>
      <div style="font-size:11px;color:#888;">Reminders Today</div>
    </div>
  </div>

  {overdue_block}

  <div style="background:#f8f8fb;border-radius:8px;padding:20px;white-space:pre-wrap;font-size:15px;line-height:1.8;color:#333;">
{report_text}
  </div>
  {_EMAIL_FOOTER}
</div>"""

    await _send(to, subject, html, report_text)
