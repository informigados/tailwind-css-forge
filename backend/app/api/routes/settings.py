from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.settings import SettingsResponse, SettingsUpdateRequest


router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    settings = request.app.state.settings_service.get_settings()
    return SettingsResponse(settings=settings)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest, request: Request) -> SettingsResponse:
    settings = request.app.state.settings_service.update_settings(payload)
    return SettingsResponse(settings=settings)
