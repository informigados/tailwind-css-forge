from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import Settings as RuntimeSettings
from app.db.session import Database
from app.i18n import Translator
from app.schemas.settings import SettingsSummary, SettingsUpdateRequest


class SettingsService:
    def __init__(
        self,
        database: Database,
        runtime_settings: RuntimeSettings,
        translator: Translator,
    ) -> None:
        self.database = database
        self.runtime_settings = runtime_settings
        self.translator = translator

    def get_settings(self) -> SettingsSummary:
        payload = self._load_serialized_settings()
        return SettingsSummary(
            language=self.translator.normalize(payload.get("language")),
            theme=payload.get("theme", "system"),
            default_workspace_path=payload.get(
                "default_workspace_path",
                str(self.runtime_settings.workspaces_path),
            ),
            default_exports_path=payload.get(
                "default_exports_path",
                str(self.runtime_settings.exports_path),
            ),
            backup_before_build=self._parse_bool(payload.get("backup_before_build"), True),
            default_minify=self._parse_bool(payload.get("default_minify"), True),
            detailed_logs=self._parse_bool(payload.get("detailed_logs"), True),
            build_timeout_seconds=self._parse_int(payload.get("build_timeout_seconds"), 600),
        )

    def update_settings(self, payload: SettingsUpdateRequest) -> SettingsSummary:
        if payload.language not in self.translator.supported_locales:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.translator.translate("settings.unsupported_language", payload.language),
            )
        serialized = {
            "language": payload.language,
            "theme": payload.theme,
            "default_workspace_path": payload.default_workspace_path,
            "default_exports_path": payload.default_exports_path,
            "backup_before_build": self._serialize_bool(payload.backup_before_build),
            "default_minify": self._serialize_bool(payload.default_minify),
            "detailed_logs": self._serialize_bool(payload.detailed_logs),
            "build_timeout_seconds": str(payload.build_timeout_seconds),
        }
        with self.database.connect() as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                list(serialized.items()),
            )
            connection.commit()
        return self.get_settings()

    def _load_serialized_settings(self) -> dict[str, str]:
        rows = self.database.fetch_all("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}

    @staticmethod
    def _serialize_bool(value: bool) -> str:
        return "1" if value else "0"

    @staticmethod
    def _parse_bool(value: str | None, default: bool) -> bool:
        if value is None:
            return default
        return value in {"1", "true", "True", "yes"}

    @staticmethod
    def _parse_int(value: str | None, default: int) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
