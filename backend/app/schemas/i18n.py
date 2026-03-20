from __future__ import annotations

from pydantic import BaseModel


class I18nMetadataResponse(BaseModel):
    default_locale: str
    fallback_locale: str
    supported_locales: list[str]
