from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import VAR_DIR
from .db import init_db
from .queue import JobQueue
from .routes import ingest, jobs, uploads, ws
from .storage import ensure_storage_dirs
from .ws import WebSocketManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    ensure_storage_dirs()
    init_db()
    app.state.ws_manager = WebSocketManager()
    app.state.queue = JobQueue(ws_manager=app.state.ws_manager)
    await app.state.queue.start()
    yield
    await app.state.queue.stop()


import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
allowed_origins = [o.strip() for o in allowed_origins if o.strip()]

app = FastAPI(title="Football Input Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(ingest.router)
app.include_router(jobs.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
