from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.db.session import Database
from app.schemas.export import ExportSummary
from app.services.build_service import BuildService
from app.utils.archive import create_zip_from_directory
from app.utils.time import utc_now_iso


class ExportService:
    max_zip_size_bytes = 250 * 1024 * 1024

    def __init__(self, database: Database, build_service: BuildService, exports_root: Path) -> None:
        self.database = database
        self.build_service = build_service
        self.exports_root = exports_root

    def export_build_zip(self, build_id: str) -> ExportSummary:
        build = self.build_service.get_build(build_id)
        if build.status != "success" or not build.output_path:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A exportação ZIP exige um build concluído com sucesso.",
            )

        dist_path = Path(build.output_path)
        if not dist_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A pasta dist do build não foi encontrada.",
            )
        self._ensure_export_size_allowed(dist_path)

        export_id = f"export_{uuid.uuid4().hex[:12]}"
        created_at = utc_now_iso()
        output_path = self.exports_root / f"{build.project_id}-{build.id}.zip"
        create_zip_from_directory(dist_path, output_path)

        self.database.execute(
            """
            INSERT INTO exports (id, build_id, format, output_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (export_id, build_id, "zip", str(output_path), created_at),
        )
        return ExportSummary(
            id=export_id,
            build_id=build_id,
            format="zip",
            output_path=str(output_path),
            created_at=created_at,
        )

    def _ensure_export_size_allowed(self, dist_path: Path) -> None:
        total_size = sum(path.stat().st_size for path in dist_path.rglob("*") if path.is_file())
        if total_size <= self.max_zip_size_bytes:
            return

        limit_mb = self.max_zip_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"A pasta dist excede o limite de exportacao ZIP de {limit_mb} MB.",
        )
