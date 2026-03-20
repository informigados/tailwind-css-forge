from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    id: str
    project_id: str
    tailwind_detected: bool
    strategy_hint: str | None = None
    probable_major_version: int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    framework_hints: list[str] = Field(default_factory=list)
    project_style: str | None = None
    build_plan: dict = Field(default_factory=dict)
    created_at: str


class AnalyzeProjectResponse(BaseModel):
    analysis: AnalysisSummary
