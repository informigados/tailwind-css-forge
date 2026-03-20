from __future__ import annotations

import json
import shutil
import threading
import uuid
from pathlib import Path
from time import perf_counter

from fastapi import HTTPException, status

from app.builders.cli_builder import CliBuilder
from app.builders.legacy_builder import LegacyBuilder
from app.builders.play_cdn_builder import PlayCdnBuilder
from app.builders.postcss_builder import PostcssBuilder
from app.builders.vite_builder import ViteBuilder
from app.core.build_context import BuildContext
from app.db.session import Database
from app.reports.report_generator import ReportGenerator
from app.schemas.build import BuildSummary
from app.services.analysis_service import AnalysisService
from app.services.project_service import ProjectService
from app.utils.process import ProcessExecutionError, ProcessRunner
from app.utils.time import utc_now_iso


class BuildCancelledError(RuntimeError):
    pass


class BuildService:
    terminal_statuses = {"success", "failed", "cancelled"}

    def __init__(
        self,
        database: Database,
        project_service: ProjectService,
        analysis_service: AnalysisService,
        report_generator: ReportGenerator | None = None,
        process_runner: ProcessRunner | None = None,
    ) -> None:
        self.database = database
        self.project_service = project_service
        self.analysis_service = analysis_service
        self.report_generator = report_generator or ReportGenerator()
        self.process_runner = process_runner or ProcessRunner()
        self._threads: dict[str, threading.Thread] = {}
        self._threads_lock = threading.Lock()

    def start_build(self, project_id: str, *, minify: bool = True) -> BuildSummary:
        project = self.project_service.get_project(project_id)
        analysis = self.analysis_service.get_latest_analysis(project_id)
        build_plan = analysis.build_plan

        if not build_plan.get("ready_for_build"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O projeto ainda não está pronto para build; revise o diagnóstico antes de continuar.",
            )

        if analysis.strategy_hint not in {
            "play_cdn_conversion",
            "cdn_legacy",
            "cli_build",
            "postcss_build",
            "vite_build",
            "legacy_safe_mode",
        }:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Estratégia `{analysis.strategy_hint}` ainda não foi implementada no builder real.",
            )

        running_build = self._get_running_build_for_project(project_id)
        if running_build:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um build em andamento para este projeto: {running_build.id}.",
            )

        build_id = f"build_{uuid.uuid4().hex[:12]}"
        started_at = utc_now_iso()
        self.database.execute(
            """
            INSERT INTO builds (
                id, project_id, analysis_id, strategy_used, status, progress_percent,
                current_step, current_message, cancel_requested, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                project_id,
                analysis.id,
                analysis.strategy_hint,
                "queued",
                0,
                "Queued",
                "Build aguardando início.",
                0,
                started_at,
            ),
        )

        worker = threading.Thread(
            target=self._run_build_job,
            args=(build_id, project_id, analysis.id, analysis.strategy_hint, bool(minify), project.workspace_path),
            daemon=True,
            name=f"forge-build-{build_id}",
        )
        with self._threads_lock:
            self._threads[build_id] = worker
        worker.start()
        return self.get_build(build_id)

    def cancel_build(self, build_id: str) -> BuildSummary:
        build = self.get_build(build_id)
        if build.status in self.terminal_statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível cancelar um build que já foi finalizado.",
            )

        self.database.execute(
            """
            UPDATE builds
            SET cancel_requested = 1, current_message = ?
            WHERE id = ?
            """,
            ("Cancelamento solicitado pelo usuário.", build_id),
        )
        return self.get_build(build_id)

    def list_project_builds(self, project_id: str) -> list[BuildSummary]:
        self.project_service.get_project(project_id)
        rows = self.database.fetch_all(
            """
            SELECT id, project_id, analysis_id, strategy_used, status, progress_percent,
                   current_step, current_message, cancel_requested, started_at, finished_at,
                   duration_ms, output_path, report_path, log_path
            FROM builds
            WHERE project_id = ?
            ORDER BY started_at DESC
            """,
            (project_id,),
        )
        return [self._to_build_summary(row) for row in rows]

    def get_build(self, build_id: str) -> BuildSummary:
        row = self.database.fetch_one(
            """
            SELECT id, project_id, analysis_id, strategy_used, status, progress_percent,
                   current_step, current_message, cancel_requested, started_at, finished_at,
                   duration_ms, output_path, report_path, log_path
            FROM builds
            WHERE id = ?
            """,
            (build_id,),
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build não encontrado.")
        return self._to_build_summary(row)

    def get_build_report(self, build_id: str) -> dict:
        build = self.get_build(build_id)
        if not build.report_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado.")

        json_path = Path(build.report_path).with_suffix(".json")
        if not json_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório JSON não encontrado.")
        return json.loads(json_path.read_text(encoding="utf-8"))

    def get_build_log(self, build_id: str) -> dict:
        build = self.get_build(build_id)
        if build.log_path:
            log_path = Path(build.log_path)
            if not log_path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de log não encontrado.")
            return {"build_id": build_id, "log": log_path.read_text(encoding="utf-8")}

        status_line = build.current_message or "Nenhum log disponível ainda."
        return {"build_id": build_id, "log": f"[{build.status}] {status_line}\n"}

    def _run_build_job(
        self,
        build_id: str,
        project_id: str,
        analysis_id: str,
        strategy_hint: str,
        minify: bool,
        workspace_path_raw: str,
    ) -> None:
        workspace_path = Path(workspace_path_raw)
        analysis = self.analysis_service.get_latest_analysis(project_id)
        build_plan = analysis.build_plan
        start_clock = perf_counter()
        context = BuildContext(
            project_id=project_id,
            build_id=build_id,
            workspace_path=workspace_path,
            src_path=workspace_path / "src",
            dist_path=workspace_path / "dist",
            temp_path=workspace_path / "temp" / build_id,
            reports_path=workspace_path / "reports",
            backups_path=workspace_path / "backups",
            analysis=analysis.model_dump(),
            build_plan=build_plan,
            strategy=strategy_hint,
            progress_callback=lambda percent, step, message: self._update_progress(
                build_id,
                percent=percent,
                step=step,
                message=message,
            ),
            cancel_check=lambda: self._ensure_not_cancelled(build_id),
        )
        context.temp_path.mkdir(parents=True, exist_ok=True)
        context.reports_path.mkdir(parents=True, exist_ok=True)
        context.backups_path.mkdir(parents=True, exist_ok=True)

        self._update_progress(
            build_id,
            status="running",
            percent=5,
            step="Starting build",
                message="Preparando workspace e criando backup antes do build.",
        )

        try:
            self._ensure_not_cancelled(build_id)
            self._create_backup(context)
            self._update_progress(
                build_id,
                percent=10,
                step="Backup complete",
                message="Backup de src concluído com sucesso.",
            )

            builder = self._select_builder(strategy_hint)
            builder_result = builder.build(context, minify=minify)
            duration_ms = int((perf_counter() - start_clock) * 1000)
            builder_result["duration_ms"] = duration_ms
            command_logs = builder_result.pop("command_logs", [])
            log_output = "\n\n".join(["Build completed successfully.", *command_logs]).strip()
            report_paths = self.report_generator.generate(context, builder_result, log_output)
            output_path = str(context.dist_path)
            self.database.execute(
                """
                UPDATE builds
                SET status = ?, progress_percent = ?, current_step = ?, current_message = ?,
                    finished_at = ?, duration_ms = ?, output_path = ?, report_path = ?, log_path = ?
                WHERE id = ?
                """,
                (
                    builder_result["status"],
                    100,
                    "Completed",
                    "Build concluído com sucesso.",
                    utc_now_iso(),
                    duration_ms,
                    output_path,
                    report_paths["markdown_path"],
                    report_paths["log_path"],
                    build_id,
                ),
            )
            self.project_service.mark_status(project_id, "built")
        except BuildCancelledError:
            duration_ms = int((perf_counter() - start_clock) * 1000)
            cancelled_result = {
                "status": "cancelled",
                "strategy_used": strategy_hint,
                "outputs": [],
                "warnings": ["Build cancelado pelo usuário antes da conclusão."],
                "errors": [],
                "duration_ms": duration_ms,
            }
            report_paths = self.report_generator.generate(
                context,
                cancelled_result,
                "Build cancelled by user.\n",
            )
            self.database.execute(
                """
                UPDATE builds
                SET status = ?, progress_percent = ?, current_step = ?, current_message = ?,
                    finished_at = ?, duration_ms = ?, output_path = ?, report_path = ?, log_path = ?
                WHERE id = ?
                """,
                (
                    "cancelled",
                    100,
                    "Cancelled",
                    "Build cancelado pelo usuário.",
                    utc_now_iso(),
                    duration_ms,
                    str(context.dist_path),
                    report_paths["markdown_path"],
                    report_paths["log_path"],
                    build_id,
                ),
            )
            self.project_service.mark_status(project_id, "build_cancelled")
        except ProcessExecutionError as exc:
            self._handle_failed_build(
                build_id=build_id,
                project_id=project_id,
                context=context,
                strategy_hint=strategy_hint,
                start_clock=start_clock,
                error_text=str(exc),
                log_output=exc.output,
            )
        except Exception as exc:
            self._handle_failed_build(
                build_id=build_id,
                project_id=project_id,
                context=context,
                strategy_hint=strategy_hint,
                start_clock=start_clock,
                error_text=str(exc),
                log_output=str(exc),
            )
        finally:
            with self._threads_lock:
                self._threads.pop(build_id, None)

    def _handle_failed_build(
        self,
        *,
        build_id: str,
        project_id: str,
        context: BuildContext,
        strategy_hint: str,
        start_clock: float,
        error_text: str,
        log_output: str,
    ) -> None:
        duration_ms = int((perf_counter() - start_clock) * 1000)
        failed_result = {
            "status": "failed",
            "strategy_used": strategy_hint,
            "outputs": [],
            "warnings": context.analysis.get("warnings", []),
            "errors": [error_text],
            "duration_ms": duration_ms,
        }
        report_paths = self.report_generator.generate(context, failed_result, log_output)
        self.database.execute(
            """
            UPDATE builds
            SET status = ?, progress_percent = ?, current_step = ?, current_message = ?,
                finished_at = ?, duration_ms = ?, output_path = ?, report_path = ?, log_path = ?
            WHERE id = ?
            """,
            (
                "failed",
                100,
                "Failed",
                error_text.splitlines()[0] if error_text else "Falha no build.",
                utc_now_iso(),
                duration_ms,
                str(context.dist_path),
                report_paths["markdown_path"],
                report_paths["log_path"],
                build_id,
            ),
        )
        self.project_service.mark_status(project_id, "build_failed")

    def _update_progress(
        self,
        build_id: str,
        *,
        percent: int,
        step: str,
        message: str,
        status: str | None = None,
    ) -> None:
        safe_percent = max(0, min(100, int(percent)))
        self.database.execute(
            """
            UPDATE builds
            SET status = COALESCE(?, status), progress_percent = ?, current_step = ?, current_message = ?
            WHERE id = ?
              AND status NOT IN ('success', 'failed', 'cancelled')
            """,
            (status, safe_percent, step, message, build_id),
        )

    def _ensure_not_cancelled(self, build_id: str) -> None:
        row = self.database.fetch_one(
            "SELECT cancel_requested FROM builds WHERE id = ?",
            (build_id,),
        )
        if row and bool(row["cancel_requested"]):
            raise BuildCancelledError("Build cancelled by user.")

    def _create_backup(self, context: BuildContext) -> None:
        backup_path = context.backups_path / f"{context.build_id}-src"
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(context.src_path, backup_path)

    def _select_builder(self, strategy: str):
        if strategy in {"play_cdn_conversion", "cdn_legacy"}:
            return PlayCdnBuilder(process_runner=self.process_runner)
        if strategy == "cli_build":
            return CliBuilder(process_runner=self.process_runner)
        if strategy == "postcss_build":
            return PostcssBuilder(process_runner=self.process_runner)
        if strategy == "vite_build":
            return ViteBuilder(process_runner=self.process_runner)
        if strategy == "legacy_safe_mode":
            return LegacyBuilder(process_runner=self.process_runner)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Estratégia `{strategy}` ainda não foi implementada no builder real.",
        )

    def _get_running_build_for_project(self, project_id: str) -> BuildSummary | None:
        row = self.database.fetch_one(
            """
            SELECT id, project_id, analysis_id, strategy_used, status, progress_percent,
                   current_step, current_message, cancel_requested, started_at, finished_at,
                   duration_ms, output_path, report_path, log_path
            FROM builds
            WHERE project_id = ? AND status IN ('queued', 'running')
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        return self._to_build_summary(row) if row else None

    def _to_build_summary(self, row: dict) -> BuildSummary:
        row = dict(row)
        row["cancel_requested"] = bool(row.get("cancel_requested"))
        row["progress_percent"] = int(row.get("progress_percent") or 0)
        return BuildSummary(**row)
