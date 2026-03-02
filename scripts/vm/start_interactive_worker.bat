@echo off
REM Worker interactivo (sesion 1) - arranca al logon de Rick.
REM Mismo codigo que openclaw-worker (puerto 8089). Tareas GUI van aqui.
cd /d C:\GitHub\umbral-agent-stack
set OPENCLAW_INTERACTIVE_SESSION=1
if exist "C:\openclaw-worker\worker_token" (
  set /p WORKER_TOKEN=<"C:\openclaw-worker\worker_token"
)
python -m uvicorn worker.app:app --host 0.0.0.0 --port 8089 --log-level info
