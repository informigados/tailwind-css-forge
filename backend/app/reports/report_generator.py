from __future__ import annotations

from app.core.build_context import BuildContext
from app.utils.fs import write_json
from app.utils.time import utc_now_iso


class ReportGenerator:
    def generate(self, context: BuildContext, result: dict, log_output: str) -> dict:
        json_path = context.reports_path / f"{context.build_id}-report.json"
        markdown_path = context.reports_path / f"{context.build_id}-report.md"
        log_path = context.reports_path / f"{context.build_id}.log"

        payload = {
            "generated_at": utc_now_iso(),
            "project_id": context.project_id,
            "build_id": context.build_id,
            "strategy_used": result["strategy_used"],
            "status": result["status"],
            "analysis": context.analysis,
            "build_plan": context.build_plan,
            "outputs": result.get("outputs", []),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
            "duration_ms": result.get("duration_ms", 0),
        }
        write_json(json_path, payload)
        markdown_path.write_text(self._to_markdown(payload), encoding="utf-8")
        log_path.write_text(log_output.strip() + "\n", encoding="utf-8")

        return {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "log_path": str(log_path),
        }

    def _to_markdown(self, payload: dict) -> str:
        lines = [
            "# Build Report",
            "",
            f"- Project ID: `{payload['project_id']}`",
            f"- Build ID: `{payload['build_id']}`",
            f"- Strategy: `{payload['strategy_used']}`",
            f"- Status: `{payload['status']}`",
            f"- Duration: `{payload['duration_ms']} ms`",
            "",
            "## Outputs",
        ]
        outputs = payload.get("outputs", [])
        lines.extend(f"- `{item}`" for item in outputs) if outputs else lines.append("- None")
        lines.extend(["", "## Warnings"])
        warnings = payload.get("warnings", [])
        lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
        lines.extend(["", "## Errors"])
        errors = payload.get("errors", [])
        lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
        return "\n".join(lines) + "\n"
