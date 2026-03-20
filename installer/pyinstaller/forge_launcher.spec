# Tailwind CSS Forge
# Spec base para empacotar o launcher depois que o bundle estiver pronto.
# Uso esperado futuro:
#   pyinstaller installer/pyinstaller/forge_launcher.spec

import json
from pathlib import Path

spec_dir = Path(__file__).resolve().parent
stage_bundle_root = spec_dir.parents[2]

if (stage_bundle_root / "installer-manifest.json").exists():
    bundle_root = stage_bundle_root
else:
    repo_root = spec_dir.parents[1]
    bundle_root = repo_root / "build" / "installer-bundle"

app_root = bundle_root / "app"
metadata_path = bundle_root / "forge-product.json"
version_file = bundle_root / "app" / "installer" / "pyinstaller" / "version_info.txt"
metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
pyinstaller_name = metadata.get("windows", {}).get("pyinstaller_name", "Tailwind CSS Forge Launcher")

block_cipher = None

a = Analysis(
    [str(app_root / "scripts" / "launch_forge.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=[
        (str(app_root), "app"),
        (str(bundle_root / "start_forge.bat"), "."),
        (str(bundle_root / "forge-product.json"), "."),
        (str(bundle_root / "installer-manifest.json"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=pyinstaller_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    version=str(version_file) if version_file.exists() else None,
)
