from __future__ import annotations

import json
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPO_ROOT / "build" / "installer-bundle"


def main() -> int:
    args = parse_args()
    bundle_dir = args.bundle.resolve()
    validate_bundle(bundle_dir)
    print(f"Bundle valid: {bundle_dir}")
    return 0


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Validates the installer-ready bundle of Tailwind CSS Forge.")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=DEFAULT_BUNDLE,
        help="Directory of the staged bundle to validate.",
    )
    return parser.parse_args()


def validate_bundle(bundle_dir: Path) -> None:
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

    manifest = json.loads((bundle_dir / "installer-manifest.json").read_text(encoding="utf-8"))
    metadata = json.loads((bundle_dir / "forge-product.json").read_text(encoding="utf-8"))
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

    _validate_launcher_self_check(bundle_dir)


def _validate_launcher_self_check(bundle_dir: Path) -> None:
    launcher_path = bundle_dir / "app" / "scripts" / "launch_forge.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(launcher_path),
            "--self-check",
            "--json",
            "--assert-ready",
        ],
        cwd=bundle_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "Launcher self-check failed: "
            f"{completed.stderr.strip() or completed.stdout.strip()}",
        )

    report = json.loads(completed.stdout)
    if not report.get("installed_layout"):
        raise SystemExit("Invalid launcher self-check: staged bundle was not recognized as an installed layout.")
    if not report.get("ready"):
        raise SystemExit("Invalid launcher self-check: staged bundle was not marked as ready.")


if __name__ == "__main__":
    raise SystemExit(main())
