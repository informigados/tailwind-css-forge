# 🖥️ Desktop Shell

This directory contains the native Tauri shell for Tailwind CSS Forge.

The current desktop shell target is Windows. The repository keeps the web app and backend cross-platform, but the packaged native shell is intentionally aligned with the Windows distribution flow used by the project.

## 🎯 Purpose

The desktop shell does not replace the Python launcher. It wraps the existing local runtime with:

- a native window
- a native application menu
- secure startup and shutdown of the local backend
- optional native folder picking for project import

## 🧱 Runtime Model

The shell starts `scripts/launch_forge.py` with a dedicated desktop port, waits for the local healthcheck, and then opens the Forge UI inside the Tauri window.

This keeps the existing architecture intact:

- backend remains the local FastAPI engine
- frontend remains served by the backend
- runtime data stays in the same local Forge paths

## 🚀 Development

Install the desktop dependencies:

```bash
cd desktop
npm install
```

Build the frontend first if needed:

```bash
cd ../frontend
npm run build
```

Run the desktop shell in development:

```bash
cd ../desktop
npm run dev
```

Create a debug desktop build:

```bash
npm run build:debug
```

Fast validation for CI or local verification:

```bash
cd src-tauri
cargo check
```

## 📦 Packaging Direction

The recommended distribution path is:

1. prepare the installer-ready bundle
2. build the Tauri desktop executable
3. install the executable alongside the staged `app/` bundle
4. package everything with Inno Setup later

This avoids duplicating the backend runtime logic inside the desktop shell.
