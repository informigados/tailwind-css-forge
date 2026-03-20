from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_METADATA_NAME = "forge-product.json"

DEFAULT_PRODUCT_METADATA: dict[str, Any] = {
    "app_name": "Tailwind CSS Forge",
    "app_slug": "tailwind-css-forge",
    "publisher": "Tailwind CSS Forge",
    "company_name": "Tailwind CSS Forge",
    "version": "0.1.0",
    "bundle_format_version": 1,
    "windows": {
        "app_id": "{{7E4B78F2-D29E-4A72-97DA-3576E8650B54}",
        "launcher_bat": "start_forge.bat",
        "pyinstaller_name": "Tailwind CSS Forge Launcher",
        "output_base_filename": "tailwind-css-forge-installer",
    },
}


def load_product_metadata(base_path: Path | None = None) -> dict[str, Any]:
    metadata = deepcopy(DEFAULT_PRODUCT_METADATA)
    metadata_path = find_product_metadata_path(base_path)
    if not metadata_path:
        return metadata

    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    return _deep_merge(metadata, raw)


def find_product_metadata_path(base_path: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if base_path is not None:
        resolved_base = base_path.resolve()
        candidates.extend(
            [
                resolved_base / PRODUCT_METADATA_NAME,
                resolved_base.parent / PRODUCT_METADATA_NAME,
            ],
        )

    candidates.append(REPO_ROOT / PRODUCT_METADATA_NAME)
    seen: set[Path] = set()
    for candidate in candidates:
        resolved_candidate = candidate.resolve()
        if resolved_candidate in seen:
            continue
        seen.add(resolved_candidate)
        if resolved_candidate.exists():
            return resolved_candidate
    return None


def sync_installer_assets(repo_root: Path | None = None) -> dict[str, Path]:
    target_root = (repo_root or REPO_ROOT).resolve()
    metadata = load_product_metadata(target_root)

    inno_version_path = target_root / "installer" / "inno" / "forge.version.iss"
    pyinstaller_version_path = target_root / "installer" / "pyinstaller" / "version_info.txt"

    _write_if_changed(inno_version_path, render_inno_version_include(metadata))
    _write_if_changed(pyinstaller_version_path, render_pyinstaller_version_info(metadata))

    return {
        "inno_version_path": inno_version_path,
        "pyinstaller_version_path": pyinstaller_version_path,
    }


def render_inno_version_include(metadata: dict[str, Any]) -> str:
    windows = metadata["windows"]
    lines = [
        "; Arquivo gerado por scripts/render_installer_assets.py",
        f'#define MyAppName "{_escape_inno(metadata["app_name"])}"',
        f'#define MyAppVersion "{_escape_inno(metadata["version"])}"',
        f'#define MyAppPublisher "{_escape_inno(metadata["publisher"])}"',
        f'#define MyAppExeName "{_escape_inno(windows["launcher_bat"])}"',
        f'#define MyAppId "{_escape_inno(windows["app_id"])}"',
        f'#define MyOutputBaseFilename "{_escape_inno(windows["output_base_filename"])}"',
        "",
    ]
    return "\n".join(lines)


def render_pyinstaller_version_info(metadata: dict[str, Any]) -> str:
    version_tuple = _parse_version_tuple(str(metadata["version"]))
    version_csv = ", ".join(str(part) for part in version_tuple)
    app_name = _escape_pyinstaller(metadata["app_name"])
    publisher = _escape_pyinstaller(metadata["publisher"])
    slug = _escape_pyinstaller(metadata["app_slug"])
    version = _escape_pyinstaller(metadata["version"])
    launcher_name = _escape_pyinstaller(metadata["windows"]["pyinstaller_name"])
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_csv}),
    prodvers=({version_csv}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{publisher}'),
            StringStruct('FileDescription', '{app_name} launcher'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('InternalName', '{launcher_name}'),
            StringStruct('OriginalFilename', '{launcher_name}.exe'),
            StringStruct('ProductName', '{app_name}'),
            StringStruct('ProductVersion', '{version}'),
            StringStruct('Comments', 'Installer-ready launcher for {slug}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _parse_version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [part for part in version.strip().split(".") if part]
    parsed: list[int] = []
    for part in parts[:4]:
        parsed.append(int(part))
    while len(parsed) < 4:
        parsed.append(0)
    return tuple(parsed)


def _escape_inno(value: str) -> str:
    return value.replace('"', '""')


def _escape_pyinstaller(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")
