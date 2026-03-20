from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()
MAX_BUILD_SOCKET_IDLE_SECONDS = 300
MAX_BUILD_SOCKET_TOTAL_SECONDS = 1800


@router.websocket("/ws/builds/{build_id}")
async def build_progress_socket(build_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    started_at = asyncio.get_running_loop().time()
    last_change_at = started_at
    last_snapshot: tuple[object, ...] | None = None
    try:
        while True:
            build = websocket.app.state.build_service.get_build(build_id)
            snapshot = (
                build.status,
                build.progress_percent,
                build.current_step,
                build.current_message,
                build.cancel_requested,
            )
            now = asyncio.get_running_loop().time()
            if snapshot != last_snapshot:
                last_snapshot = snapshot
                last_change_at = now
            await websocket.send_json(
                {
                    "type": "progress",
                    "build_id": build.id,
                    "status": build.status,
                    "progress_percent": build.progress_percent,
                    "step": build.current_step,
                    "message": build.current_message,
                    "cancel_requested": build.cancel_requested,
                    "started_at": build.started_at,
                    "finished_at": build.finished_at,
                },
            )
            if build.status in {"success", "failed", "cancelled"}:
                break
            if (now - last_change_at) >= MAX_BUILD_SOCKET_IDLE_SECONDS:
                break
            if (now - started_at) >= MAX_BUILD_SOCKET_TOTAL_SECONDS:
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
    finally:
        await websocket.close()
