from __future__ import annotations

from typing import Any, Dict, Set

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(job_id, set()).add(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        if job_id in self._connections:
            self._connections[job_id].discard(websocket)
            if not self._connections[job_id]:
                self._connections.pop(job_id, None)

    async def broadcast(self, job_id: str, payload: Dict) -> None:
        if job_id not in self._connections:
            return
        dead = []
        for ws in self._connections[job_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)
