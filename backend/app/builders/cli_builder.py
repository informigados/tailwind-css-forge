from __future__ import annotations

import shutil
from pathlib import Path

from app.builders.base_builder import BaseBuilder
from app.core.build_context import BuildContext
from app.utils.fs import copy_project_tree, iter_files
from app.utils.process import ProcessExecutionError, ProcessRunner


class CliBuilder(BaseBuilder):
    content_glob = "./**/*.{html,js,ts,jsx,tsx,vue,svelte,php,twig}"

    def __init__(self, process_runner: ProcessRunner | None = None) -> None:
        self.process_runner = process_runner or ProcessRunner()

    def build(self, context: BuildContext, *, minify: bool = True) -> dict:
        self._emit_progress(context, 15, "Preparing workspace", "Resetting dist and copying project source.")
        self._check_cancelled(context)
        if context.dist_path.exists():
            shutil.rmtree(context.dist_path)

        copy_project_tree(context.src_path, context.dist_path, ())
        self._emit_progress(context, 28, "Locating Tailwind input", "Searching for the CSS entry file with Tailwind directives.")
        input_css = self._locate_input_css(context.src_path)
        output_css = context.dist_path / input_css.relative_to(context.src_path)
        output_css.parent.mkdir(parents=True, exist_ok=True)

        logs: list[str] = []
        self._check_cancelled(context)
        self._emit_progress(context, 48, "Installing dependencies", "Ensuring project dependencies are installed.")
        logs.append(self._install_dependencies(context.src_path))
        self._check_cancelled(context)
        self._emit_progress(context, 78, "Compiling CSS", "Running Tailwind CLI for the project entry CSS.")
        logs.append(self._run_tailwind_build(context.src_path, input_css, output_css, minify=minify))
        self._emit_progress(context, 92, "Finalizing output", "Scanning generated artifacts in dist.")

        outputs = [path.relative_to(context.workspace_path).as_posix() for path in iter_files(context.dist_path)]
        return {
            "status": "success",
            "strategy_used": context.strategy,
            "outputs": outputs,
            "warnings": list(context.analysis.get("warnings", [])),
            "errors": [],
            "command_logs": [log for log in logs if log],
        }

    def _locate_input_css(self, src_path: Path) -> Path:
        for file_path in iter_files(src_path):
            if file_path.suffix.lower() not in {".css", ".pcss"}:
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if any(
                marker in content
                for marker in ("@tailwind base;", "@tailwind components;", "@tailwind utilities;")
            ):
                return file_path

        raise ProcessExecutionError(["npx", "tailwindcss"], -1, "No Tailwind CSS input file was found.")

    def _install_dependencies(self, src_path: Path) -> str:
        package_json_path = src_path / "package.json"
        if not package_json_path.exists():
            raise ProcessExecutionError(["npm", "install"], -1, "package.json was not found in the project source.")

        if (src_path / "node_modules").exists():
            return "Dependencies already installed."

        return self.process_runner.run(
            ["npm", "install", "--ignore-scripts", "--no-fund", "--no-audit", "--silent"],
            cwd=src_path,
        )

    def _run_tailwind_build(
        self,
        src_path: Path,
        input_css: Path,
        output_css: Path,
        *,
        minify: bool,
    ) -> str:
        command = [
            "npx",
            "tailwindcss",
            "-i",
            str(input_css),
            "-o",
            str(output_css),
            "--content",
            self.content_glob,
        ]
        config_path = self._find_config_path(src_path)
        if config_path is not None:
            command.extend(["--config", str(config_path)])
        if minify:
            command.append("--minify")

        return self.process_runner.run(command, cwd=src_path)

    def _find_config_path(self, src_path: Path) -> Path | None:
        for file_name in ("tailwind.config.js", "tailwind.config.cjs", "tailwind.config.ts"):
            candidate = src_path / file_name
            if candidate.exists():
                return candidate
        return None
