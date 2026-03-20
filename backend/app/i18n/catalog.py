from __future__ import annotations


DEFAULT_LOCALE = "pt-BR"
FALLBACK_LOCALE = "en-US"
SUPPORTED_LOCALES = ("pt-BR", "en-US")

MESSAGES: dict[str, dict[str, str]] = {
    "pt-BR": {
        "settings.unsupported_language": "Idioma não suportado. Use um dos idiomas disponíveis.",
    },
    "en-US": {
        "settings.unsupported_language": "Unsupported language. Use one of the available locales.",
    },
}
