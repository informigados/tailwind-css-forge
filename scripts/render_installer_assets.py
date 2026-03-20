from __future__ import annotations

from forge_metadata import sync_installer_assets


def main() -> int:
    assets = sync_installer_assets()
    print("Artefatos de instalador atualizados:")
    for label, path in assets.items():
        print(f"- {label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
