from __future__ import annotations

import json

from app.db.session import Database
from app.schemas.build import BuildSummary
from app.schemas.history import AuditLogEntry, HistoryProjectEntry, ProjectActivityResponse
from app.services.project_service import ProjectService


class HistoryService:
    def __init__(self, database: Database, project_service: ProjectService) -> None:
        self.database = database
        self.project_service = project_service

    def list_history(self) -> list[HistoryProjectEntry]:
        projects = self.project_service.list_projects()
        return [
            HistoryProjectEntry(
                project=project,
                latest_build=self._get_latest_build(project.id),
                latest_analysis_at=self._get_latest_analysis_at(project.id),
                publish_profile_count=self._count_publish_profiles(project.id),
                recent_audit_events=self._get_recent_audit_events(project.id, limit=3),
            )
            for project in projects
        ]

    def get_project_activity(self, project_id: str) -> ProjectActivityResponse:
        project = self.project_service.get_project(project_id)
        recent_builds = self.database.fetch_all(
            """
            SELECT id, project_id, analysis_id, strategy_used, status, progress_percent,
                   current_step, current_message, cancel_requested, started_at, finished_at,
                   duration_ms, output_path, report_path, log_path
            FROM builds
            WHERE project_id = ?
            ORDER BY started_at DESC
            LIMIT 10
            """,
            (project_id,),
        )
        return ProjectActivityResponse(
            project=project,
            latest_analysis_at=self._get_latest_analysis_at(project_id),
            recent_builds=[self._to_build_summary(row) for row in recent_builds],
            publish_profile_count=self._count_publish_profiles(project_id),
            recent_audit_events=self._get_recent_audit_events(project_id, limit=10),
        )

    def _get_latest_build(self, project_id: str) -> BuildSummary | None:
        row = self.database.fetch_one(
            """
            SELECT id, project_id, analysis_id, strategy_used, status, progress_percent,
                   current_step, current_message, cancel_requested, started_at, finished_at,
                   duration_ms, output_path, report_path, log_path
            FROM builds
            WHERE project_id = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        return self._to_build_summary(row) if row else None

    def _get_latest_analysis_at(self, project_id: str) -> str | None:
        row = self.database.fetch_one(
            """
            SELECT created_at
            FROM analyses
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        return row["created_at"] if row else None

    def _count_publish_profiles(self, project_id: str) -> int:
        row = self.database.fetch_one(
            "SELECT COUNT(*) AS count FROM publish_profiles WHERE project_id = ?",
            (project_id,),
        )
        return int(row["count"]) if row else 0

    def _get_recent_audit_events(self, project_id: str, *, limit: int) -> list[AuditLogEntry]:
        project_marker = f'"project_id": "{project_id}"'
        rows = self.database.fetch_all(
            """
            SELECT id, event_type, payload_json, created_at
            FROM audit_logs
            WHERE instr(payload_json, ?) > 0
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_marker, limit),
        )
        events: list[AuditLogEntry] = []
        for row in rows:
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            events.append(
                AuditLogEntry(
                    id=row["id"],
                    event_type=row["event_type"],
                    created_at=row["created_at"],
                    payload=payload,
                ),
            )
        return events

    def _to_build_summary(self, row: dict) -> BuildSummary:
        normalized = dict(row)
        normalized["progress_percent"] = int(normalized.get("progress_percent") or 0)
        normalized["cancel_requested"] = bool(normalized.get("cancel_requested"))
        return BuildSummary(
            **normalized,
        )
