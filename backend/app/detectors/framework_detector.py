from __future__ import annotations

import json
from pathlib import Path

from app.utils.fs import iter_files


class FrameworkDetector:
    dependency_map = {
        "react": "react",
        "react-dom": "react",
        "next": "nextjs",
        "vue": "vue",
        "nuxt": "nuxt",
        "svelte": "svelte",
        "@sveltejs/kit": "sveltekit",
        "astro": "astro",
        "laravel-vite-plugin": "laravel",
        "alpinejs": "alpinejs",
    }

    def detect(self, source_path: Path) -> dict:
        frameworks: set[str] = set()
        signals: set[str] = set()
        warnings: set[str] = set()

        package_json = source_path / "package.json"
        if package_json.exists():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                warnings.add("package.json inválido; framework do projeto não pode ser inferido com segurança.")
            else:
                dependencies = {
                    **payload.get("dependencies", {}),
                    **payload.get("devDependencies", {}),
                }
                for dependency_name, framework_name in self.dependency_map.items():
                    if dependency_name in dependencies:
                        frameworks.add(framework_name)
                        signals.add(f"framework_{framework_name}")

        has_html_templates = False
        has_server_templates = False
        has_component_framework = bool(
            frameworks & {"react", "vue", "svelte", "sveltekit", "astro", "nextjs", "nuxt"},
        )

        for file_path in iter_files(source_path):
            relative_path = file_path.relative_to(source_path).as_posix()
            suffix = file_path.suffix.lower()
            lower_name = file_path.name.lower()

            if suffix in {".html", ".htm"}:
                has_html_templates = True
            if suffix in {".jsx", ".tsx"}:
                has_component_framework = True
                frameworks.add("react")
                signals.add("framework_react")
            if suffix == ".vue":
                has_component_framework = True
                frameworks.add("vue")
                signals.add("framework_vue")
            if suffix == ".svelte":
                has_component_framework = True
                frameworks.add("svelte")
                signals.add("framework_svelte")
            if suffix == ".astro":
                has_component_framework = True
                frameworks.add("astro")
                signals.add("framework_astro")
            if suffix == ".twig":
                has_server_templates = True
                frameworks.add("twig")
                signals.add("framework_twig")
            if suffix == ".php":
                has_server_templates = True
                if lower_name.endswith(".blade.php"):
                    frameworks.add("laravel")
                    signals.add("framework_laravel")
                    signals.add("template_blade")
                else:
                    frameworks.add("php")
                    signals.add("framework_php")

            if "resources/views/" in relative_path or lower_name.endswith(".blade.php"):
                has_server_templates = True
                frameworks.add("laravel")
                signals.add("framework_laravel")

        project_style = self._resolve_project_style(
            has_html_templates=has_html_templates,
            has_server_templates=has_server_templates,
            has_component_framework=has_component_framework,
        )
        if project_style:
            signals.add(f"project_style_{project_style}")

        conflicting_frameworks = sorted(frameworks - {"alpinejs"})
        if len(conflicting_frameworks) >= 2 and (
            has_server_templates or len(set(conflicting_frameworks) & {"react", "vue", "svelte", "sveltekit", "astro", "nextjs", "nuxt"}) >= 2
        ):
            warnings.add(
                "Projeto com multiplos frameworks ou camadas de template; revise a classificacao antes do build.",
            )

        return {
            "framework_hints": sorted(frameworks),
            "project_style": project_style,
            "signals": sorted(signals),
            "warnings": sorted(warnings),
        }

    def _resolve_project_style(
        self,
        *,
        has_html_templates: bool,
        has_server_templates: bool,
        has_component_framework: bool,
    ) -> str:
        if has_server_templates and has_component_framework:
            return "mixed_templates"
        if has_component_framework:
            return "spa"
        if has_server_templates:
            return "server_templates"
        if has_html_templates:
            return "static_html"
        return "unknown"
