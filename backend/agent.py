import os
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are a personal AI life management assistant. You help the user with:
- Managing tasks and goals (creating, tracking, prioritizing)
- Setting and tracking reminders
- Researching topics and summarizing information
- Generating daily briefings and reports
- Providing advice on productivity and life organization

Be concise, actionable, and friendly. Today's date is {date}.
When the user asks you to add tasks, reminders, or do research — respond with the action AND a JSON block at the end of your message.

For adding a task, end your response with:
```json
{{"action": "add_task", "title": "...", "priority": "high|medium|low", "category": "...", "description": "..."}}
```

For adding a reminder, end your response with:
```json
{{"action": "add_reminder", "title": "...", "note": "...", "remind_at": "YYYY-MM-DDTHH:MM:SS"}}
```

For research requests, end your response with:
```json
{{"action": "research", "query": "..."}}
```

Otherwise just respond naturally."""


def build_context(tasks: list, reminders: list) -> str:
    ctx = []
    pending = [t for t in tasks if not t.completed]
    if pending:
        ctx.append(f"Current tasks ({len(pending)} pending):")
        for t in pending[:10]:
            due = f", due {t.due_date.strftime('%Y-%m-%d')}" if t.due_date else ""
            ctx.append(f"  - [{t.priority.upper()}] {t.title}{due}")
    upcoming = [r for r in reminders if not r.triggered and r.remind_at > datetime.utcnow()]
    if upcoming:
        ctx.append(f"\nUpcoming reminders ({len(upcoming)}):")
        for r in upcoming[:5]:
            ctx.append(f"  - {r.title} at {r.remind_at.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(ctx)


async def chat_with_agent(messages: list[dict], tasks: list, reminders: list) -> str:
    context = build_context(tasks, reminders)
    system = SYSTEM_PROMPT.format(date=datetime.utcnow().strftime("%Y-%m-%d"))
    if context:
        system += f"\n\nUser's current data:\n{context}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def research_topic(query: str) -> str:
    prompt = f"""Research the following topic thoroughly and provide a well-structured summary:

Topic: {query}

Provide:
1. A brief overview (2-3 sentences)
2. Key facts and findings (bullet points)
3. Actionable takeaways or recommendations
4. Any important caveats or things to watch out for

Keep the total response under 500 words. Be factual and helpful."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def generate_daily_report(tasks: list, reminders: list, date: str) -> str:
    pending = [t for t in tasks if not t.completed]
    completed_today = [
        t for t in tasks
        if t.completed and t.completed_at and t.completed_at.strftime("%Y-%m-%d") == date
    ]
    overdue = [
        t for t in pending
        if t.due_date and t.due_date.strftime("%Y-%m-%d") < date
    ]
    due_today = [
        t for t in pending
        if t.due_date and t.due_date.strftime("%Y-%m-%d") == date
    ]
    upcoming_reminders = [
        r for r in reminders
        if not r.triggered and r.remind_at.strftime("%Y-%m-%d") == date
    ]

    context = f"""Date: {date}

Pending tasks: {len(pending)}
Overdue tasks: {len(overdue)}
Due today: {len(due_today)}
Completed today: {len(completed_today)}
Reminders today: {len(upcoming_reminders)}

Tasks overdue:
{chr(10).join(f"- [{t.priority}] {t.title} (due {t.due_date.strftime('%Y-%m-%d')})" for t in overdue[:5]) if overdue else "None"}

Tasks due today:
{chr(10).join(f"- [{t.priority}] {t.title}" for t in due_today) if due_today else "None"}

Top pending tasks by priority:
{chr(10).join(f"- [{t.priority}] {t.title}" for t in sorted(pending, key=lambda x: {"high":0,"medium":1,"low":2}.get(x.priority, 1))[:5]) if pending else "None"}

Today's reminders:
{chr(10).join(f"- {r.title} at {r.remind_at.strftime('%H:%M')}" for r in upcoming_reminders) if upcoming_reminders else "None"}"""

    prompt = f"""Generate a concise, motivating daily briefing for the user based on this data:

{context}

Format it as a friendly morning briefing with:
- A brief greeting and summary of the day ahead
- Priority focus areas (what to tackle first)
- Any urgent items needing immediate attention
- A short motivational closing note

Keep it under 300 words, warm and actionable."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
