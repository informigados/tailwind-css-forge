from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectImportRequest(BaseModel):
    source_path: str = Field(..., description="Caminho absoluto da pasta do projeto.")


class ProjectSummary(BaseModel):
    id: str
    name: str
    source_path: str
    workspace_path: str
    fingerprint: str
    created_at: str
    updated_at: str
    last_status: str | None = None


class ProjectImportResponse(BaseModel):
    project: ProjectSummary
