from __future__ import annotations

from pydantic import BaseModel, Field


class BuildSummary(BaseModel):
    id: str
    project_id: str
    analysis_id: str | None = None
    strategy_used: str
    status: str
    progress_percent: int = 0
    current_step: str | None = None
    current_message: str | None = None
    cancel_requested: bool = False
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    output_path: str | None = None
    report_path: str | None = None
    log_path: str | None = None


class BuildStartRequest(BaseModel):
    minify: bool = True


class BuildResultPayload(BaseModel):
    status: str
    strategy_used: str
    outputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    dist_path: str | None = None
    report_path: str | None = None
    log_path: str | None = None


class BuildStartResponse(BaseModel):
    build: BuildSummary
    result: BuildResultPayload | None = None


class BuildCancelResponse(BaseModel):
    build: BuildSummary
