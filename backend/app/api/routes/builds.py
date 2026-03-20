from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.build import BuildCancelResponse, BuildStartRequest, BuildStartResponse, BuildSummary


router = APIRouter(tags=["builds"])


@router.post("/projects/{project_id}/build", response_model=BuildStartResponse, status_code=202)
def start_build(project_id: str, payload: BuildStartRequest, request: Request) -> BuildStartResponse:
    build = request.app.state.build_service.start_build(project_id, minify=payload.minify)
    return BuildStartResponse(build=build, result=None)


@router.get("/projects/{project_id}/builds", response_model=list[BuildSummary])
def list_project_builds(project_id: str, request: Request) -> list[BuildSummary]:
    return request.app.state.build_service.list_project_builds(project_id)


@router.get("/builds/{build_id}", response_model=BuildSummary)
def get_build(build_id: str, request: Request) -> BuildSummary:
    return request.app.state.build_service.get_build(build_id)


@router.get("/builds/{build_id}/report")
def get_build_report(build_id: str, request: Request) -> dict:
    return request.app.state.build_service.get_build_report(build_id)


@router.get("/builds/{build_id}/log")
def get_build_log(build_id: str, request: Request) -> dict:
    return request.app.state.build_service.get_build_log(build_id)


@router.post("/builds/{build_id}/cancel", response_model=BuildCancelResponse, status_code=200)
def cancel_build(build_id: str, request: Request) -> BuildCancelResponse:
    build = request.app.state.build_service.cancel_build(build_id)
    return BuildCancelResponse(build=build)
