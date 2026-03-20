from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.api.routes.analysis import router as analysis_router
from app.api.routes.builds import router as builds_router
from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.i18n import router as i18n_router
from app.api.routes.publish import router as publish_router
from app.api.routes.projects import router as projects_router
from app.api.routes.settings import router as settings_router
from app.api.routes.system import router as system_router
from app.api.websocket.builds import router as builds_websocket_router
from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import Database
from app.i18n import Translator
from app.middleware.rate_limit import LocalRateLimitMiddleware
from app.services.analysis_service import AnalysisService
from app.services.build_service import BuildService
from app.services.export_service import ExportService
from app.services.history_service import HistoryService
from app.services.publish_service import PublishService
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.workspace_service import WorkspaceService
from app.utils.secrets import SecretManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    translator = Translator()
    workspace_service = WorkspaceService(settings)
    workspace_service.prepare_runtime_directories()

    database = Database(settings.database_path)
    init_db(database)

    project_service = ProjectService(database, workspace_service)
    analysis_service = AnalysisService(database, project_service)
    build_service = BuildService(database, project_service, analysis_service)
    export_service = ExportService(database, build_service, settings.exports_path)
    settings_service = SettingsService(database, settings, translator)
    history_service = HistoryService(database, project_service)
    publish_service = PublishService(
        database,
        project_service,
        build_service,
        SecretManager(settings.secrets_path),
        settings.known_hosts_path,
    )

    app.state.settings = settings
    app.state.translator = translator
    app.state.database = database
    app.state.workspace_service = workspace_service
    app.state.project_service = project_service
    app.state.analysis_service = analysis_service
    app.state.build_service = build_service
    app.state.export_service = export_service
    app.state.settings_service = settings_service
    app.state.history_service = history_service
    app.state.publish_service = publish_service
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        LocalRateLimitMiddleware,
        max_requests=settings.api_rate_limit_max_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "Origin"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(projects_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(builds_router, prefix="/api")
    app.include_router(exports_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    app.include_router(i18n_router, prefix="/api")
    app.include_router(history_router, prefix="/api")
    app.include_router(publish_router, prefix="/api")
    app.include_router(builds_websocket_router)

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        return _serve_frontend_asset(settings.frontend_dist_path, "")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            return HTMLResponse("Not Found", status_code=404)
        return _serve_frontend_asset(settings.frontend_dist_path, full_path)

    return app


def _serve_frontend_asset(frontend_dist_path: Path, full_path: str):
    frontend_dist_resolved = frontend_dist_path.resolve()
    index_path = frontend_dist_path / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            """
            <html><body style="font-family: monospace; background:#05070d; color:#fff; padding:32px;">
            <h1>Tailwind CSS Forge</h1>
            <p>Frontend ainda não buildado. Execute <code>npm run build</code> em <code>frontend/</code>.</p>
            </body></html>
            """,
            status_code=503,
        )

    if full_path:
        if not _is_safe_frontend_path(full_path):
            return HTMLResponse("Not Found", status_code=404)

        candidate = (frontend_dist_resolved / PurePosixPath(full_path)).resolve()
        if candidate.is_file() and candidate.is_relative_to(frontend_dist_resolved):
            return FileResponse(candidate)

    return FileResponse(index_path)


def _is_safe_frontend_path(full_path: str) -> bool:
    if not full_path or "\x00" in full_path:
        return False

    normalized = full_path.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute():
        return False

    return all(part not in {"", ".", ".."} for part in pure_path.parts)


app = create_app()
