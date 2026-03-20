from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.project import ProjectImportRequest, ProjectImportResponse, ProjectSummary


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/import", response_model=ProjectImportResponse, status_code=201)
def import_project(payload: ProjectImportRequest, request: Request) -> ProjectImportResponse:
    project = request.app.state.project_service.import_project(payload.source_path)
    return ProjectImportResponse(project=project)


@router.get("", response_model=list[ProjectSummary])
def list_projects(request: Request) -> list[ProjectSummary]:
    return request.app.state.project_service.list_projects()


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: str, request: Request) -> ProjectSummary:
    return request.app.state.project_service.get_project(project_id)
