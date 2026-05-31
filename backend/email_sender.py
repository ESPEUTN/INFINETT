import asyncio
import os
import smtplib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_executor = ThreadPoolExecutor(max_workers=2)


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
  <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">
  <p style="color:#aaa;font-size:11px;">Sent by your INFINETT Life Agent</p>
</div>"""

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(_executor, _smtp_send, to, subject, html, text)
    except Exception as exc:
        print(f"[email] Send failed: {exc}")
