from __future__ import annotations

import shutil

from app.builders.base_builder import BaseBuilder
from app.core.build_context import BuildContext
from app.utils.fs import iter_files
from app.utils.process import ProcessExecutionError, ProcessRunner


class ViteBuilder(BaseBuilder):
    def __init__(self, process_runner: ProcessRunner | None = None) -> None:
        self.process_runner = process_runner or ProcessRunner()

    def build(self, context: BuildContext, *, minify: bool = True) -> dict:
        self._emit_progress(context, 18, "Preparing workspace", "Resetting dist for the Vite build output.")
        self._check_cancelled(context)
        if context.dist_path.exists():
            shutil.rmtree(context.dist_path)

        logs: list[str] = []
        self._emit_progress(context, 42, "Installing dependencies", "Ensuring the Vite project dependencies are present.")
        logs.append(self._install_dependencies(context.src_path))
        self._check_cancelled(context)
        self._emit_progress(context, 78, "Running Vite build", "Executing the project production bundle.")
        logs.append(self._run_vite_build(context, minify=minify))
        self._emit_progress(context, 92, "Finalizing output", "Collecting Vite build artifacts.")

        if not context.dist_path.exists():
            raise ProcessExecutionError(["npx", "vite"], -1, "Vite build did not produce a dist directory.")

        outputs = [path.relative_to(context.workspace_path).as_posix() for path in iter_files(context.dist_path)]
        return {
            "status": "success",
            "strategy_used": context.strategy,
            "outputs": outputs,
            "warnings": list(context.analysis.get("warnings", [])),
            "errors": [],
            "command_logs": [log for log in logs if log],
        }

    def _install_dependencies(self, src_path) -> str:
        if (src_path / "node_modules").exists():
            return "Dependencies already installed."

        return self.process_runner.run(
            ["npm", "install", "--ignore-scripts", "--no-fund", "--no-audit", "--silent"],
            cwd=src_path,
        )

    def _run_vite_build(self, context: BuildContext, *, minify: bool) -> str:
        command = [
            "npx",
            "vite",
            "build",
            "--outDir",
            str(context.dist_path),
            "--emptyOutDir",
        ]
        if not minify:
            command.extend(["--minify", "false"])

        return self.process_runner.run(command, cwd=context.src_path)
