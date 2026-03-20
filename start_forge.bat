@echo off
setlocal
cd /d "%~dp0"

set "LAUNCHER=scripts\launch_forge.py"
if not exist "%LAUNCHER%" (
  set "LAUNCHER=app\scripts\launch_forge.py"
)

if not exist "%LAUNCHER%" (
  echo Launcher nao encontrado. Estrutura esperada: scripts\launch_forge.py ou app\scripts\launch_forge.py
  exit /b 1
)

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%LAUNCHER%" %*
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    python "%LAUNCHER%" %*
  ) else (
    echo Python nao foi encontrado no PATH.
    exit /b 1
  )
)

endlocal
