from __future__ import annotations


class BuildPlanFactory:
    def create(self, analysis: dict) -> dict:
        strategy = analysis["strategy_hint"]
        warnings = list(analysis.get("warnings", []))
        project_style = analysis.get("project_style")
        framework_hints = list(analysis.get("framework_hints", []))

        risk_level = "low"
        requires_conversion = False
        ready_for_build = analysis["tailwind_detected"]
        requires_manual_review = False
        execution_mode = "direct_build"
        compatibility_notes: list[str] = []
        pipeline_steps = self._pipeline_steps(strategy)

        if strategy in {"play_cdn_conversion", "cdn_legacy"}:
            risk_level = "medium"
            requires_conversion = True
            execution_mode = "conversion_build"
        elif strategy == "postcss_build":
            risk_level = "medium"
            compatibility_notes.append("Projeto com PostCSS detectado; o Forge priorizara compilacao segura do CSS Tailwind.")
        elif strategy == "legacy_safe_mode":
            risk_level = "medium_high"
            execution_mode = "safe_mode"
            compatibility_notes.append("Pipeline legado detectado; recursos avancados devem ser validados apos o build.")
        elif strategy in {"mixed_project", "unknown_tailwind_style"}:
            risk_level = "high"
            ready_for_build = False
            requires_manual_review = True
            execution_mode = "analysis_only"
        elif strategy in {"analysis_only", "no_tailwind_detected"}:
            risk_level = "high"
            ready_for_build = False
            execution_mode = "analysis_only"

        if project_style == "mixed_templates":
            compatibility_notes.append(
                "Projeto mistura templates de servidor e componentes de frontend; classes dinâmicas exigem revisão.",
            )
            requires_manual_review = True
            risk_level = self._raise_risk(risk_level)
        if framework_hints:
            compatibility_notes.append(f"Frameworks/contextos detectados: {', '.join(framework_hints)}.")
        if warnings:
            risk_level = self._raise_risk(risk_level)

        return {
            "strategy": strategy,
            "requires_conversion": requires_conversion,
            "ready_for_build": ready_for_build,
            "risk_level": risk_level,
            "execution_mode": execution_mode,
            "requires_manual_review": requires_manual_review,
            "pipeline_steps": pipeline_steps,
            "compatibility_notes": compatibility_notes,
            "recommended_action": self._recommended_action(strategy, ready_for_build),
            "warnings": warnings,
        }

    def _recommended_action(self, strategy: str, ready_for_build: bool) -> str:
        if strategy == "play_cdn_conversion":
            return "converter_e_compilar"
        if strategy in {"cli_build", "vite_build", "postcss_build"} and ready_for_build:
            return "compilar"
        if strategy == "legacy_safe_mode":
            return "analisar_antes_de_compilar"
        if strategy in {"mixed_project", "unknown_tailwind_style"}:
            return "revisar_diagnostico"
        if strategy == "no_tailwind_detected":
            return "apenas_analisar"
        return "revisar_diagnostico"

    def _pipeline_steps(self, strategy: str) -> list[str]:
        if strategy == "play_cdn_conversion":
            return ["scan_inputs", "rewrite_cdn_references", "compile_css", "validate_dist"]
        if strategy == "cdn_legacy":
            return ["scan_inputs", "convert_legacy_cdn", "compile_css", "validate_dist"]
        if strategy == "cli_build":
            return ["scan_inputs", "install_dependencies", "run_tailwind_cli", "validate_dist"]
        if strategy == "postcss_build":
            return ["scan_inputs", "prepare_postcss_context", "run_tailwind_cli", "validate_dist"]
        if strategy == "vite_build":
            return ["scan_inputs", "install_dependencies", "run_vite_build", "validate_dist"]
        if strategy == "legacy_safe_mode":
            return ["scan_inputs", "prepare_safe_mode", "run_conservative_build", "validate_dist"]
        return ["scan_inputs", "review_required"]

    def _raise_risk(self, risk_level: str) -> str:
        order = ["low", "medium", "medium_high", "high"]
        try:
            current_index = order.index(risk_level)
        except ValueError:
            return risk_level
        return order[min(current_index + 1, len(order) - 1)]
