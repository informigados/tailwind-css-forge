# Tailwind CSS Forge

[![CI](https://img.shields.io/github/actions/workflow/status/AlexBritoDEV/tailwind-css-forge/backend-ci.yml?branch=main&label=CI)](https://github.com/AlexBritoDEV/tailwind-css-forge/actions/workflows/backend-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#-quick-start)
[![Node.js](https://img.shields.io/badge/Node.js-20%2B-339933?logo=node.js&logoColor=white)](#-quick-start)
[![Desktop](https://img.shields.io/badge/Desktop-Tauri-24C8DB?logo=tauri&logoColor=white)](desktop/README.md)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/informigados/tailwind-css-forge)

🔥 Local build, conversion, packaging, publishing, and desktop-ready toolkit for Tailwind CSS projects across multiple generations.

## ✨ Overview

Tailwind CSS Forge is a local-first system for analyzing, converting, compiling, exporting, and publishing Tailwind CSS projects safely.

It is designed for real-world projects such as:

- plain HTML websites
- multi-page static sites
- simple PHP template projects
- legacy Tailwind setups
- browser/CDN-based Tailwind projects that need a production build pipeline

The project currently ships with a working FastAPI backend, a React/Vite frontend, async builds with progress streaming, ZIP export, secure FTP/SFTP publishing, a Tauri desktop shell, and an installer-ready launcher flow for future packaging.

## 🚀 Current Capabilities

- 🔍 Secure project import into isolated workspaces
- 🧠 Tailwind usage detection from HTML, CSS, config files, and `package.json`
- 🧭 Strategy planning with confidence, signals, and warnings
- 🌍 Real `pt-BR` and `en-US` i18n support
- 🏗️ Real build support for:
  - `play_cdn_conversion`
  - `cdn_legacy`
  - `cli_build`
  - `vite_build`
  - `postcss_build`
  - `legacy_safe_mode`
- 📡 Async build jobs with cancel support and WebSocket progress
- 🧾 JSON, Markdown, and log report generation
- 🧮 History, activity, settings, and report views in the UI
- 📦 ZIP export for successful builds
- 🌐 FTP/FTPS and SFTP publishing from `dist`
- 🔐 Locally encrypted publishing credentials
- 🖥️ Smart launcher with one-click Windows startup
- 🪟 Native Tauri desktop shell with local backend boot
- 🧰 Installer-ready bundle preparation for future PyInstaller or Inno Setup usage

## 🏛️ Architecture

```text
tailwind-css-forge/
├─ backend/     FastAPI API, services, builders, detectors, tests
├─ frontend/    React + Vite web UI
├─ desktop/     Tauri shell and native boot UI
├─ installer/   Installer-ready templates and guides
├─ scripts/     Launcher, bundle preparation, validation helpers
├─ runtime/     Local runtime data during development
└─ build/       Generated distribution artifacts
```

## 🧱 Tech Stack

- Backend: Python 3.12+, FastAPI, SQLite
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Publishing: `ftplib` and `paramiko`
- Security: local encryption for stored publish credentials
- Distribution prep: Python launcher + Windows batch entrypoint + Tauri shell + installer templates

## ⚡ Quick Start

### Requirements

- Python `3.12+`
- Node.js `20+`
- `npm` and `npx` available in `PATH`

### Backend

```bash
cd backend
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

Backend endpoints:

- `http://127.0.0.1:8000/api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server:

- `http://127.0.0.1:5173`

## 🖱️ Smart Local Launcher

Windows one-click entrypoint:

```bat
start_forge.bat
```

Manual launcher:

```bash
python scripts/launch_forge.py
```

Useful launcher commands:

```bash
python scripts/launch_forge.py --prepare-only
python scripts/launch_forge.py --no-browser
python scripts/launch_forge.py --port 8010
python scripts/launch_forge.py --self-check
python scripts/launch_forge.py --self-check --json --assert-ready
```

The launcher can:

- create the backend virtual environment automatically
- install backend dependencies
- install frontend dependencies in source-layout mode
- rebuild the frontend when needed
- start the backend serving the built frontend
- wait for health checks
- open the browser automatically
- validate source-layout or installed-layout readiness through `self-check`

## 📦 Installer-Ready Workflow

The repository is already prepared for future packaging, without generating an executable yet.

```bash
python scripts/render_installer_assets.py
python scripts/prepare_installer_bundle.py --force
python scripts/validate_installer_bundle.py
```

This workflow prepares and validates a staged bundle in `build/installer-bundle/` that is ready for:

- PyInstaller later
- Inno Setup later
- Inno Setup wrapping a future PyInstaller output

Key distribution files:

- `forge-product.json`
- `installer/README.md`
- `installer/inno/forge.iss`
- `installer/inno/forge.version.iss`
- `installer/pyinstaller/forge_launcher.spec`
- `installer/pyinstaller/version_info.txt`

## 🔌 API Flow Available Today

Main workflow:

1. `POST /api/projects/import`
2. `POST /api/projects/{project_id}/analyze`
3. `POST /api/projects/{project_id}/build`
4. `POST /api/builds/{build_id}/cancel`
5. `GET /api/projects/{project_id}/builds`
6. `GET /api/builds/{build_id}`
7. `GET /api/builds/{build_id}/report`
8. `GET /api/builds/{build_id}/log`
9. `POST /api/builds/{build_id}/export/zip`
10. `GET /api/history`
11. `GET /api/history/projects/{project_id}`
12. `GET /api/settings`
13. `PUT /api/settings`
14. `GET /api/projects/{project_id}/publish/profiles`
15. `POST /api/projects/{project_id}/publish/profiles`
16. `PUT /api/projects/{project_id}/publish/profiles/{profile_id}`
17. `DELETE /api/projects/{project_id}/publish/profiles/{profile_id}`
18. `POST /api/projects/{project_id}/publish/test`
19. `POST /api/builds/{build_id}/publish/ftp`
20. `POST /api/builds/{build_id}/publish/sftp`

Example import request:

```bash
curl -X POST http://127.0.0.1:8000/api/projects/import ^
  -H "Content-Type: application/json" ^
  -d "{\"source_path\":\"C:/sites/my-project\"}"
```

## 🛠️ Build Strategies

### `play_cdn_conversion`

Converts modern Tailwind browser/CDN usage into a local production build flow.

### `cdn_legacy`

Handles older CDN-driven Tailwind projects with a safer compatibility-oriented path.

### `cli_build`

Builds projects that already use Tailwind directives such as `@tailwind`.

### `vite_build`

Builds Vite-based projects and materializes final output directly into `dist/`.

### `legacy_safe_mode`

Applies a more conservative compatibility flow for legacy scenarios.

## 🧪 Quality Checks

Backend quality:

```bash
cd backend
python -m ruff check app tests
python -m pytest
```

Frontend production build:

```bash
cd frontend
npm run build
npm run test
npm run test:e2e
```

Desktop shell smoke:

```bash
cd desktop/src-tauri
cargo check
```

Current local validation status:

- backend test suite passing
- frontend build, unit tests, and E2E smoke passing
- installer bundle preparation validated
- staged bundle self-check validated

## 🔐 Security Highlights

- isolated workspaces per imported project
- backup of `src/` before each build
- internal command allowlist for build execution
- `npm install --ignore-scripts` in safety-sensitive flows
- encrypted local storage for publishing credentials
- explicit FTPS mode for FTP publishing
- explicit SFTP host key policy support with local `known_hosts`
- publishing always uses `dist`, never the original project folder

Please read [`SECURITY.md`](SECURITY.md) before reporting vulnerabilities.

## 🖼️ Frontend Status

The web interface already includes:

- health and recent-project dashboard
- project import flow
- analysis view
- async build, live progress, cancel, and ZIP export flow
- settings, report, FTP/SFTP publishing, and history screens
- theme switching and full `pt-BR` / `en-US` language switching

## 🖥️ Desktop Status

The native desktop shell is already present and can:

- boot the local backend
- wait for health before opening the UI
- expose native folder selection
- package the existing web app without changing the backend architecture

## 🗺️ Roadmap Direction

- 🧾 richer history filtering and comparison views
- 📊 broader observability and diagnostics
- 🧳 stronger installer assets and signed release polish
- 🖥️ final desktop packaging and release workflow hardening

## 📚 Additional Guides

- `installer/README.md`
- `desktop/README.md`

## 📝 Changelog

### 2026-03-20 (1.0.0)

- Initial release.

## 🤝 Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## 👥 Authors

- [INformigados](https://github.com/informigados)
- [Alex Brito](https://github.com/alexbritodev)

## 📄 License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
