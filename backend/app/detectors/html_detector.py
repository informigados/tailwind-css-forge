from __future__ import annotations

import re
from pathlib import Path

from app.utils.fs import iter_files


PLAY_CDN_V4_PATTERN = re.compile(r"@tailwindcss/browser(?:@\d+)?", re.IGNORECASE)
LEGACY_CDN_PATTERN = re.compile(r"cdn\.tailwindcss\.com", re.IGNORECASE)
TAILWIND_STYLE_BLOCK_PATTERN = re.compile(
    r"<style[^>]+type=[\"']text/tailwindcss[\"']",
    re.IGNORECASE,
)
CLASS_DYNAMICS_PATTERN = re.compile(
    r"(classList\.|classnames\(|clsx\(|`[^`]*\$\{[^}]+\}[^`]*`)",
    re.IGNORECASE,
)
BOUND_CLASS_PATTERN = re.compile(r"(:class=|v-bind:class=)", re.IGNORECASE)
TEMPLATE_CLASS_PATTERN = re.compile(r'class\s*=\s*["\'][^"\']*(\{\{|\{%\s*|<\?=)', re.IGNORECASE)
MAX_SCAN_BYTES = 512 * 1024
SCAN_EXTENSIONS = {".html", ".htm", ".php", ".twig", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}


class HtmlDetector:
    def detect(self, source_path: Path) -> tuple[list[str], list[str]]:
        signals: list[str] = []
        warnings: list[str] = []

        for file_path in iter_files(source_path):
            if file_path.suffix.lower() not in SCAN_EXTENSIONS:
                continue

            content = self._read_excerpt(file_path, source_path, warnings)
            if content is None:
                continue
            if PLAY_CDN_V4_PATTERN.search(content):
                signals.append("cdn_browser_script_v4")
            if LEGACY_CDN_PATTERN.search(content):
                signals.append("cdn_tailwindcss_com")
            if TAILWIND_STYLE_BLOCK_PATTERN.search(content):
                signals.append("text_tailwindcss_style_block")
            if CLASS_DYNAMICS_PATTERN.search(content):
                warnings.append(
                    f"Possível uso de classes dinâmicas em {file_path.relative_to(source_path).as_posix()}",
                )
            if BOUND_CLASS_PATTERN.search(content) or TEMPLATE_CLASS_PATTERN.search(content):
                warnings.append(
                    f"Possivel composicao de classes por template em {file_path.relative_to(source_path).as_posix()}",
                )

        return sorted(set(signals)), sorted(set(warnings))

    def _read_excerpt(self, file_path: Path, source_path: Path, warnings: list[str]) -> str | None:
        size = file_path.stat().st_size
        if size > MAX_SCAN_BYTES:
            warnings.append(
                f"Arquivo grande analisado parcialmente em {file_path.relative_to(source_path).as_posix()}",
            )

        with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
            excerpt = handle.read(MAX_SCAN_BYTES)

        return excerpt or None
