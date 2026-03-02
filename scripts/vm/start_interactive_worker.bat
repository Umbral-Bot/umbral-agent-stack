@echo off
REM Worker interactivo (sesion 1) - arranca al logon de Rick.
REM Mismo codigo que openclaw-worker (puerto 8089). Tareas GUI van aqui.
cd /d C:\GitHub\umbral-agent-stack
REM WORKER_TOKEN debe estar en el entorno; usar setx o configurar en Tarea programada.
python -m uvicorn worker.app:app --host 0.0.0.0 --port 8089 --log-level info
