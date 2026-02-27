# 20 — Migrar Worker VM → VPS (usar mientras)

## Certeza de la configuración actual

Lo que **sí está documentado** (auditorías 2026-02-26 y 2026-02-27):

| Lado | Qué sabemos | Qué no está 100% verificado |
|------|-------------|-----------------------------|
| **VPS** | Repo en `~/umbral-agent-stack`, OpenClaw en systemd (`openclaw gateway`), Redis en 6379 (Docker), `~/.config/openclaw/env` con WORKER_URL→VM y WORKER_TOKEN, Tailscale 100.113.249.25, Dispatcher/Notion poller ejecutables. | Contenido exacto de `~/.openclaw/openclaw.json`, variables extra en `env` (OpenAI/Anthropic keys, etc.). |
| **VM** | Repo en `C:\GitHub\umbral-agent-stack`, NSSM `openclaw-worker` corriendo, puerto 8088, Tailscale 100.109.16.40, Python 3.11.9, Worker responde en `/health` y `/run`. | Comando exacto de NSSM (¿`uvicorn app:app` desde `C:\openclaw-worker\` o `uvicorn worker.app:app` desde el repo?), variables de entorno que NSSM inyecta (WORKER_TOKEN, NOTION_*), si el worker está en `C:\openclaw-worker\` o solo en el repo. |

Para tener **certeza total** en la VM, conviene que Codex (o alguien) en la VM ejecute una vez un checklist y lo deje en el repo: comando NSSM, `WORKER_TOKEN`/`NOTION_*` (sin valores), rutas, y versión de `worker/app.py` que está corriendo. Ver tarea en `.agents/tasks/` más abajo.

## Dónde hacer la migración / “usar mientras”

**Recomendación:** levantar el **Worker en la VPS** (mismo código que en la VM) y apuntar el Dispatcher a `WORKER_URL=http://127.0.0.1:8088`. Así podés usar Rick (OpenClaw + Dispatcher + cola + Worker) **mientras la VM está apagada o no disponible**.

- **Ventajas:** Un solo host (VPS), sin depender de Tailscale ni de la VM para el flujo básico (ping, tareas que no requieran Windows/PAD/Notion).
- **Limitaciones:** En la VPS no tenés PAD/RPA ni herramientas Windows; las tareas que requieran Notion funcionarán solo si configurás en la VPS las mismas variables Notion que en la VM (`NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_GRANOLA_DB_ID`).

Opciones:

1. **Solo VPS (Worker en VPS)**  
   Dispatcher → Redis → Worker en localhost (VPS). Para “usar mientras” sin VM.
2. **Híbrido**  
   Dejar Dispatcher apuntando a la VM cuando esté encendida; cuando no, cambiar `WORKER_URL` a `http://127.0.0.1:8088` y levantar el Worker en la VPS (o tener dos entornos y elegir por env).
3. **Solo VM**  
   No migrar; seguir usando solo la VM cuando esté disponible.

Para “migrar lo que ya tenés en la VM a la VPS para usarlo mientras”, la opción práctica es la **1** (Worker en VPS, Dispatcher a localhost), documentada más abajo.

## Pasos para tener Worker en la VPS (modo “mientras”)

1. **En la VPS** (con el repo ya clonado en `~/umbral-agent-stack`):
   - Instalar deps del worker:  
     `pip3 install -r ~/umbral-agent-stack/worker/requirements.txt`  
     (o en un venv si preferís).
   - Exportar (o poner en `~/.config/openclaw/env` o en un `.env` que cargue el servicio):
     - `WORKER_TOKEN` (el mismo que usa el Dispatcher para llamar al Worker).
     - Opcional, para tareas Notion: `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_GRANOLA_DB_ID`.
   - Arrancar el Worker:
     - **Opción A (manual):**  
       `cd ~/umbral-agent-stack && PYTHONPATH=. WORKER_TOKEN=... python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088`
     - **Opción B (servicio):**  
       Usar el unit systemd de usuario `openclaw-worker-vps.service` (ver `openclaw/systemd/` y runbook más abajo).

2. **Configurar el Dispatcher para usar el Worker en la VPS:**
   - En el entorno donde corrés Dispatcher (o en `~/.config/openclaw/env` si lo lee):
     - `WORKER_URL=http://127.0.0.1:8088`
     - Mismo `WORKER_TOKEN` que el Worker.
   - Reiniciar Dispatcher (y Notion poller si lo usás).

3. **Probar:**  
   `curl http://127.0.0.1:8088/health` y una llamada a `/run` con Bearer; o usar `scripts/test_s1_contract.py` con `WORKER_URL=http://127.0.0.1:8088`.

Cuando quieras volver a usar la VM, cambiás `WORKER_URL` a la IP Tailscale de la VM (p. ej. `http://100.109.16.40:8088`) y reiniciás Dispatcher (y opcionalmente parás el Worker en la VPS).

## Tarea para Codex en la VM (levantar todo y documentar)

Si querés que **Codex 5.3 en la VM** se encargue de “levantar todo lo de la VM” y dejar la configuración clara:

1. **Documentar el estado real de la VM** (sin secretos):
   - Comando exacto que usa NSSM para el worker (ej. `python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088` y desde qué directorio).
   - Variables de entorno que NSSM inyecta (nombres solamente: WORKER_TOKEN, NOTION_*, etc.).
   - Ruta del ejecutable Python y si usa `C:\openclaw-worker\` o el repo `C:\GitHub\umbral-agent-stack`.
   - Que el worker que corre sea el del repo (p. ej. `worker.app:app` desde repo) o el de `C:\openclaw-worker\app.py`.

2. **Dejar un runbook corto** en el repo (por ejemplo `runbooks/runbook-vm-worker-setup.md`) con los pasos para “levantar todo” en la VM desde cero (instalar deps, configurar NSSM, firewall, WORKER_TOKEN, Notion si aplica).

3. Opcional: un script (PowerShell) que verifique que el Worker está arriba, que el repo está al día y que las env necesarias están definidas (sin imprimir valores).

La tarea ya está creada: [.agents/tasks/2026-02-27-002-vm-document-setup-and-runbook.md](../.agents/tasks/2026-02-27-002-vm-document-setup-and-runbook.md). Asignada a Codex; podés abrir la VM con VS + Codex y pedirle que ejecute esa tarea.

## Resumen

- **Certeza:** Tenemos una buena foto de VPS y VM por las auditorías; la VM no está 100% documentada a nivel NSSM/comando y env. Recomendación: que Codex en la VM documente el setup exacto y un runbook de “levantar todo”.
- **Migración “mientras”:** Levantar el Worker en la VPS y poner `WORKER_URL=http://127.0.0.1:8088` en el Dispatcher; así podés usar Rick sin la VM. Para paridad con Notion, copiar (o compartir de forma segura) las variables Notion en la VPS.
- **Dónde hacerlo:** La parte “migrar a la VPS” se hace **en la VPS** (instalar deps del worker, arrancar worker, apuntar Dispatcher a localhost). La parte “levantar todo en la VM” y documentar se hace **en la VM** con Codex.
