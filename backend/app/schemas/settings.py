from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ThemeValue = Literal["system", "dark", "light"]


class SettingsSummary(BaseModel):
    language: str = Field(min_length=2, max_length=20)
    theme: ThemeValue
    default_workspace_path: str
    default_exports_path: str
    backup_before_build: bool = True
    default_minify: bool = True
    detailed_logs: bool = True
    build_timeout_seconds: int = Field(ge=30, le=3600)


class SettingsUpdateRequest(BaseModel):
    language: str = Field(min_length=2, max_length=20)
    theme: ThemeValue
    default_workspace_path: str
    default_exports_path: str
    backup_before_build: bool = True
    default_minify: bool = True
    detailed_logs: bool = True
    build_timeout_seconds: int = Field(ge=30, le=3600)


class SettingsResponse(BaseModel):
    settings: SettingsSummary
