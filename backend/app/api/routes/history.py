from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.history import HistoryProjectEntry, ProjectActivityResponse


router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryProjectEntry])
def list_history(request: Request) -> list[HistoryProjectEntry]:
    return request.app.state.history_service.list_history()


@router.get("/projects/{project_id}", response_model=ProjectActivityResponse)
def get_project_activity(project_id: str, request: Request) -> ProjectActivityResponse:
    return request.app.state.history_service.get_project_activity(project_id)
