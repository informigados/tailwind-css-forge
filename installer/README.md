# 📦 Installer-Ready Workflow

This directory does not package the system by itself. It prepares the project for packaging later.

## 🎯 Goal

Enable two future packaging paths without rework:

- 🧰 PyInstaller on top of the launcher
- 🪟 Inno Setup on top of the staged bundle or on top of a future PyInstaller output
- 🖥️ Tauri desktop shell installed alongside the staged `app/` runtime

## ✅ Recommended Order

### 1. Sync generated installer assets

```bash
python scripts/render_installer_assets.py
```

### 2. Build the production frontend

```bash
cd frontend
npm run build
```

### 3. Prepare the installer-ready bundle

```bash
python scripts/prepare_installer_bundle.py --force
```

### 4. Validate the staged bundle

```bash
python scripts/validate_installer_bundle.py
```

### 5. Choose the packaging step later

- `installer/pyinstaller/forge_launcher.spec`
- `installer/inno/forge.iss`
- `desktop/` for the native shell build

## 🧭 Central Product Metadata

`forge-product.json` is the single source of truth for:

- product name
- version
- publisher
- Windows App ID and output naming

Automatically generated derived files:

- `installer/inno/forge.version.iss`
- `installer/pyinstaller/version_info.txt`

## 🔁 Template Portability

The installer templates were prepared to work in two scenarios:

- directly from the repository, consuming `build/installer-bundle/`
- directly from inside the staged bundle, without depending on the repository layout

## 🗂️ Staged Bundle Result

The generated staged bundle looks like this:

```text
build/installer-bundle/
├─ app/
│  ├─ backend/
│  ├─ desktop/
│  ├─ frontend/
│  ├─ installer/
│  └─ scripts/
├─ forge-product.json
├─ start_forge.bat
├─ installer-manifest.json
└─ INSTALLER_READY.txt
```

## 🛡️ Validation Notes

The staged bundle validation currently checks:

- required files are present
- forbidden development-only content is excluded
- metadata and manifest stay consistent
- the copied launcher passes a real `self-check` in installed-layout mode

## 🚫 What This Step Does Not Do Yet

This workflow does not:

- generate an executable yet
- run PyInstaller yet
- build an Inno Setup installer yet
- replace the current launcher or desktop shell workflow

It only makes the project ready for those steps later, with a cleaner and safer distribution foundation.
