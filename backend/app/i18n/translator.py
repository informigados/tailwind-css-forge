from __future__ import annotations

from app.i18n.catalog import DEFAULT_LOCALE, FALLBACK_LOCALE, MESSAGES, SUPPORTED_LOCALES


class Translator:
    def __init__(
        self,
        *,
        default_locale: str = DEFAULT_LOCALE,
        fallback_locale: str = FALLBACK_LOCALE,
        supported_locales: tuple[str, ...] = SUPPORTED_LOCALES,
    ) -> None:
        self.default_locale = default_locale
        self.fallback_locale = fallback_locale
        self.supported_locales = supported_locales

    def normalize(self, locale: str | None) -> str:
        if locale in self.supported_locales:
            return str(locale)
        return self.default_locale

    def translate(self, key: str, locale: str | None = None, **values: str) -> str:
        normalized_locale = self.normalize(locale)
        template = (
            MESSAGES.get(normalized_locale, {}).get(key)
            or MESSAGES.get(self.fallback_locale, {}).get(key)
            or MESSAGES.get(self.default_locale, {}).get(key)
            or key
        )
        return template.format(**values)
