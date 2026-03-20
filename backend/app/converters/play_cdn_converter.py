from __future__ import annotations

import os
import re
import ntpath
from pathlib import Path

from app.core.build_context import BuildContext
from app.utils.fs import iter_files


SCRIPT_PATTERN = re.compile(
    r"<script[^>]+src=[\"'][^\"']*(?:@tailwindcss/browser|cdn\.tailwindcss\.com)[^\"']*[\"'][^>]*>\s*</script>",
    re.IGNORECASE,
)
STYLE_BLOCK_PATTERN = re.compile(
    r"<style[^>]+type=[\"']text/tailwindcss[\"'][^>]*>(.*?)</style>",
    re.IGNORECASE | re.DOTALL,
)
HEAD_CLOSE_PATTERN = re.compile(r"</head>", re.IGNORECASE)
HTML_EXTENSIONS = {".html", ".htm", ".php", ".twig"}


class PlayCdnConverter:
    def convert(self, context: BuildContext) -> dict:
        extracted_blocks: list[str] = []
        rewritten_files: list[str] = []

        for file_path in iter_files(context.dist_path):
            if file_path.suffix.lower() not in HTML_EXTENSIONS:
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            matches = STYLE_BLOCK_PATTERN.findall(content)
            if matches:
                extracted_blocks.extend(block.strip() for block in matches if block.strip())

            updated = SCRIPT_PATTERN.sub("", content)
            updated = STYLE_BLOCK_PATTERN.sub("", updated)

            stylesheet_href = self._stylesheet_href(file_path, context.dist_path / "assets" / "css" / "app.css")
            link_tag = f'<link rel="stylesheet" href="{stylesheet_href}">'
            if link_tag not in updated:
                if HEAD_CLOSE_PATTERN.search(updated):
                    updated = HEAD_CLOSE_PATTERN.sub(f"  {link_tag}\n</head>", updated, count=1)
                else:
                    updated = f"{link_tag}\n{updated}"

            file_path.write_text(updated, encoding="utf-8")
            rewritten_files.append(file_path.relative_to(context.dist_path).as_posix())

        return {
            "rewritten_files": rewritten_files,
            "extracted_tailwind_blocks": extracted_blocks,
        }

    def _stylesheet_href(self, html_path: Path, stylesheet_path: Path) -> str:
        html_drive = ntpath.splitdrive(str(html_path))[0].lower()
        stylesheet_drive = ntpath.splitdrive(str(stylesheet_path))[0].lower()
        if html_drive and stylesheet_drive and html_drive != stylesheet_drive:
            return "/assets/css/app.css"

        try:
            relative = os.path.relpath(stylesheet_path, start=html_path.parent)
        except ValueError:
            return "/assets/css/app.css"

        normalized = Path(relative).as_posix()
        if Path(normalized).is_absolute():
            return "/assets/css/app.css"
        return normalized
