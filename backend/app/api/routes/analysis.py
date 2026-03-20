from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.analysis import AnalyzeProjectResponse, AnalysisSummary


router = APIRouter(prefix="/projects", tags=["analysis"])


@router.post("/{project_id}/analyze", response_model=AnalyzeProjectResponse, status_code=201)
def analyze_project(project_id: str, request: Request) -> AnalyzeProjectResponse:
    analysis = request.app.state.analysis_service.analyze_project(project_id)
    return AnalyzeProjectResponse(analysis=analysis)


@router.get("/{project_id}/analysis/latest", response_model=AnalysisSummary)
def latest_analysis(project_id: str, request: Request) -> AnalysisSummary:
    return request.app.state.analysis_service.get_latest_analysis(project_id)
