from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path, PurePosixPath


class ProcessExecutionError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, output: str) -> None:
        command_label = " ".join(command)
        super().__init__(f"Command failed ({returncode}): {command_label}\n{output}")
        self.command = command
        self.returncode = returncode
        self.output = output


class ProcessRunner:
    allowed_commands = {
        ("npm", "install"),
        ("npx", "@tailwindcss/cli"),
        ("npx", "tailwindcss"),
        ("npx", "vite"),
    }

    def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
        self._ensure_allowed(command, cwd)
        normalized_command = self._normalize_command(command)
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            completed = subprocess.run(
                normalized_command,
                cwd=cwd,
                env=merged_env,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ProcessExecutionError(command, -1, f"Executable not found for command: {' '.join(command)}") from exc
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
        if completed.returncode != 0:
            raise ProcessExecutionError(command, completed.returncode, output)

        return output

    def _ensure_allowed(self, command: list[str], cwd: Path) -> None:
        if len(command) < 2:
            raise ProcessExecutionError(command, -1, "Incomplete command.")

        key = (command[0], command[1])
        if key not in self.allowed_commands:
            raise ProcessExecutionError(command, -1, "Command not allowed by policy.")

        allowed_roots = self._derive_allowed_roots(cwd)
        if key == ("npm", "install"):
            self._validate_npm_install(command)
            return
        if key in {("npx", "tailwindcss"), ("npx", "@tailwindcss/cli")}:
            self._validate_tailwind_command(command, cwd, allowed_roots)
            return
        if key == ("npx", "vite"):
            self._validate_vite_command(command, cwd, allowed_roots)

    def _validate_npm_install(self, command: list[str]) -> None:
        allowed_flags = {"--ignore-scripts", "--no-fund", "--no-audit", "--silent"}
        extras = command[2:]
        invalid = [arg for arg in extras if arg not in allowed_flags]
        if invalid:
            raise ProcessExecutionError(command, -1, f"Unsupported npm install arguments: {invalid}")

    def _validate_tailwind_command(
        self,
        command: list[str],
        cwd: Path,
        allowed_roots: list[Path],
    ) -> None:
        index = 2
        path_flags = {"-i", "-o", "--config"}
        glob_flags = {"--content"}
        flag_only = {"--minify"}

        while index < len(command):
            current = command[index]
            if current in flag_only:
                index += 1
                continue
            if current in path_flags:
                if index + 1 >= len(command):
                    raise ProcessExecutionError(command, -1, f"Missing value for argument {current}")
                self._validate_path_argument(command, command[index + 1], cwd, allowed_roots)
                index += 2
                continue
            if current in glob_flags:
                if index + 1 >= len(command):
                    raise ProcessExecutionError(command, -1, f"Missing value for argument {current}")
                self._validate_glob_argument(command, command[index + 1])
                index += 2
                continue
            raise ProcessExecutionError(command, -1, f"Unsupported Tailwind argument: {current}")

    def _validate_vite_command(
        self,
        command: list[str],
        cwd: Path,
        allowed_roots: list[Path],
    ) -> None:
        if len(command) < 3 or command[2] != "build":
            raise ProcessExecutionError(command, -1, "Only `npx vite build` is allowed.")

        index = 3
        while index < len(command):
            current = command[index]
            if current == "--emptyOutDir":
                index += 1
                continue
            if current == "--outDir":
                if index + 1 >= len(command):
                    raise ProcessExecutionError(command, -1, "Missing value for `--outDir`.")
                self._validate_path_argument(command, command[index + 1], cwd, allowed_roots)
                index += 2
                continue
            if current == "--minify":
                if index + 1 >= len(command):
                    raise ProcessExecutionError(command, -1, "Missing value for `--minify`.")
                if command[index + 1] not in {"false", "true", "esbuild", "terser"}:
                    raise ProcessExecutionError(command, -1, "Unsupported value for `--minify`.")
                index += 2
                continue
            raise ProcessExecutionError(command, -1, f"Unsupported Vite argument: {current}")

    def _validate_path_argument(
        self,
        command: list[str],
        raw_value: str,
        cwd: Path,
        allowed_roots: list[Path],
    ) -> None:
        if "\x00" in raw_value:
            raise ProcessExecutionError(command, -1, "Null bytes are not allowed in process arguments.")

        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = (cwd / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not any(candidate.is_relative_to(root) for root in allowed_roots):
            raise ProcessExecutionError(
                command,
                -1,
                f"Process argument points outside the allowed workspace: {raw_value}",
            )

    def _validate_glob_argument(self, command: list[str], raw_value: str) -> None:
        if "\x00" in raw_value:
            raise ProcessExecutionError(command, -1, "Null bytes are not allowed in glob arguments.")

        path = PurePosixPath(raw_value.replace("\\", "/"))
        if path.is_absolute() or any(part == ".." for part in path.parts):
            raise ProcessExecutionError(command, -1, f"Unsupported glob argument: {raw_value}")

    def _derive_allowed_roots(self, cwd: Path) -> list[Path]:
        resolved_cwd = cwd.resolve()
        allowed_roots = [resolved_cwd]
        for ancestor in (resolved_cwd, *resolved_cwd.parents):
            if (ancestor / "src").is_dir() and (ancestor / "dist").exists():
                allowed_roots.append(ancestor.resolve())
                break
        return allowed_roots

    def _normalize_command(self, command: list[str]) -> list[str]:
        if sys.platform.startswith("win") and command[0] in {"npm", "npx"}:
            return [f"{command[0]}.cmd", *command[1:]]
        return command
