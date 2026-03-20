from __future__ import annotations

from fastapi import HTTPException, status

from app.db.session import Database
from app.schemas.project import ProjectSummary
from app.services.workspace_service import WorkspaceService
from app.utils.time import utc_now_iso


class ProjectService:
    def __init__(self, database: Database, workspace_service: WorkspaceService) -> None:
        self.database = database
        self.workspace_service = workspace_service

    def import_project(self, source_path_raw: str) -> ProjectSummary:
        source_path = self.workspace_service.validate_source_path(source_path_raw)
        project_id = self.workspace_service.new_project_id()
        workspace_path = self.workspace_service.create_workspace(project_id)
        workspace_meta = self.workspace_service.populate_workspace(source_path, workspace_path)
        timestamp = utc_now_iso()

        self.database.execute(
            """
            INSERT INTO projects (
                id, name, source_path, workspace_path, fingerprint, created_at, updated_at, last_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                source_path.name,
                str(source_path),
                str(workspace_path),
                workspace_meta["fingerprint"],
                timestamp,
                timestamp,
                "imported",
            ),
        )

        return self.get_project(project_id)

    def list_projects(self) -> list[ProjectSummary]:
        rows = self.database.fetch_all(
            """
            SELECT id, name, source_path, workspace_path, fingerprint, created_at, updated_at, last_status
            FROM projects
            ORDER BY created_at DESC
            """,
        )
        return [ProjectSummary(**row) for row in rows]

    def get_project(self, project_id: str) -> ProjectSummary:
        row = self.database.fetch_one(
            """
            SELECT id, name, source_path, workspace_path, fingerprint, created_at, updated_at, last_status
            FROM projects
            WHERE id = ?
            """,
            (project_id,),
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado.",
            )

        return ProjectSummary(**row)

    def mark_status(self, project_id: str, status_value: str) -> None:
        self.database.execute(
            "UPDATE projects SET last_status = ?, updated_at = ? WHERE id = ?",
            (status_value, utc_now_iso(), project_id),
        )
