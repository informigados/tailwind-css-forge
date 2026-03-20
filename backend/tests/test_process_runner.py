from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.process import ProcessExecutionError, ProcessRunner


def test_process_runner_allows_workspace_bound_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    src_path = workspace / "src"
    dist_path = workspace / "dist"
    src_path.mkdir(parents=True)
    dist_path.mkdir(parents=True)

    input_css = src_path / "app.css"
    output_css = dist_path / "app.css"
    config_path = src_path / "tailwind.config.js"
    input_css.write_text("@tailwind base;", encoding="utf-8")
    config_path.write_text("module.exports = {}", encoding="utf-8")

    runner = ProcessRunner()
    runner._ensure_allowed(
        [
            "npx",
            "tailwindcss",
            "-i",
            str(input_css),
            "-o",
            str(output_css),
            "--config",
            str(config_path),
            "--content",
            "./**/*.{html,js}",
            "--minify",
        ],
        src_path,
    )


def test_process_runner_rejects_paths_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    src_path = workspace / "src"
    dist_path = workspace / "dist"
    src_path.mkdir(parents=True)
    dist_path.mkdir(parents=True)

    outsider = tmp_path / "outside.css"
    outsider.write_text("body{}", encoding="utf-8")
    input_css = src_path / "app.css"
    input_css.write_text("@tailwind base;", encoding="utf-8")

    runner = ProcessRunner()
    with pytest.raises(ProcessExecutionError, match="outside the allowed workspace"):
        runner._ensure_allowed(
            [
                "npx",
                "tailwindcss",
                "-i",
                str(input_css),
                "-o",
                str(outsider),
            ],
            src_path,
        )
