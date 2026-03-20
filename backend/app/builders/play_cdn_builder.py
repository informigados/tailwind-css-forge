from __future__ import annotations

import shutil
from pathlib import Path

from app.builders.base_builder import BaseBuilder
from app.converters.play_cdn_converter import PlayCdnConverter
from app.core.build_context import BuildContext
from app.utils.fs import copy_project_tree, ensure_directory
from app.utils.process import ProcessRunner


class PlayCdnBuilder(BaseBuilder):
    def __init__(
        self,
        process_runner: ProcessRunner | None = None,
        converter: PlayCdnConverter | None = None,
        tailwind_version: str = "^4.1.0",
    ) -> None:
        self.process_runner = process_runner or ProcessRunner()
        self.converter = converter or PlayCdnConverter()
        self.tailwind_version = tailwind_version

    def build(self, context: BuildContext, *, minify: bool = True) -> dict:
        command_logs: list[str] = []
        self._emit_progress(context, 15, "Preparing workspace", "Resetting dist and copying source files.")
        self._check_cancelled(context)
        if context.dist_path.exists():
            shutil.rmtree(context.dist_path)

        copy_project_tree(context.src_path, context.dist_path, ())
        self._emit_progress(context, 28, "Converting CDN project", "Extracting Tailwind browser blocks and rewriting references.")
        conversion = self.converter.convert(context)

        toolchain_path = ensure_directory(context.temp_path / "play_cdn_toolchain")
        input_css = toolchain_path / "input.css"
        output_css = ensure_directory(context.dist_path / "assets" / "css") / "app.css"

        self._check_cancelled(context)
        self._write_toolchain_files(toolchain_path, context, conversion["extracted_tailwind_blocks"])
        self._emit_progress(context, 48, "Installing toolchain", "Preparing temporary Tailwind CLI toolchain.")
        install_log = self._install_toolchain(toolchain_path)
        if install_log:
            command_logs.append(install_log)
        self._check_cancelled(context)
        self._emit_progress(context, 76, "Compiling CSS", "Running Tailwind CLI for the converted CDN project.")
        build_log = self._run_tailwind_build(toolchain_path, input_css, output_css, minify=minify)
        if build_log:
            command_logs.append(build_log)
        self._emit_progress(context, 92, "Finalizing output", "Collecting rewritten files and generated assets.")

        outputs = [
            output_css.relative_to(context.workspace_path).as_posix(),
            *[
                (context.dist_path / item).relative_to(context.workspace_path).as_posix()
                for item in conversion["rewritten_files"]
            ],
        ]
        return {
            "status": "success",
            "strategy_used": context.strategy,
            "outputs": outputs,
            "warnings": list(context.analysis.get("warnings", [])),
            "errors": [],
            "command_logs": command_logs,
        }

    def _write_toolchain_files(
        self,
        toolchain_path: Path,
        context: BuildContext,
        extracted_blocks: list[str],
    ) -> None:
        package_json = f"""{{
  "name": "tailwind-css-forge-play-cdn-build",
  "private": true,
  "dependencies": {{
    "tailwindcss": "{self.tailwind_version}",
    "@tailwindcss/cli": "{self.tailwind_version}"
  }}
}}
"""
        input_css_content = [
            '@import "tailwindcss";',
            f'@source "{context.src_path.as_posix()}";',
        ]
        if extracted_blocks:
            input_css_content.append("")
            input_css_content.extend(extracted_blocks)

        (toolchain_path / "package.json").write_text(package_json, encoding="utf-8")
        (toolchain_path / "input.css").write_text("\n".join(input_css_content) + "\n", encoding="utf-8")

    def _install_toolchain(self, toolchain_path: Path) -> str:
        node_modules = toolchain_path / "node_modules"
        if node_modules.exists():
            return "Toolchain cache reused."

        return self.process_runner.run(
            ["npm", "install", "--no-fund", "--no-audit", "--silent"],
            cwd=toolchain_path,
        )

    def _run_tailwind_build(
        self,
        toolchain_path: Path,
        input_css: Path,
        output_css: Path,
        *,
        minify: bool,
    ) -> str:
        command = [
            "npx",
            "@tailwindcss/cli",
            "-i",
            str(input_css),
            "-o",
            str(output_css),
        ]
        if minify:
            command.append("--minify")

        return self.process_runner.run(command, cwd=toolchain_path)
