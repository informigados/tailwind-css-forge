from __future__ import annotations

import time
from pathlib import Path
from zipfile import ZipFile


def _stub_process_runner(client) -> None:
    def fake_run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
        if command[:2] == ["npm", "install"]:
            (cwd / "node_modules").mkdir(parents=True, exist_ok=True)
            return "npm install stubbed"

        if command[:2] == ["npx", "@tailwindcss/cli"]:
            output_index = command.index("-o") + 1
            output_path = Path(command[output_index])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                ".bg-slate-950{background-color:#020617}.text-white{color:#fff}",
                encoding="utf-8",
            )
            return "tailwind build stubbed"

        if command[:2] == ["npx", "tailwindcss"]:
            output_index = command.index("-o") + 1
            output_path = Path(command[output_index])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                ".text-white{color:#fff}.font-bold{font-weight:700}",
                encoding="utf-8",
            )
            return "tailwind cli build stubbed"

        if command[:2] == ["npx", "vite"]:
            out_dir = Path(command[command.index("--outDir") + 1])
            assets_dir = out_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(
                "<html><body><script type='module' src='/assets/app.js'></script></body></html>",
                encoding="utf-8",
            )
            (assets_dir / "app.js").write_text("console.log('vite');", encoding="utf-8")
            (assets_dir / "app.css").write_text("body{color:#fff}", encoding="utf-8")
            return "vite build stubbed"

        raise AssertionError(f"Unexpected command: {command}")

    client.app.state.build_service.process_runner.run = fake_run


def _stub_slow_process_runner(client, delay_seconds: float = 0.25) -> None:
    def fake_run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
        time.sleep(delay_seconds)

        if command[:2] == ["npm", "install"]:
            (cwd / "node_modules").mkdir(parents=True, exist_ok=True)
            return "npm install stubbed"

        if command[:2] == ["npx", "@tailwindcss/cli"]:
            output_index = command.index("-o") + 1
            output_path = Path(command[output_index])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                ".bg-slate-950{background-color:#020617}.text-white{color:#fff}",
                encoding="utf-8",
            )
            return "tailwind build stubbed"

        raise AssertionError(f"Unexpected command: {command}")

    client.app.state.build_service.process_runner.run = fake_run


def _wait_for_terminal_build(client, build_id: str, timeout_seconds: float = 5.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = client.get(f"/api/builds/{build_id}").json()
        if payload["status"] in {"success", "failed", "cancelled"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Build {build_id} did not finish within {timeout_seconds} seconds.")


def test_build_play_cdn_project_generates_dist_and_report(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "cdn-build-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
            <style type="text/tailwindcss">
              @theme { --color-brand: #2563eb; }
            </style>
          </head>
          <body class="bg-slate-950 text-white">
            <h1>Forge</h1>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 202
    payload = response.json()
    build = payload["build"]
    assert payload["result"] is None

    terminal_build = _wait_for_terminal_build(client, build["id"])
    result = client.get(f"/api/builds/{build['id']}/report").json()

    dist_path = Path(terminal_build["output_path"])
    html_content = (dist_path / "index.html").read_text(encoding="utf-8")
    css_content = (dist_path / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    log_json = client.get(f"/api/builds/{build['id']}/log").json()

    assert terminal_build["status"] == "success"
    assert '<link rel="stylesheet" href="assets/css/app.css">' in html_content
    assert "@tailwindcss/browser" not in html_content
    assert "background-color" in css_content
    assert result["status"] == "success"
    assert result["strategy_used"] == "play_cdn_conversion"
    assert "Build completed successfully." in log_json["log"]
    assert "npm install stubbed" in log_json["log"]
    assert "tailwind build stubbed" in log_json["log"]


def test_export_zip_creates_archive_from_successful_build(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "cdn-export-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <style type="text/tailwindcss">
              @theme { --color-brand: #16a34a; }
            </style>
          </head>
          <body class="text-white">Export</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    build_response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})
    build_id = build_response.json()["build"]["id"]
    _wait_for_terminal_build(client, build_id)

    export_response = client.post(f"/api/builds/{build_id}/export/zip")

    assert export_response.status_code == 201
    export_path = Path(export_response.json()["export"]["output_path"])
    assert export_path.exists()

    with ZipFile(export_path) as zip_file:
        members = set(zip_file.namelist())

    assert "index.html" in members
    assert "assets/css/app.css" in members


def test_export_zip_rejects_oversized_dist(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "cdn-export-limit-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <style type="text/tailwindcss">@theme { --color-brand: #16a34a; }</style>
          </head>
          <body class="text-white">Export limit</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    build_response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})
    build_id = build_response.json()["build"]["id"]
    terminal_build = _wait_for_terminal_build(client, build_id)
    client.app.state.export_service.max_zip_size_bytes = 16
    (Path(terminal_build["output_path"]) / "oversized.bin").write_bytes(b"x" * 32)

    export_response = client.post(f"/api/builds/{build_id}/export/zip")

    assert export_response.status_code == 413
    assert "limite de exportacao ZIP" in export_response.json()["detail"]


def test_build_cli_project_generates_compiled_css(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "cli-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "tailwindcss": "^3.4.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (source_path / "tailwind.config.js").write_text(
        "module.exports = { content: ['./index.html'], theme: { extend: {} }, plugins: [] }",
        encoding="utf-8",
    )
    (source_path / "styles.css").write_text(
        "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
        encoding="utf-8",
    )
    (source_path / "index.html").write_text(
        "<html><head><link rel='stylesheet' href='styles.css'></head><body class='text-white font-bold'>CLI</body></html>",
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 202
    build_id = response.json()["build"]["id"]
    terminal_build = _wait_for_terminal_build(client, build_id)
    css_path = Path(terminal_build["output_path"]) / "styles.css"
    assert css_path.exists()
    assert "font-weight" in css_path.read_text(encoding="utf-8")


def test_build_vite_project_generates_dist_bundle(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "vite-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "tailwindcss": "^4.0.0",
            "@tailwindcss/vite": "^4.0.0",
            "vite": "^5.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (source_path / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (source_path / "app.css").write_text('@import "tailwindcss";', encoding="utf-8")

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 202
    build_id = response.json()["build"]["id"]
    terminal_build = _wait_for_terminal_build(client, build_id)
    dist_path = Path(terminal_build["output_path"])
    assert (dist_path / "index.html").exists()
    assert (dist_path / "assets" / "app.css").exists()


def test_build_legacy_project_runs_in_safe_mode(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "legacy-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "postcss": "^8.0.0",
            "autoprefixer": "^10.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (source_path / "postcss.config.js").write_text("module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } }", encoding="utf-8")
    (source_path / "tailwind.config.js").write_text(
        "module.exports = { content: ['./index.html'], theme: { extend: {} }, plugins: [] }",
        encoding="utf-8",
    )
    (source_path / "legacy.css").write_text(
        "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
        encoding="utf-8",
    )
    (source_path / "index.html").write_text(
        "<html><head><link rel='stylesheet' href='legacy.css'></head><body class='text-white'>Legacy</body></html>",
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    analysis = client.post(f"/api/projects/{project_id}/analyze").json()["analysis"]

    assert analysis["strategy_hint"] == "legacy_safe_mode"

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 202
    build_id = response.json()["build"]["id"]
    terminal_build = _wait_for_terminal_build(client, build_id)
    report = client.get(f"/api/builds/{build_id}/report").json()
    assert "modo conservador" in " ".join(report["warnings"])
    assert (Path(terminal_build["output_path"]) / "legacy.css").exists()


def test_build_postcss_project_generates_compiled_css(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "postcss-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "tailwindcss": "^3.4.0",
            "postcss": "^8.0.0",
            "autoprefixer": "^10.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (source_path / "postcss.config.js").write_text(
        "module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } }",
        encoding="utf-8",
    )
    (source_path / "tailwind.config.js").write_text(
        "module.exports = { content: ['./index.html'], theme: { extend: {} }, plugins: [] }",
        encoding="utf-8",
    )
    (source_path / "styles.css").write_text(
        "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
        encoding="utf-8",
    )
    (source_path / "index.html").write_text(
        "<html><head><link rel='stylesheet' href='styles.css'></head><body class='text-white'>PostCSS</body></html>",
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    analysis = client.post(f"/api/projects/{project_id}/analyze").json()["analysis"]

    assert analysis["strategy_hint"] == "postcss_build"

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 202
    build_id = response.json()["build"]["id"]
    terminal_build = _wait_for_terminal_build(client, build_id)
    report = client.get(f"/api/builds/{build_id}/report").json()

    assert terminal_build["status"] == "success"
    assert (Path(terminal_build["output_path"]) / "styles.css").exists()
    assert "PostCSS" in " ".join(report["warnings"])


def test_build_rejects_unimplemented_strategy(client, tmp_path: Path) -> None:
    source_path = tmp_path / "unsupported-site"
    source_path.mkdir()
    (source_path / "index.html").write_text("<html><body>No Tailwind</body></html>", encoding="utf-8")

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")

    response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})

    assert response.status_code == 409


def test_cancel_build_marks_job_cancelled(client, tmp_path: Path) -> None:
    _stub_slow_process_runner(client)

    source_path = tmp_path / "cancel-build-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
          </head>
          <body class="bg-slate-950 text-white">Cancel</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    start_response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})
    build_id = start_response.json()["build"]["id"]

    cancel_response = client.post(f"/api/builds/{build_id}/cancel")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["build"]["cancel_requested"] is True

    terminal_build = _wait_for_terminal_build(client, build_id)
    log_payload = client.get(f"/api/builds/{build_id}/log").json()

    assert terminal_build["status"] == "cancelled"
    assert "cancelled" in log_payload["log"].lower()


def test_build_websocket_streams_progress_until_terminal_status(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "ws-build-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
          </head>
          <body class="bg-slate-950 text-white">Socket</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    start_response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})
    build_id = start_response.json()["build"]["id"]

    statuses: list[str] = []
    progress_values: list[int] = []
    with client.websocket_connect(f"/ws/builds/{build_id}") as websocket:
        while True:
            payload = websocket.receive_json()
            statuses.append(payload["status"])
            progress_values.append(payload["progress_percent"])
            assert payload["type"] == "progress"
            assert payload["build_id"] == build_id
            if payload["status"] in {"success", "failed", "cancelled"}:
                break

    assert statuses
    assert statuses[-1] == "success"
    assert max(progress_values) == 100


def test_progress_updates_do_not_overwrite_terminal_status(client, tmp_path: Path) -> None:
    _stub_process_runner(client)

    source_path = tmp_path / "terminal-status-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
          </head>
          <body class="bg-slate-950 text-white">Terminal</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    start_response = client.post(f"/api/projects/{project_id}/build", json={"minify": True})
    build_id = start_response.json()["build"]["id"]

    terminal_build = _wait_for_terminal_build(client, build_id)
    client.app.state.build_service._update_progress(
        build_id,
        percent=20,
        step="Unexpected update",
        message="This should be ignored.",
        status="running",
    )
    persisted_build = client.get(f"/api/builds/{build_id}").json()

    assert terminal_build["status"] == "success"
    assert persisted_build["status"] == "success"
    assert persisted_build["progress_percent"] == 100
