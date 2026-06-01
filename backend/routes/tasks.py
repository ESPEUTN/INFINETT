from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    category: str | None = None
    due_date: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    category: str | None = None
    due_date: str | None = None
    completed: bool | None = None


def task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "category": t.category,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed": t.completed,
        "created_at": t.created_at.isoformat(),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.get("")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = result.scalars().all()
    return [task_to_dict(t) for t in tasks]


@router.post("")
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    due = None
    if body.due_date:
        try:
            due = datetime.fromisoformat(body.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_date format")

    task = Task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        due_date=due,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task_to_dict(task)


@router.patch("/{task_id}")
async def update_task(task_id: int, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.priority is not None:
        task.priority = body.priority
    if body.category is not None:
        task.category = body.category
    if body.due_date is not None:
        task.due_date = datetime.fromisoformat(body.due_date)
    if body.completed is not None:
        task.completed = body.completed
        if body.completed and not task.completed_at:
            task.completed_at = datetime.utcnow()
        elif not body.completed:
            task.completed_at = None

    await db.commit()
    await db.refresh(task)
    return task_to_dict(task)


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"ok": True}
