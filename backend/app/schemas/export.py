from __future__ import annotations

from pydantic import BaseModel


class ExportSummary(BaseModel):
    id: str
    build_id: str
    format: str
    output_path: str
    created_at: str


class ZipExportResponse(BaseModel):
    export: ExportSummary
