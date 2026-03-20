from __future__ import annotations

from pathlib import Path

from app.converters.play_cdn_converter import PlayCdnConverter


def test_stylesheet_href_falls_back_to_root_relative_when_relpath_is_invalid() -> None:
    converter = PlayCdnConverter()

    href = converter._stylesheet_href(
        Path("C:/sites/example/index.html"),
        Path("D:/workspace/assets/css/app.css"),
    )

    assert href == "/assets/css/app.css"
