from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.db.session import Database
from app.detectors.tailwind_detector import TailwindDetector
from app.planners.build_plan_factory import BuildPlanFactory
from app.schemas.analysis import AnalysisSummary
from app.services.project_service import ProjectService
from app.utils.fs import read_json, write_json
from app.utils.time import utc_now_iso


class AnalysisService:
    def __init__(
        self,
        database: Database,
        project_service: ProjectService,
        detector: TailwindDetector | None = None,
        build_plan_factory: BuildPlanFactory | None = None,
    ) -> None:
        self.database = database
        self.project_service = project_service
        self.detector = detector or TailwindDetector()
        self.build_plan_factory = build_plan_factory or BuildPlanFactory()

    def analyze_project(self, project_id: str) -> AnalysisSummary:
        project = self.project_service.get_project(project_id)
        workspace_path = Path(project.workspace_path)
        src_path = workspace_path / "src"
        if not src_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace do projeto está incompleto; a pasta src não foi encontrada.",
            )

        analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
        created_at = utc_now_iso()
        analysis_payload = self.detector.analyze(src_path)
        build_plan = self.build_plan_factory.create(analysis_payload)

        self.database.execute(
            """
            INSERT INTO analyses (
                id, project_id, tailwind_detected, strategy_hint, probable_major_version,
                confidence, signals_json, warnings_json, framework_hints_json, project_style, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                project_id,
                int(analysis_payload["tailwind_detected"]),
                analysis_payload["strategy_hint"],
                analysis_payload["probable_major_version"],
                analysis_payload["confidence"],
                json.dumps(analysis_payload["signals"], ensure_ascii=False),
                json.dumps(analysis_payload["warnings"], ensure_ascii=False),
                json.dumps(analysis_payload["framework_hints"], ensure_ascii=False),
                analysis_payload["project_style"],
                created_at,
            ),
        )

        write_json(workspace_path / "meta" / "analysis.json", {"analysis_id": analysis_id, **analysis_payload})
        write_json(workspace_path / "meta" / "build_plan.json", build_plan)
        self.project_service.mark_status(project_id, "analyzed")

        return AnalysisSummary(
            id=analysis_id,
            project_id=project_id,
            build_plan=build_plan,
            created_at=created_at,
            **analysis_payload,
        )

    def get_latest_analysis(self, project_id: str) -> AnalysisSummary:
        project = self.project_service.get_project(project_id)
        row = self.database.fetch_one(
            """
            SELECT id, project_id, tailwind_detected, strategy_hint, probable_major_version,
                   confidence, signals_json, warnings_json, framework_hints_json, project_style, created_at
            FROM analyses
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma análise encontrada para o projeto.",
            )

        build_plan = read_json(Path(project.workspace_path) / "meta" / "build_plan.json")
        return AnalysisSummary(
            id=row["id"],
            project_id=row["project_id"],
            tailwind_detected=bool(row["tailwind_detected"]),
            strategy_hint=row["strategy_hint"],
            probable_major_version=row["probable_major_version"],
            confidence=row["confidence"],
            signals=json.loads(row["signals_json"]),
            warnings=json.loads(row["warnings_json"]),
            framework_hints=json.loads(row["framework_hints_json"] or "[]"),
            project_style=row["project_style"],
            build_plan=build_plan,
            created_at=row["created_at"],
        )
