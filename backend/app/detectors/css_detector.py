from __future__ import annotations

from pathlib import Path

from app.utils.fs import iter_files


class CssDetector:
    def detect(self, source_path: Path) -> tuple[list[str], list[str]]:
        signals: list[str] = []
        warnings: list[str] = []

        for file_path in iter_files(source_path):
            if file_path.suffix.lower() not in {".css", ".pcss", ".scss"}:
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if '@import "tailwindcss"' in content or "@import 'tailwindcss'" in content:
                signals.append("css_import_tailwindcss")
            if "@theme" in content:
                signals.append("css_theme_block")
            if "@source" in content:
                signals.append("css_source_directive")
            if "@config" in content:
                signals.append("css_config_directive")
            if "@plugin" in content:
                signals.append("css_plugin_directive")
            if "@tailwind base;" in content:
                signals.append("css_tailwind_base")
            if "@tailwind components;" in content:
                signals.append("css_tailwind_components")
            if "@tailwind utilities;" in content:
                signals.append("css_tailwind_utilities")
            if ("@import \"tailwindcss\"" in content or "@import 'tailwindcss'" in content) and "@tailwind " in content:
                warnings.append(
                    f"Dialetos mistos do Tailwind detectados em {file_path.relative_to(source_path).as_posix()}",
                )

        return sorted(set(signals)), sorted(set(warnings))
