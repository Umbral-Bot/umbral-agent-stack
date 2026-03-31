@echo off
REM Worker interactivo (sesion 1) - arranca al logon de Rick.
REM Mismo codigo que openclaw-worker (puerto 8089). Tareas GUI van aqui.
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set REPO_ROOT=%%~fI
cd /d "%REPO_ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\vm\start_interactive_worker.ps1"
