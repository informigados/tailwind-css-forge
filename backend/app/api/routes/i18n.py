from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.i18n import I18nMetadataResponse


router = APIRouter(tags=["i18n"])


@router.get("/i18n", response_model=I18nMetadataResponse)
def get_i18n_metadata(request: Request) -> I18nMetadataResponse:
    translator = request.app.state.translator
    return I18nMetadataResponse(
        default_locale=translator.default_locale,
        fallback_locale=translator.fallback_locale,
        supported_locales=list(translator.supported_locales),
    )
