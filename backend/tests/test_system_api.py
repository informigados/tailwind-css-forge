from __future__ import annotations


def test_system_pick_directory_returns_selected_path(client, monkeypatch) -> None:
    def fake_pick_directory(title: str | None):
        assert title == "Selecionar pasta"
        return True, "C:/Forge/site"

    monkeypatch.setattr("app.api.routes.system.pick_directory", fake_pick_directory)

    response = client.post("/api/system/pick-directory", json={"title": "Selecionar pasta"})

    assert response.status_code == 200
    assert response.json() == {"supported": True, "path": "C:/Forge/site"}


def test_system_pick_directory_reports_unsupported(client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.system.pick_directory", lambda title: (False, None))

    response = client.post("/api/system/pick-directory", json={"title": "Selecionar pasta"})

    assert response.status_code == 200
    assert response.json() == {"supported": False, "path": None}
