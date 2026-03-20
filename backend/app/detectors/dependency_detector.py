from __future__ import annotations

import json
import re
from pathlib import Path


class DependencyDetector:
    def detect(self, source_path: Path) -> tuple[list[str], list[str]]:
        package_json = source_path / "package.json"
        if not package_json.exists():
            return [], []

        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [], ["package.json inválido; dependências não puderam ser analisadas."]

        dependency_maps = [
            payload.get("dependencies", {}),
            payload.get("devDependencies", {}),
        ]
        merged_dependencies: dict[str, str] = {}
        for dependency_map in dependency_maps:
            merged_dependencies.update(dependency_map)

        signals: list[str] = []
        for dependency in ("tailwindcss", "@tailwindcss/vite", "postcss", "autoprefixer", "vite"):
            if dependency in merged_dependencies:
                normalized = dependency.replace("/", "_").replace("@", "").replace("-", "_")
                signals.append(f"dependency_{normalized}")
                major_version = self._extract_major_version(merged_dependencies[dependency])
                if major_version is not None:
                    signals.append(f"dependency_{normalized}_major_{major_version}")

        return sorted(set(signals)), []

    def _extract_major_version(self, version_spec: str) -> int | None:
        match = re.search(r"(\d+)", version_spec)
        if not match:
            return None
        return int(match.group(1))
