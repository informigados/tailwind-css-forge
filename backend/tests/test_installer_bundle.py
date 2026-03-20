from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "prepare_installer_bundle.py"
RENDER_SCRIPT = REPO_ROOT / "scripts" / "render_installer_assets.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_installer_bundle.py"


def test_render_installer_assets() -> None:
    render = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert render.returncode == 0, render.stderr or render.stdout
    assert (REPO_ROOT / "installer" / "inno" / "forge.version.iss").exists()
    assert (REPO_ROOT / "installer" / "pyinstaller" / "version_info.txt").exists()


def test_prepare_and_validate_installer_bundle(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "installer-bundle"
    frontend_build = subprocess.run(
        ["npm", "run", "build"],
        cwd=REPO_ROOT / "frontend",
        check=False,
        capture_output=True,
        text=True,
        shell=True,
    )
    assert frontend_build.returncode == 0, frontend_build.stderr or frontend_build.stdout

    prepare = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--output", str(bundle_dir), "--force"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert prepare.returncode == 0, prepare.stderr or prepare.stdout

    validate = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--bundle", str(bundle_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0, validate.stderr or validate.stdout

    manifest = json.loads((bundle_dir / "installer-manifest.json").read_text(encoding="utf-8"))
    assert (bundle_dir / "app" / "frontend" / "dist" / "index.html").exists()
    assert (bundle_dir / "forge-product.json").exists()
    assert (bundle_dir / "app" / "installer" / "inno" / "forge.version.iss").exists()
    assert (bundle_dir / "app" / "installer" / "pyinstaller" / "version_info.txt").exists()
    assert not (bundle_dir / "app" / "frontend" / "src").exists()
    assert not (bundle_dir / "app" / "backend" / "tests").exists()
    assert manifest["version"] == "0.1.0"

    self_check = subprocess.run(
        [
            sys.executable,
            str(bundle_dir / "app" / "scripts" / "launch_forge.py"),
            "--self-check",
            "--json",
            "--assert-ready",
        ],
        cwd=bundle_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    assert self_check.returncode == 0, self_check.stderr or self_check.stdout
    report = json.loads(self_check.stdout)
    assert report["installed_layout"] is True
    assert report["ready"] is True


def test_source_launcher_prepare_only() -> None:
    launcher = REPO_ROOT / "scripts" / "launch_forge.py"
    completed = subprocess.run(
        [sys.executable, str(launcher), "--prepare-only"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "Preparacao concluida com sucesso." in completed.stdout
