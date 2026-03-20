from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def healthcheck(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "version": settings.app_version,
    }
