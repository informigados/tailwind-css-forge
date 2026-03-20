from __future__ import annotations

from pathlib import Path


def test_analyze_project_detects_play_cdn_v4(client, tmp_path: Path) -> None:
    source_path = tmp_path / "cdn-site"
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
          <body class="bg-slate-950 text-white">Forge</body>
        </html>
        """,
        encoding="utf-8",
    )

    import_response = client.post("/api/projects/import", json={"source_path": str(source_path)})
    project_id = import_response.json()["project"]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")

    assert analyze_response.status_code == 201
    analysis = analyze_response.json()["analysis"]
    assert analysis["tailwind_detected"] is True
    assert analysis["strategy_hint"] == "play_cdn_conversion"
    assert analysis["probable_major_version"] == 4
    assert "cdn_browser_script_v4" in analysis["signals"]
    assert analysis["build_plan"]["requires_conversion"] is True
    assert analysis["project_style"] == "static_html"


def test_latest_analysis_returns_persisted_payload(client, tmp_path: Path) -> None:
    source_path = tmp_path / "vite-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "react": "^19.0.0",
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

    import_response = client.post("/api/projects/import", json={"source_path": str(source_path)})
    project_id = import_response.json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")

    latest_response = client.get(f"/api/projects/{project_id}/analysis/latest")

    assert latest_response.status_code == 200
    analysis = latest_response.json()
    assert analysis["strategy_hint"] == "vite_build"
    assert analysis["build_plan"]["ready_for_build"] is True
    assert "react" in analysis["framework_hints"]
    assert analysis["project_style"] == "spa"


def test_analyze_vite_v4_project_without_css_signals_still_prefers_vite_build(client, tmp_path: Path) -> None:
    source_path = tmp_path / "vite-v4-no-css-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "react": "^19.0.0",
            "tailwindcss": "^4.0.0",
            "vite": "^5.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (source_path / "vite.config.ts").write_text("export default {}", encoding="utf-8")

    import_response = client.post("/api/projects/import", json={"source_path": str(source_path)})
    project_id = import_response.json()["project"]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")

    assert analyze_response.status_code == 201
    analysis = analyze_response.json()["analysis"]
    assert analysis["strategy_hint"] == "vite_build"
    assert analysis["probable_major_version"] == 4


def test_analyze_project_detects_postcss_build(client, tmp_path: Path) -> None:
    source_path = tmp_path / "postcss-site"
    source_path.mkdir()
    (source_path / "package.json").write_text(
        """
        {
          "devDependencies": {
            "tailwindcss": "^3.4.0",
            "postcss": "^8.4.0",
            "autoprefixer": "^10.4.0"
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

    import_response = client.post("/api/projects/import", json={"source_path": str(source_path)})
    project_id = import_response.json()["project"]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")

    assert analyze_response.status_code == 201
    analysis = analyze_response.json()["analysis"]
    assert analysis["strategy_hint"] == "postcss_build"
    assert analysis["probable_major_version"] == 3
    assert analysis["build_plan"]["ready_for_build"] is True
    assert analysis["build_plan"]["execution_mode"] == "direct_build"


def test_analyze_project_flags_mixed_tailwind_project(client, tmp_path: Path) -> None:
    source_path = tmp_path / "mixed-site"
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
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
          </head>
          <body class="bg-slate-950 text-white">Mixed</body>
        </html>
        """,
        encoding="utf-8",
    )

    import_response = client.post("/api/projects/import", json={"source_path": str(source_path)})
    project_id = import_response.json()["project"]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")

    assert analyze_response.status_code == 201
    analysis = analyze_response.json()["analysis"]
    assert analysis["strategy_hint"] == "mixed_project"
    assert analysis["build_plan"]["ready_for_build"] is False
    assert analysis["build_plan"]["requires_manual_review"] is True
    assert any("mistura sinais de CDN" in warning for warning in analysis["warnings"])
