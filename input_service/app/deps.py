from __future__ import annotations

from fastapi import Request

from .queue import JobQueue
from .ws import WebSocketManager


def get_queue(request: Request) -> JobQueue:
    return request.app.state.queue


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager
