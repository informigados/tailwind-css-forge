from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.publish import (
    PublishBuildRequest,
    PublishConnectionTestRequest,
    PublishConnectionTestResponse,
    PublishProfileDeleteResponse,
    PublishProfileInput,
    PublishProfileResponse,
    PublishProfileSummary,
    PublishResultResponse,
)


router = APIRouter(tags=["publish"])


@router.get("/projects/{project_id}/publish/profiles", response_model=list[PublishProfileSummary])
def list_publish_profiles(project_id: str, request: Request) -> list[PublishProfileSummary]:
    return request.app.state.publish_service.list_profiles(project_id)


@router.post("/projects/{project_id}/publish/profiles", response_model=PublishProfileResponse, status_code=201)
def create_publish_profile(
    project_id: str,
    payload: PublishProfileInput,
    request: Request,
) -> PublishProfileResponse:
    profile = request.app.state.publish_service.create_profile(project_id, payload)
    return PublishProfileResponse(profile=profile)


@router.put("/projects/{project_id}/publish/profiles/{profile_id}", response_model=PublishProfileResponse)
def update_publish_profile(
    project_id: str,
    profile_id: str,
    payload: PublishProfileInput,
    request: Request,
) -> PublishProfileResponse:
    profile = request.app.state.publish_service.update_profile(project_id, profile_id, payload)
    return PublishProfileResponse(profile=profile)


@router.delete(
    "/projects/{project_id}/publish/profiles/{profile_id}",
    response_model=PublishProfileDeleteResponse,
)
def delete_publish_profile(
    project_id: str,
    profile_id: str,
    request: Request,
) -> PublishProfileDeleteResponse:
    return request.app.state.publish_service.delete_profile(project_id, profile_id)


@router.post(
    "/projects/{project_id}/publish/test",
    response_model=PublishConnectionTestResponse,
    status_code=200,
)
def test_publish_connection(
    project_id: str,
    payload: PublishConnectionTestRequest,
    request: Request,
) -> PublishConnectionTestResponse:
    return request.app.state.publish_service.test_connection(project_id, payload)


@router.post("/builds/{build_id}/publish/ftp", response_model=PublishResultResponse, status_code=201)
def publish_build_ftp(build_id: str, payload: PublishBuildRequest, request: Request) -> PublishResultResponse:
    return request.app.state.publish_service.publish_build(build_id, "ftp", payload)


@router.post("/builds/{build_id}/publish/sftp", response_model=PublishResultResponse, status_code=201)
def publish_build_sftp(build_id: str, payload: PublishBuildRequest, request: Request) -> PublishResultResponse:
    return request.app.state.publish_service.publish_build(build_id, "sftp", payload)
