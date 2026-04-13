from __future__ import annotations

import json
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPO_ROOT / "build" / "installer-bundle"
LAUNCHER_SELF_CHECK_TIMEOUT_SECONDS = 30


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: {exc.msg} (line {exc.lineno}, column {exc.colno})"
        ) from exc


def _validated_python_executable() -> Path:
    python_executable_path = Path(sys.executable)
    if python_executable_path.is_symlink():
        raise SystemExit("Invalid Python interpreter path: symbolic links are not allowed.")

    python_executable = python_executable_path.resolve()
    if not python_executable.is_file():
        raise SystemExit("Invalid Python interpreter path: expected an existing file.")
    return python_executable


def main() -> int:
    args = parse_args()
    bundle_dir = args.bundle
    validate_bundle(bundle_dir)
    print(f"Bundle valid: {bundle_dir.resolve()}")
    return 0


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Validates the installer bundle of Tailwind CSS Forge.")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=DEFAULT_BUNDLE,
        help="Directory of the installer bundle to validate.",
    )
    return parser.parse_args()


def validate_bundle(bundle_dir: Path) -> None:
    _validate_launcher_self_check(bundle_dir)

    required_files = [
        bundle_dir / "forge-product.json",
        bundle_dir / "installer-manifest.json",
        bundle_dir / "INSTALLER_READY.txt",
        bundle_dir / "start_forge.bat",
        bundle_dir / "app" / "backend" / "pyproject.toml",
        bundle_dir / "app" / "backend" / "app" / "main.py",
        bundle_dir / "app" / "desktop" / "package.json",
        bundle_dir / "app" / "desktop" / "ui" / "index.html",
        bundle_dir / "app" / "desktop" / "src-tauri" / "Cargo.toml",
        bundle_dir / "app" / "desktop" / "src-tauri" / "tauri.conf.json",
        bundle_dir / "app" / "frontend" / "dist" / "index.html",
        bundle_dir / "app" / "scripts" / "launch_forge.py",
        bundle_dir / "app" / "scripts" / "forge_metadata.py",
        bundle_dir / "app" / "installer" / "pyinstaller" / "forge_launcher.spec",
        bundle_dir / "app" / "installer" / "pyinstaller" / "version_info.txt",
        bundle_dir / "app" / "installer" / "inno" / "forge.iss",
        bundle_dir / "app" / "installer" / "inno" / "forge.version.iss",
    ]

    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        missing_list = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(f"Incomplete bundle. Missing files:\n{missing_list}")

    manifest_path = bundle_dir / "installer-manifest.json"
    metadata_path = bundle_dir / "forge-product.json"
    manifest = _load_json_file(manifest_path)
    metadata = _load_json_file(metadata_path)
    if manifest.get("app_name") != "Tailwind CSS Forge":
        raise SystemExit("Invalid manifest: incorrect app_name.")
    if manifest.get("version") != metadata.get("version"):
        raise SystemExit("Invalid manifest: version mismatch with product metadata.")

    forbidden_paths = [
        bundle_dir / "app" / "backend" / "tests",
        bundle_dir / "app" / "backend" / ".venv",
        bundle_dir / "app" / "frontend" / "src",
        bundle_dir / "app" / "frontend" / "node_modules",
        bundle_dir / "app" / "desktop" / "node_modules",
        bundle_dir / "app" / "desktop" / "src-tauri" / "target",
    ]
    forbidden_found = [str(path) for path in forbidden_paths if path.exists()]
    if forbidden_found:
        forbidden_list = "\n".join(f"- {path}" for path in forbidden_found)
        raise SystemExit(f"Bundle contains unexpected content:\n{forbidden_list}")


def _validate_launcher_self_check(bundle_dir: Path) -> None:
    if not bundle_dir.is_dir():
        raise SystemExit("Invalid bundle path: expected an existing directory.")
    if bundle_dir.is_symlink():
        raise SystemExit("Invalid bundle path: symbolic links are not allowed.")

    app_dir = bundle_dir / "app"
    scripts_dir = app_dir / "scripts"
    if app_dir.is_symlink() or scripts_dir.is_symlink():
        raise SystemExit("Invalid launcher path: symbolic links are not allowed in launcher directories.")

    resolved_bundle_dir = bundle_dir.resolve()
    launcher_path = scripts_dir / "launch_forge.py"
    if launcher_path.is_symlink():
        raise SystemExit("Invalid launcher path: symbolic links are not allowed.")
    resolved_launcher_path = launcher_path.resolve()
    launcher_within_bundle = _is_within(resolved_launcher_path, resolved_bundle_dir)
    if not resolved_launcher_path.is_file() or not launcher_within_bundle:
        raise SystemExit("Invalid launcher path: expected launch_forge.py inside the bundle directory.")

    python_executable = _validated_python_executable()
    try:
        completed = subprocess.run(
            [
                str(python_executable),
                str(resolved_launcher_path),
                "--self-check",
                "--json",
                "--assert-ready",
            ],
            cwd=resolved_bundle_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=LAUNCHER_SELF_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            "Launcher self-check failed: process timed out after "
            f"{LAUNCHER_SELF_CHECK_TIMEOUT_SECONDS} seconds."
        ) from exc
    if completed.returncode != 0:
        stderr_output = completed.stderr.strip()
        stdout_output = completed.stdout.strip()
        parts = [
            f"{label}:\n{value}"
            for label, value in (("stderr", stderr_output), ("stdout", stdout_output))
            if value
        ]
        error_output = "\n".join(parts) if parts else "Launcher self-check failed with no output."
        raise SystemExit(f"Launcher self-check failed: {error_output}")

    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Launcher self-check failed: invalid JSON output ({exc.msg}).") from exc
    if not report.get("installed_layout"):
        raise SystemExit(
            "Invalid launcher self-check: installer bundle was not recognized as an installed layout."
        )
    if not report.get("ready"):
        raise SystemExit("Invalid launcher self-check: installer bundle was not marked as ready.")


if __name__ == "__main__":
    raise SystemExit(main())
