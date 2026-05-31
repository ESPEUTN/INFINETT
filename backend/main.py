import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from backend.database import init_db
from backend.routes import tasks, reminders, research, reports, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Life Management Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(reminders.router)
app.include_router(research.router)
app.include_router(reports.router)
app.include_router(chat.router)

FRONTEND = Path(__file__).parent.parent / "frontend" / "app.html"


@app.get("/")
async def serve_app():
    return FileResponse(FRONTEND)


@app.get("/health")
async def health():
    return {"status": "ok"}
