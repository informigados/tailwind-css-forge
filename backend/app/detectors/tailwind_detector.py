from __future__ import annotations

from pathlib import Path

from app.detectors.config_detector import ConfigDetector
from app.detectors.css_detector import CssDetector
from app.detectors.dependency_detector import DependencyDetector
from app.detectors.framework_detector import FrameworkDetector
from app.detectors.html_detector import HtmlDetector
from app.detectors.version_resolver import VersionResolver


class TailwindDetector:
    def __init__(self) -> None:
        self.html_detector = HtmlDetector()
        self.css_detector = CssDetector()
        self.config_detector = ConfigDetector()
        self.dependency_detector = DependencyDetector()
        self.framework_detector = FrameworkDetector()
        self.version_resolver = VersionResolver()

    def analyze(self, source_path: Path) -> dict:
        html_signals, html_warnings = self.html_detector.detect(source_path)
        css_signals, css_warnings = self.css_detector.detect(source_path)
        config_signals, config_warnings = self.config_detector.detect(source_path)
        dependency_signals, dependency_warnings = self.dependency_detector.detect(source_path)
        framework_payload = self.framework_detector.detect(source_path)

        signals = sorted(
            set(
                html_signals
                + css_signals
                + config_signals
                + dependency_signals
                + framework_payload["signals"],
            ),
        )
        warnings = sorted(
            set(
                html_warnings
                + css_warnings
                + config_warnings
                + dependency_warnings
                + framework_payload["warnings"],
            ),
        )
        version_payload = self.version_resolver.resolve(signals, warnings)

        return {
            **version_payload,
            "signals": signals,
            "warnings": version_payload["warnings"],
            "framework_hints": framework_payload["framework_hints"],
            "project_style": framework_payload["project_style"],
        }
