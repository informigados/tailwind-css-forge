from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.utils.fs import ensure_directory


def create_zip_from_directory(source_dir: Path, output_zip: Path) -> Path:
    ensure_directory(output_zip.parent)
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_dir():
                continue
            zip_file.write(file_path, arcname=file_path.relative_to(source_dir))
    return output_zip
