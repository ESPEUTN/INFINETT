import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Task, Reminder, ChatMessage, ResearchEntry
from backend.agent import chat_with_agent, research_topic

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_HISTORY = 20


class ChatRequest(BaseModel):
    message: str


async def _apply_action(action_data: dict, db: AsyncSession):
    action = action_data.get("action")
    if action == "add_task":
        task = Task(
            title=action_data.get("title", "New Task"),
            description=action_data.get("description"),
            priority=action_data.get("priority", "medium"),
            category=action_data.get("category"),
        )
        db.add(task)
        await db.commit()

    elif action == "add_reminder":
        try:
            remind_at = datetime.fromisoformat(action_data.get("remind_at", ""))
            reminder = Reminder(
                title=action_data.get("title", "Reminder"),
                note=action_data.get("note"),
                remind_at=remind_at,
            )
            db.add(reminder)
            await db.commit()
        except (ValueError, TypeError):
            pass

    elif action == "research":
        query = action_data.get("query", "")
        if query:
            summary = await research_topic(query)
            entry = ResearchEntry(query=query, summary=summary)
            db.add(entry)
            await db.commit()


def extract_action(text: str) -> tuple[str, dict | None]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            clean_text = text[: match.start()].strip()
            return clean_text, data
        except json.JSONDecodeError:
            pass
    return text, None


@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(MAX_HISTORY)
    )
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content, "id": m.id} for m in messages]


@router.post("")
async def send_message(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Load recent history
    history_result = await db.execute(
        select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(MAX_HISTORY)
    )
    history = list(reversed(history_result.scalars().all()))

    # Load context
    tasks_result = await db.execute(select(Task))
    tasks = tasks_result.scalars().all()

    reminders_result = await db.execute(select(Reminder))
    reminders = reminders_result.scalars().all()

    # Build message list for API
    api_messages = [{"role": m.role, "content": m.content} for m in history]
    api_messages.append({"role": "user", "content": body.message})

    # Get AI response
    raw_response = await chat_with_agent(api_messages, tasks, reminders)
    clean_response, action_data = extract_action(raw_response)

    # Persist messages
    user_msg = ChatMessage(role="user", content=body.message)
    assistant_msg = ChatMessage(role="assistant", content=clean_response)
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    # Apply any actions
    if action_data:
        await _apply_action(action_data, db)

    return {
        "response": clean_response,
        "action": action_data,
    }


@router.delete("/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatMessage))
    for msg in result.scalars().all():
        await db.delete(msg)
    await db.commit()
    return {"ok": True}
