from __future__ import annotations

import platform
import subprocess


def pick_directory(title: str | None = None) -> tuple[bool, str | None]:
    system_name = platform.system()
    if system_name == "Windows":
        return True, _pick_directory_windows(title)
    if system_name in {"Linux", "Darwin"}:
        return _pick_directory_tk(title)
    return False, None


def _pick_directory_windows(title: str | None) -> str | None:
    description = (title or "Selecione uma pasta").replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '{description}'
$dialog.ShowNewFolderButton = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  Write-Output $dialog.SelectedPath
}}
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Falha ao abrir o seletor de pastas do Windows.")
    selected_path = completed.stdout.strip()
    return selected_path or None


def _pick_directory_tk(title: str | None) -> tuple[bool, str | None]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return False, None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askdirectory(title=title or "Selecione uma pasta", mustexist=True)
    finally:
        root.destroy()
    return True, path or None
