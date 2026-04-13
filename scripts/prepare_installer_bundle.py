from __future__ import annotations

import json
import shutil
from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone
from pathlib import Path

from forge_metadata import load_product_metadata, sync_installer_assets


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "build" / "installer-bundle"


def main() -> int:
    args = parse_args()
    output_dir = args.output.resolve()
    product_metadata = load_product_metadata(REPO_ROOT)
    sync_installer_assets(REPO_ROOT)

    if output_dir.exists() and not args.force:
        raise SystemExit(
            f"Diretorio de bundle ja existe: {output_dir}. Use --force para recriar.",
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)

    stage_root = output_dir
    app_root = stage_root / "app"
    backend_target = app_root / "backend"
    desktop_target = app_root / "desktop"
    frontend_target = app_root / "frontend"
    scripts_target = app_root / "scripts"
    installer_target = app_root / "installer"

    print(f"Preparando bundle de instalacao em {stage_root}")
    copy_backend(REPO_ROOT / "backend", backend_target)
    copy_desktop(REPO_ROOT / "desktop", desktop_target)
    copy_frontend(REPO_ROOT / "frontend", frontend_target)
    copy_tree(REPO_ROOT / "scripts", scripts_target)
    copy_tree(REPO_ROOT / "installer", installer_target)
    copy_file(REPO_ROOT / "start_forge.bat", stage_root / "start_forge.bat")
    copy_file(REPO_ROOT / "forge-product.json", stage_root / "forge-product.json")
    copy_file(REPO_ROOT / "LICENSE", stage_root / "LICENSE")
    copy_file(REPO_ROOT / "README.md", stage_root / "README.md")
    write_manifest(stage_root, product_metadata)
    write_launcher_readme(stage_root, product_metadata)
    print("Bundle installer-ready concluido.")
    return 0


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Prepara o bundle de instalacao do Tailwind CSS Forge.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Diretorio de saida do bundle de instalacao.",
    )
    parser.add_argument("--force", action="store_true", help="Remove e recria o bundle se ele ja existir.")
    return parser.parse_args()


def copy_tree(source: Path, target: Path, *, require_build: bool = False) -> None:
    if require_build and not (source / "dist" / "index.html").exists():
        raise SystemExit("Frontend buildado nao encontrado. Execute `npm run build` em `frontend/` antes.")

    shutil.copytree(source, target, ignore=base_ignore_patterns())


def copy_backend(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=backend_ignore_patterns())


def copy_frontend(source: Path, target: Path) -> None:
    dist_dir = source / "dist"
    if not (dist_dir / "index.html").exists():
        raise SystemExit("Frontend buildado nao encontrado. Execute `npm run build` em `frontend/` antes.")

    target.mkdir(parents=True, exist_ok=True)
    copy_file(source / ".env.example", target / ".env.example")
    copy_tree(dist_dir, target / "dist")


def copy_desktop(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=desktop_ignore_patterns())


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_manifest(stage_root: Path, product_metadata: dict[str, object]) -> None:
    windows = product_metadata["windows"]
    manifest = {
        "app_name": product_metadata["app_name"],
        "app_slug": product_metadata["app_slug"],
        "publisher": product_metadata["publisher"],
        "version": product_metadata["version"],
        "bundle_format_version": product_metadata["bundle_format_version"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "entrypoints": {
            "windows_batch": windows["launcher_bat"],
            "python_launcher": "app/scripts/launch_forge.py",
        },
        "layout": {
            "app_root": "app",
            "backend": "app/backend",
            "frontend": "app/frontend",
            "desktop": "app/desktop",
            "scripts": "app/scripts",
            "installer": "app/installer",
        },
        "installer_targets": {
            "pyinstaller": "installer/pyinstaller/forge_launcher.spec",
            "innosetup": "installer/inno/forge.iss",
        },
        "validation": {
            "self_check_command": [
                "python",
                "app/scripts/launch_forge.py",
                "--self-check",
                "--json",
                "--assert-ready",
            ],
            "validator_script": "app/scripts/validate_installer_bundle.py",
        },
        "installed_runtime_policy": {
            "venv": "user_data_runtime/venv/backend",
            "runtime": "user_data_runtime",
            "frontend": "reuse_prebuilt_dist_only",
        },
    }
    manifest_path = stage_root / "installer-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_launcher_readme(stage_root: Path, product_metadata: dict[str, object]) -> None:
    text = f"""{product_metadata["app_name"]} - Installer Bundle

Este diretorio esta pronto para ser usado por um instalador.

Uso direto:
- execute `start_forge.bat`
- execute `python app/scripts/launch_forge.py --self-check --assert-ready`

Layout esperado:
- `app/backend`
- `app/desktop`
- `app/frontend`
- `app/scripts`

Empacotamento posterior:
- PyInstaller pode transformar o launcher em executavel
- Inno Setup pode instalar este bundle ou o resultado do PyInstaller
"""
    (stage_root / "INSTALLER_READY.txt").write_text(text, encoding="utf-8")


def base_ignore_patterns():
    return shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".ruff_cache",
        ".tmp",
        ".venv",
        "node_modules",
        ".git",
        "runtime",
        "*.db",
        "*.zip",
    )


def backend_ignore_patterns():
    return shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".ruff_cache",
        ".tmp",
        ".venv",
        ".git",
        "runtime",
        "tests",
        "*.egg-info",
        "*.db",
        "*.zip",
    )


def desktop_ignore_patterns():
    return shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".git",
        "node_modules",
        "target",
        "gen",
        "*.db",
        "*.zip",
    )


if __name__ == "__main__":
    raise SystemExit(main())
