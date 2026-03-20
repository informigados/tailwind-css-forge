from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import Settings
from app.utils.fs import copy_project_tree, ensure_directory, safe_resolve, write_json
from app.utils.hash import calculate_directory_fingerprint
from app.utils.time import utc_now_iso


class WorkspaceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def prepare_runtime_directories(self) -> None:
        for path in (
            self.settings.runtime_path,
            self.settings.workspaces_path,
            self.settings.logs_path,
            self.settings.temp_path,
            self.settings.exports_path,
            self.settings.secrets_path,
            self.settings.known_hosts_path.parent,
        ):
            ensure_directory(path)

    def validate_source_path(self, raw_path: str) -> Path:
        try:
            source_path = safe_resolve(Path(raw_path))
        except (FileNotFoundError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O caminho informado não existe ou não pode ser acessado.",
            ) from exc

        if not source_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O caminho informado precisa apontar para uma pasta existente.",
            )

        runtime_path = self.settings.runtime_path.resolve()
        if runtime_path.is_relative_to(source_path) or source_path.is_relative_to(runtime_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é permitido importar uma pasta que contenha ou esteja dentro do runtime do Forge.",
            )

        return source_path

    def create_workspace(self, project_id: str) -> Path:
        workspace_path = ensure_directory(self.settings.workspaces_path / project_id)
        for directory_name in (
            "original_snapshot",
            "src",
            "dist",
            "backups",
            "reports",
            "temp",
            "meta",
        ):
            ensure_directory(workspace_path / directory_name)

        return workspace_path

    def populate_workspace(self, source_path: Path, workspace_path: Path) -> dict:
        copy_project_tree(
            source_path,
            workspace_path / "original_snapshot",
            self.settings.ignored_copy_names,
        )
        copy_project_tree(
            source_path,
            workspace_path / "src",
            self.settings.ignored_copy_names,
        )

        fingerprint = calculate_directory_fingerprint(
            source_path,
            self.settings.ignored_copy_names,
        )
        workspace_meta = {
            "project_name": source_path.name,
            "source_path": str(source_path),
            "workspace_path": str(workspace_path),
            "fingerprint": fingerprint,
            "ignored_copy_names": list(self.settings.ignored_copy_names),
            "imported_at": utc_now_iso(),
        }
        write_json(workspace_path / "meta" / "project_meta.json", workspace_meta)
        return workspace_meta

    def new_project_id(self) -> str:
        return f"proj_{uuid.uuid4().hex[:12]}"
