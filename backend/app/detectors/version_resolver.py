from __future__ import annotations


class VersionResolver:
    def resolve(self, signals: list[str], warnings: list[str]) -> dict:
        signal_set = set(signals)
        resolved_warnings = list(warnings)

        strategy_hint = "analysis_only"
        probable_major_version: int | None = None
        confidence = 0.18

        has_play_cdn = "cdn_browser_script_v4" in signal_set
        has_legacy_cdn = "cdn_tailwindcss_com" in signal_set
        has_vite = self._has_any_prefix(signal_set, "config_vite_") or "dependency_tailwindcss_vite" in signal_set
        has_postcss = self._has_any_prefix(signal_set, "config_postcss_") or "dependency_postcss" in signal_set
        has_tailwind_config = self._has_any_prefix(signal_set, "config_tailwind_")
        has_v4_css = bool({"css_import_tailwindcss", "css_theme_block", "css_source_directive"} & signal_set)
        has_v3_css = bool(
            {"css_tailwind_base", "css_tailwind_components", "css_tailwind_utilities"} & signal_set,
        )
        has_tailwind_dependency = "dependency_tailwindcss" in signal_set

        probable_major_version = self._infer_major_version(signal_set)

        mixed_reasons: list[str] = []
        if (has_play_cdn or has_legacy_cdn) and (has_vite or has_postcss or has_tailwind_config or has_tailwind_dependency):
            mixed_reasons.append("Projeto mistura sinais de CDN com pipeline local de build.")
        if has_v4_css and has_v3_css:
            mixed_reasons.append("Projeto mistura sintaxe moderna do Tailwind v4 com diretivas classicas.")
        if has_vite and has_postcss and not has_tailwind_dependency:
            mixed_reasons.append("Projeto combina Vite e PostCSS sem dependencia de Tailwind claramente versionada.")

        if mixed_reasons:
            strategy_hint = "mixed_project"
            confidence = 0.52
            resolved_warnings.extend(mixed_reasons)
        elif has_play_cdn:
            strategy_hint = "play_cdn_conversion"
            probable_major_version = 4
            confidence = 0.93
        elif has_vite and (
            has_v4_css
            or "dependency_tailwindcss_vite" in signal_set
            or (has_tailwind_dependency and probable_major_version == 4)
        ):
            strategy_hint = "vite_build"
            probable_major_version = probable_major_version or (4 if has_v4_css else 3)
            confidence = 0.89
        elif has_postcss and has_tailwind_dependency and (has_v3_css or has_v4_css):
            strategy_hint = "postcss_build"
            probable_major_version = probable_major_version or (4 if has_v4_css else 3)
            confidence = 0.81
        elif has_postcss and (has_v3_css or has_tailwind_config):
            strategy_hint = "legacy_safe_mode"
            probable_major_version = probable_major_version or 2
            confidence = 0.67
            resolved_warnings.append(
                "Projeto com PostCSS legado ou incompleto; o Forge usará modo conservador para evitar regressão.",
            )
        elif has_v3_css or (has_tailwind_config and has_tailwind_dependency):
            strategy_hint = "cli_build"
            probable_major_version = probable_major_version or 3
            confidence = 0.81
        elif has_legacy_cdn:
            strategy_hint = "cdn_legacy"
            probable_major_version = probable_major_version or 3
            confidence = 0.74
        elif has_tailwind_dependency and probable_major_version == 3:
            strategy_hint = "cli_build"
            probable_major_version = 3
            confidence = 0.62
        elif signal_set:
            strategy_hint = "unknown_tailwind_style"
            confidence = 0.34
            resolved_warnings.append(
                "Tailwind foi detectado, mas o estilo do projeto não corresponde a uma estratégia suportada com segurança.",
            )

        if resolved_warnings:
            confidence = max(0.0, round(confidence - 0.08, 2))

        tailwind_detected = bool(signal_set)
        if not tailwind_detected:
            strategy_hint = "no_tailwind_detected"
            confidence = 0.0

        return {
            "tailwind_detected": tailwind_detected,
            "strategy_hint": strategy_hint,
            "probable_major_version": probable_major_version,
            "confidence": confidence,
            "warnings": sorted(set(resolved_warnings)),
        }

    def _has_any_prefix(self, signal_set: set[str], prefix: str) -> bool:
        return any(signal.startswith(prefix) for signal in signal_set)

    def _infer_major_version(self, signal_set: set[str]) -> int | None:
        for major_version in (4, 3, 2, 1):
            if f"dependency_tailwindcss_major_{major_version}" in signal_set:
                return major_version

        if "dependency_tailwindcss_vite" in signal_set or "css_import_tailwindcss" in signal_set:
            return 4
        if {"css_tailwind_base", "css_tailwind_components", "css_tailwind_utilities"} & signal_set:
            return 3
        if "cdn_browser_script_v4" in signal_set:
            return 4
        if "cdn_tailwindcss_com" in signal_set:
            return 3
        return None
