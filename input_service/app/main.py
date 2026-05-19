from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import ensure_admin_user
from .config import ADMIN_EMAIL, ADMIN_PASSWORD, VAR_DIR
from .db import init_db
from .middleware import RateLimitMiddleware
from .queue import JobQueue
from .routes import auth, ingest, jobs, uploads, ws
from .storage import ensure_storage_dirs
from .ws import WebSocketManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    ensure_storage_dirs()
    init_db()
    ensure_admin_user(ADMIN_EMAIL, ADMIN_PASSWORD)
    app.state.ws_manager = WebSocketManager()
    app.state.queue = JobQueue(ws_manager=app.state.ws_manager)
    await app.state.queue.start()
    yield
    await app.state.queue.stop()


app = FastAPI(title="Football Input Service", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(ingest.router)
app.include_router(jobs.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
