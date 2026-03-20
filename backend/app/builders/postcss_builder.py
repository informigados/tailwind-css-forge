from __future__ import annotations

from app.builders.cli_builder import CliBuilder
from app.core.build_context import BuildContext
from app.utils.process import ProcessRunner


class PostcssBuilder(CliBuilder):
    def __init__(self, process_runner: ProcessRunner | None = None) -> None:
        super().__init__(process_runner=process_runner)

    def build(self, context: BuildContext, *, minify: bool = True) -> dict:
        result = super().build(context, minify=minify)
        warnings = list(result.get("warnings", []))
        warnings.append(
            "Projeto classificado como PostCSS; o Forge compilou a entrada Tailwind de forma segura sem executar plugins customizados fora da allowlist.",
        )
        result["warnings"] = sorted(set(warnings))
        return result
