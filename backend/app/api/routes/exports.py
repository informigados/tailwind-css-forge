from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.export import ZipExportResponse


router = APIRouter(tags=["exports"])


@router.post("/builds/{build_id}/export/zip", response_model=ZipExportResponse, status_code=201)
def export_build_zip(build_id: str, request: Request) -> ZipExportResponse:
    export = request.app.state.export_service.export_build_zip(build_id)
    return ZipExportResponse(export=export)
