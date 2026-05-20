from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..db import get_job
from ..deps import get_ws_manager
from ..ws import WebSocketManager


router = APIRouter(tags=["ws"])


@router.websocket("/ws/jobs/{job_id}")
async def job_updates(
    websocket: WebSocket,
    job_id: str,
    manager: WebSocketManager = Depends(get_ws_manager),
) -> None:
    await manager.connect(job_id, websocket)
    try:
        job = get_job(job_id)
        if job:
            await websocket.send_json({"type": "job", "payload": job})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception:
        manager.disconnect(job_id, websocket)
