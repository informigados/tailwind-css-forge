from __future__ import annotations

from pathlib import Path


class ConfigDetector:
    def detect(self, source_path: Path) -> tuple[list[str], list[str]]:
        signals: list[str] = []

        known_files = {
            "tailwind.config.js": "config_tailwind_js",
            "tailwind.config.cjs": "config_tailwind_cjs",
            "tailwind.config.ts": "config_tailwind_ts",
            "tailwind.config.mjs": "config_tailwind_mjs",
            "tailwind.config.mts": "config_tailwind_mts",
            "postcss.config.js": "config_postcss_js",
            "postcss.config.cjs": "config_postcss_cjs",
            "postcss.config.ts": "config_postcss_ts",
            "postcss.config.mjs": "config_postcss_mjs",
            "vite.config.js": "config_vite_js",
            "vite.config.ts": "config_vite_ts",
            "vite.config.mjs": "config_vite_mjs",
            "vite.config.mts": "config_vite_mts",
        }

        for file_name, signal in known_files.items():
            if (source_path / file_name).exists():
                signals.append(signal)

        return sorted(set(signals)), []
