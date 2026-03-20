from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.build import BuildSummary
from app.schemas.project import ProjectSummary


class AuditLogEntry(BaseModel):
    id: str
    event_type: str
    created_at: str
    payload: dict[str, Any] = Field(default_factory=dict)


class HistoryProjectEntry(BaseModel):
    project: ProjectSummary
    latest_build: BuildSummary | None = None
    latest_analysis_at: str | None = None
    publish_profile_count: int = 0
    recent_audit_events: list[AuditLogEntry] = Field(default_factory=list)


class ProjectActivityResponse(BaseModel):
    project: ProjectSummary
    latest_analysis_at: str | None = None
    recent_builds: list[BuildSummary] = Field(default_factory=list)
    publish_profile_count: int = 0
    recent_audit_events: list[AuditLogEntry] = Field(default_factory=list)
