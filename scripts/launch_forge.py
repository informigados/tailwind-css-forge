from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from argparse import ArgumentParser, Namespace
from pathlib import Path

from forge_metadata import find_product_metadata_path, load_product_metadata


SOURCE_ROOT = Path(__file__).resolve().parents[1]
MINIMUM_PYTHON = (3, 12)


def main() -> int:
    args = parse_args()
    backend_process: subprocess.Popen[str] | None = None
    try:
        app_root = resolve_app_root()
        installed_layout = is_installed_layout(app_root)
        if args.self_check or args.assert_ready:
            report = build_self_check_report(app_root, installed_layout=installed_layout)
            emit_self_check_report(report, as_json=args.json)
            return 0 if report["ready"] or not args.assert_ready else 1

        backend_dir = app_root / "backend"
        frontend_dir = app_root / "frontend"
        runtime_dir = resolve_runtime_dir(app_root, installed_layout=installed_layout, create=True)
        python_executable = ensure_backend_venv(backend_dir, runtime_dir, installed_layout=installed_layout)
        install_backend_dependencies(python_executable)
        install_frontend_dependencies(frontend_dir, runtime_dir, installed_layout=installed_layout)
        build_frontend_if_needed(frontend_dir, installed_layout=installed_layout)
        if args.prepare_only:
            print("Preparacao concluida com sucesso.")
            return 0

        backend_process = start_backend(
            python_executable,
            backend_dir=backend_dir,
            frontend_dist_dir=frontend_dir / "dist",
            runtime_dir=runtime_dir,
            port=args.port,
        )
        wait_for_health(args.port, backend_process=backend_process)
        app_url = f"http://127.0.0.1:{args.port}"
        if not args.no_browser:
            webbrowser.open(app_url)
        print(f"Forge iniciado em {app_url}")
        print("Pressione Ctrl+C para encerrar o backend.")
        backend_process.wait()
        return backend_process.returncode or 0
    except KeyboardInterrupt:
        print("\nEncerrando o Forge...")
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
        return 0
    except Exception as exc:
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
        print(f"Falha ao iniciar o Forge: {exc}", file=sys.stderr)
        return 1


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Launcher local do Tailwind CSS Forge.")
    parser.add_argument("--prepare-only", action="store_true", help="Instala dependencias e builda o frontend sem subir o servidor.")
    parser.add_argument("--no-browser", action="store_true", help="Nao abre o navegador automaticamente.")
    parser.add_argument("--port", type=int, default=8000, help="Porta do backend local.")
    parser.add_argument("--self-check", action="store_true", help="Valida o layout atual sem instalar dependencias nem iniciar o sistema.")
    parser.add_argument("--json", action="store_true", help="Emite o resultado do self-check em JSON.")
    parser.add_argument("--assert-ready", action="store_true", help="Retorna erro se o self-check indicar que o layout nao esta pronto.")
    return parser.parse_args()


def ensure_backend_venv(backend_dir: Path, runtime_dir: Path, *, installed_layout: bool) -> Path:
    venv_dir = (runtime_dir / "venv" / "backend") if installed_layout else (backend_dir / ".venv")
    if not venv_dir.exists():
        print("Criando ambiente virtual do backend...")
        venv.create(venv_dir, with_pip=True)

    scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    python_name = "python.exe" if sys.platform.startswith("win") else "python"
    python_executable = venv_dir / scripts_dir / python_name
    if not python_executable.exists():
        raise RuntimeError("Python do ambiente virtual nao foi encontrado.")
    return python_executable


def install_backend_dependencies(python_executable: Path) -> None:
    print("Verificando dependencias do backend...")
    app_root = resolve_app_root()
    backend_dir = app_root / "backend"
    runtime_dir = resolve_runtime_dir(
        app_root,
        installed_layout=is_installed_layout(app_root),
        create=False,
    )
    stamp_path = runtime_dir / "setup" / "backend.stamp"
    if _is_stamp_current(stamp_path, [backend_dir / "pyproject.toml"]):
        print("Backend ja esta atualizado.")
        return

    run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)
    run([str(python_executable), "-m", "pip", "install", "-e", "."], cwd=backend_dir)
    _write_stamp(stamp_path)


def install_frontend_dependencies(frontend_dir: Path, runtime_dir: Path, *, installed_layout: bool) -> None:
    print("Verificando dependencias do frontend...")
    if installed_layout:
        if not (frontend_dir / "dist" / "index.html").exists():
            raise RuntimeError("Bundle instalado sem frontend buildado. Recrie o bundle antes de instalar.")
        print("Layout instalado detectado; usando frontend ja buildado.")
        return

    stamp_path = runtime_dir / "setup" / "frontend.stamp"
    dependency_inputs = [frontend_dir / "package.json", frontend_dir / "package-lock.json"]
    if _is_stamp_current(stamp_path, dependency_inputs):
        print("Frontend ja esta atualizado.")
        return

    run(["npm", "install", "--ignore-scripts", "--no-fund", "--no-audit"], cwd=frontend_dir)
    _write_stamp(stamp_path)


def build_frontend_if_needed(frontend_dir: Path, *, installed_layout: bool) -> None:
    print("Verificando build do frontend...")
    if installed_layout:
        if not (frontend_dir / "dist" / "index.html").exists():
            raise RuntimeError("Frontend buildado nao encontrado no layout instalado.")
        print("Layout instalado detectado; frontend buildado sera reutilizado.")
        return

    dist_index = frontend_dir / "dist" / "index.html"
    sources = [
        frontend_dir / "index.html",
        frontend_dir / "package.json",
        frontend_dir / "vite.config.ts",
        *list((frontend_dir / "src").rglob("*")),
    ]
    if dist_index.exists() and dist_index.stat().st_mtime >= max(path.stat().st_mtime for path in sources if path.exists()):
        print("Build do frontend ja esta atual.")
        return

    run(["npm", "run", "build"], cwd=frontend_dir)


def start_backend(
    python_executable: Path,
    *,
    backend_dir: Path,
    frontend_dist_dir: Path,
    runtime_dir: Path,
    port: int,
) -> subprocess.Popen[str]:
    print("Iniciando backend com frontend estatico...")
    command = [
        str(python_executable),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    env = os.environ.copy()
    env["FORGE_RUNTIME_PATH"] = str(runtime_dir)
    env["FORGE_DATABASE_PATH"] = str(runtime_dir / "forge.db")
    env["FORGE_FRONTEND_DIST_PATH"] = str(frontend_dist_dir)
    return subprocess.Popen(command, cwd=backend_dir, env=env)


def wait_for_health(
    port: int,
    timeout_seconds: int = 45,
    *,
    backend_process: subprocess.Popen[str] | None = None,
) -> None:
    health_url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        if backend_process and backend_process.poll() is not None:
            raise RuntimeError(
                f"Backend encerrou antes do healthcheck com codigo {backend_process.returncode}.",
            )
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    detail = f" Ultimo erro observado: {last_error}" if last_error else ""
    raise RuntimeError(f"Backend nao respondeu ao healthcheck no tempo esperado.{detail}")


def run(command: list[str], cwd: Path) -> None:
    normalized_command = _normalize_command(command)
    completed = subprocess.run(normalized_command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Comando falhou ({completed.returncode}): {' '.join(command)}")


def _is_stamp_current(stamp_path: Path, inputs: list[Path]) -> bool:
    if not stamp_path.exists():
        return False

    stamp_mtime = stamp_path.stat().st_mtime
    return all(path.exists() and path.stat().st_mtime <= stamp_mtime for path in inputs)


def _write_stamp(stamp_path: Path) -> None:
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(str(time.time()), encoding="utf-8")


def _normalize_command(command: list[str]) -> list[str]:
    if sys.platform.startswith("win") and command and command[0] == "npm":
        return ["npm.cmd", *command[1:]]
    return command


def resolve_app_root() -> Path:
    app_root_override = os.getenv("FORGE_APP_ROOT")
    if app_root_override:
        return Path(app_root_override).resolve()

    if getattr(sys, "frozen", False):
        return (Path(sys.executable).resolve().parent / "app").resolve()

    return SOURCE_ROOT


def resolve_runtime_dir(app_root: Path, *, installed_layout: bool, create: bool) -> Path:
    runtime_override = os.getenv("FORGE_RUNTIME_PATH")
    if runtime_override:
        runtime_dir = Path(runtime_override).resolve()
        if create:
            runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    if getattr(sys, "frozen", False) or installed_layout:
        base_dir = _user_data_root()
        runtime_dir = base_dir / "Tailwind CSS Forge" / "runtime"
        if create:
            runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    runtime_dir = (app_root / "runtime").resolve()
    if create:
        runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _user_data_root() -> Path:
    if sys.platform.startswith("win"):
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data).resolve()

    return Path.home().resolve() / ".local" / "share"


def is_installed_layout(app_root: Path) -> bool:
    return (app_root.parent / "installer-manifest.json").exists()


def build_self_check_report(app_root: Path, *, installed_layout: bool) -> dict[str, object]:
    runtime_dir = resolve_runtime_dir(app_root, installed_layout=installed_layout, create=False)
    backend_dir = app_root / "backend"
    frontend_dir = app_root / "frontend"
    bundle_root = app_root.parent if installed_layout else app_root
    manifest_path = bundle_root / "installer-manifest.json"
    metadata_path = find_product_metadata_path(app_root)
    metadata = load_product_metadata(app_root)

    checks = [
        _make_check(
            "python_version",
            sys.version_info >= MINIMUM_PYTHON,
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        _make_check("backend_dir", backend_dir.is_dir(), str(backend_dir)),
        _make_check("backend_pyproject", (backend_dir / "pyproject.toml").is_file(), str(backend_dir / "pyproject.toml")),
        _make_check("frontend_dist", (frontend_dir / "dist" / "index.html").is_file(), str(frontend_dir / "dist" / "index.html")),
        _make_check("launcher_batch", (bundle_root / "start_forge.bat").is_file(), str(bundle_root / "start_forge.bat")),
        _make_check("product_metadata", metadata_path is not None, str(metadata_path) if metadata_path else "forge-product.json ausente"),
        _make_check(
            "installer_manifest",
            manifest_path.is_file() if installed_layout else True,
            str(manifest_path) if installed_layout else "Nao exigido em layout source",
        ),
        _make_check(
            "npm_available",
            installed_layout or _command_exists("npm"),
            "Nao exigido em layout instalado" if installed_layout else "npm encontrado no PATH" if _command_exists("npm") else "npm nao encontrado no PATH",
        ),
    ]

    ready = all(bool(check["ok"]) for check in checks)
    return {
        "app_name": metadata["app_name"],
        "app_version": metadata["version"],
        "app_root": str(app_root),
        "bundle_root": str(bundle_root),
        "runtime_dir": str(runtime_dir),
        "installed_layout": installed_layout,
        "frozen": bool(getattr(sys, "frozen", False)),
        "ready": ready,
        "checks": checks,
    }


def emit_self_check_report(report: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
        return

    print(f"{report['app_name']} {report['app_version']}")
    print(f"Layout instalado: {'sim' if report['installed_layout'] else 'nao'}")
    print(f"Pronto: {'sim' if report['ready'] else 'nao'}")
    for check in report["checks"]:
        status = "OK" if check["ok"] else "FAIL"
        print(f"- [{status}] {check['name']}: {check['detail']}")


def _make_check(name: str, ok: bool, detail: str) -> dict[str, object]:
    return {"name": name, "ok": ok, "detail": detail}


def _command_exists(command: str) -> bool:
    candidates = [command]
    if sys.platform.startswith("win"):
        candidates.append(f"{command}.cmd")
    return any(shutil.which(candidate) for candidate in candidates)


if __name__ == "__main__":
    raise SystemExit(main())
