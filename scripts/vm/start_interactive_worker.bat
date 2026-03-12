@echo off
REM Worker interactivo (sesion 1) - arranca al logon de Rick.
REM Mismo codigo que openclaw-worker (puerto 8089). Tareas GUI van aqui.
cd /d C:\GitHub\umbral-agent-stack
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\GitHub\umbral-agent-stack\scripts\vm\start_interactive_worker.ps1"
