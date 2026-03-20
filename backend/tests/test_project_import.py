from __future__ import annotations

from pathlib import Path


def test_import_project_creates_workspace(client, tmp_path: Path) -> None:
    source_path = tmp_path / "simple-site"
    source_path.mkdir()
    (source_path / "index.html").write_text("<html><body>Hello</body></html>", encoding="utf-8")
    (source_path / "styles.css").write_text("body { color: red; }", encoding="utf-8")

    response = client.post(
        "/api/projects/import",
        json={"source_path": str(source_path)},
    )

    assert response.status_code == 201
    payload = response.json()["project"]
    workspace_path = Path(payload["workspace_path"])
    assert (workspace_path / "original_snapshot" / "index.html").exists()
    assert (workspace_path / "src" / "styles.css").exists()
    assert (workspace_path / "meta" / "project_meta.json").exists()


def test_import_rejects_runtime_folder_overlap(client, tmp_path: Path) -> None:
    response = client.post(
        "/api/projects/import",
        json={"source_path": str(tmp_path)},
    )

    assert response.status_code == 400


def test_import_rejects_missing_path(client, tmp_path: Path) -> None:
    response = client.post(
        "/api/projects/import",
        json={"source_path": str(tmp_path / "missing-project")},
    )

    assert response.status_code == 400
