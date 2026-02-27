# Umbral Agent Stack

> Sistema multi-agente, multi-modelo: **Rick** (meta-orquestador) gestiona equipos de agentes AI en una arquitectura split — Control Plane (VPS 24/7) + Execution Plane (VM Windows) — conectados por Tailscale, coordinados vía Notion y Redis.

---

## 🏗️ Arquitectura (v2.8)

```
David ──► Telegram/Notion ──► VPS (Control Plane 24/7) ──Tailscale──► VM Windows (Execution Plane)
                                    │                                         │
                                    ├── Rick (meta-orquestador)               ├── LangGraph runtime
                                    ├── ModelRouter → TeamRouter              ├── Worker FastAPI :8088
                                    ├── LiteLLM (5 LLMs)                     ├── PAD/RPA adapters
                                    └── Redis (cola+estado)                   └── Langfuse + ChromaDB
```

- **Control Plane (VPS Hostinger)**: Rick + OpenClaw + Dispatcher + LiteLLM + Redis → 24/7
- **Execution Plane (VM Windows)**: Worker + LangGraph + PAD/RPA + ChromaDB + Langfuse
- **5 LLMs**: Claude Pro, ChatGPT Plus, Gemini Pro, Copilot Pro, Notion AI
- **3 Equipos**: Marketing, Asesoría Personal, Mejora Continua
- **Red privada**: Tailscale mesh sin puertos públicos expuestos

> 📋 **Plan Maestro**: [docs/14-codex-plan.md](docs/14-codex-plan.md) | **Política Cuotas**: [docs/15-model-quota-policy.md](docs/15-model-quota-policy.md) | **ADRs**: [docs/adr/](docs/adr/)

## 🚀 Quickstart

### VPS — Verificar estado

```bash
systemctl --user status openclaw
openclaw status --all
```

### VPS — Probar worker desde VPS

```bash
# Health check (sin auth)
curl http://WINDOWS_TAILSCALE_IP:8088/health

# Ejecutar tarea (con auth — usar comillas simples para tokens con "!")
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer CHANGE_ME_WORKER_TOKEN' \
  -d '{"task":"ping","input":{}}'
```

### Windows — Levantar worker (modo dev)

```powershell
cd C:\GitHub\umbral-agent-stack
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info
```

### Windows — Desplegar y reiniciar servicio (NSSM)
Para actualizar con los últimos cambios de `main`, instalar dependencias y reiniciar el servicio NSSM en Windows:
```powershell
.\scripts\deploy-vm.ps1
```

## 🔗 Worker + Notion Bridge

El worker expone un bus HTTP para ejecutar tareas, incluyendo integración con Notion como **bus de coordinación** entre David, Rick (OpenClaw/Worker) y agentes.

### Variables de entorno requeridas

| Variable | Dónde | Descripción |
|----------|-------|-------------|
| `WORKER_TOKEN` | VPS + Windows | Token Bearer compartido |
| `WORKER_URL` | VPS | URL del worker (e.g. `http://100.109.16.40:8088`) |
| `NOTION_API_KEY` | Windows | Token de la integración Notion |
| `NOTION_CONTROL_ROOM_PAGE_ID` | Windows | ID de la página "OpenClaw Control Room" |
| `NOTION_GRANOLA_DB_ID` | Windows | ID de la DB "Granola Inbox" |

Copiar `.env.example` → `.env` y rellenar con valores reales.

### Tareas disponibles en `/run`

| Task | Input | Descripción |
|------|-------|-------------|
| `ping` | `{}` o cualquier JSON | Echo de prueba |
| `notion.write_transcript` | `{title, content, source?, date?}` | Crea página en Granola Inbox DB |
| `notion.add_comment` | `{text, page_id?}` | Comenta en Control Room (o página específica) |
| `notion.poll_comments` | `{since?, limit?, page_id?}` | Lee comentarios recientes |

### S3 — Loop Notion ↔ Rick (poller)

En la VPS podés levantar el **Notion poller**: revisa comentarios de la página Control Room (vía Worker) y encola tareas. Se coordina con el agente de Notion **"Enlace Notion ↔ Rick"** (que corre cada hora en punto): **Rick revisa a las XX:10** de cada hora para ver mensajes que Enlace o David dejaron. Ver [docs/18-notion-enlace-rick-convention.md](docs/18-notion-enlace-rick-convention.md).

```bash
# En la VPS (misma env que el Dispatcher)
cd ~/umbral-agent-stack
export WORKER_URL="http://IP_TAILSCALE_VM:8088"
export WORKER_TOKEN="tu-token"
export REDIS_URL="redis://localhost:6379/0"
export PYTHONPATH=$(pwd)
# Por defecto: poll a las XX:10 de cada hora. Para otro minuto: NOTION_POLL_AT_MINUTE=15
# Para poll continuo cada N segundos: NOTION_POLL_INTERVAL_SEC=300
python3 -m dispatcher.notion_poller
```

Dejalo corriendo en una terminal (o systemd/nohup). Los comentarios que empiezan por `Rick:` se ignoran (son nuestras respuestas).

**Equipos y workers:** Los equipos y supervisores se definen en [config/teams.yaml](config/teams.yaml) (supervisor, roles, `requires_vm`, `notion_page_id` opcional). El Dispatcher usa **N workers en paralelo** (env `DISPATCHER_WORKERS`, default 2).

### Ejemplo desde VPS (curl)

```bash
# Health check
curl http://100.109.16.40:8088/health

# Ping (usar comillas simples — evita "event not found" si el token tiene "!")
curl -s -X POST http://100.109.16.40:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer MI_TOKEN_AQUI' \
  -d '{"task":"ping","input":{"msg":"hola"}}'

# Escribir comentario en Notion Control Room
curl -s -X POST http://100.109.16.40:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer MI_TOKEN_AQUI' \
  -d '{"task":"notion.add_comment","input":{"text":"Test desde VPS"}}'
```

### WorkerClient SDK (Python)

```python
from client.worker_client import WorkerClient

wc = WorkerClient()  # lee WORKER_URL y WORKER_TOKEN de env
wc.ping()
wc.notion_add_comment("Hello from VPS")
wc.notion_poll_comments(since="2026-02-26T00:00:00Z")
```

### Tests

```bash
pip install -r worker/requirements.txt
WORKER_TOKEN=test python -m pytest tests/ -v
```

## 📂 Estructura del Repositorio

```
├── client/            # WorkerClient SDK (Python)
├── docs/              # Documentación completa paso a paso
├── runbooks/          # Procedimientos operativos (runbooks)
├── worker/            # Código FastAPI del worker
│   ├── app.py         #   App principal (endpoints)
│   ├── config.py      #   Variables de entorno centralizadas
│   ├── notion_client.py #  Cliente Notion API
│   └── tasks/         #   Handlers de tareas (ping, notion.*)
├── tests/             # Tests mínimos (pytest)
├── openclaw/          # Config templates, scripts, systemd units
├── scripts/           # Scripts de utilidad (VPS bash + Windows PS1)
├── infra/             # Docker compose scaffolds, diagramas
└── changelog/         # Log de cambios por fecha
```

## 📖 Documentación Clave

| Doc | Descripción |
|-----|-------------|
| [00-overview](docs/00-overview.md) | Visión general del sistema |
| [01-architecture](docs/01-architecture-v2.3.md) | Arquitectura v2.8 objetivo |
| [14-codex-plan](docs/14-codex-plan.md) | **Plan Maestro v2.8** |
| [15-model-quota](docs/15-model-quota-policy.md) | **Política multi-modelo y cuotas** |
| [ADRs](docs/adr/) | **Decisiones arquitectónicas (001-004)** |
| [02-implementation-log](docs/02-implementation-log.md) | Cronología de implementación |
| [03-setup-vps](docs/03-setup-vps-openclaw.md) | Setup VPS + OpenClaw |
| [05-setup-tailscale](docs/05-setup-tailscale.md) | Tailscale VPS ↔ Windows |
| [06-setup-worker](docs/06-setup-worker-windows.md) | Worker Windows (FastAPI) |
| [07-api-contract](docs/07-worker-api-contract.md) | Contrato API del worker |
| [11-roadmap](docs/11-roadmap-next-steps.md) | Roadmap por sprints (S0-S7) |
| [12-vps-audit](docs/12-vps-audit-2026-02-26.md) | Auditoría VPS |
| [13-vm-audit](docs/13-vm-audit-2026-02-26.md) | Auditoría VM |

## ⚠️ Seguridad

- **NUNCA** commitear tokens, claves API o archivos `.env`.
- Todos los secretos usan placeholders: `CHANGE_ME_*`.
- Acceso a Control UI solo por SSH tunnel o Tailscale — **nunca exponer puertos públicos**.
- Ver [docs/10-security-notes.md](docs/10-security-notes.md) para detalles completos.

> **Nota sobre bash history**: Si un token contiene `!`, usar comillas simples en comandos curl para evitar "event not found". Ejemplo: `-H 'Authorization: Bearer token_con_!_aquí'`

## 📋 Estado del Proyecto

| Sprint | Estado | Descripción |
|--------|--------|-------------|
| **Fase 1.0-1.7** | ✅ Hecho | VPS + OpenClaw + Telegram + Tailscale + Worker + Notion Bridge |
| **S0** | ✅ Hecho | Normalización docs/repo, ADRs, auditorías VPS/VM |
| **S1** | ✅ Hecho | TaskEnvelope v0.1 + gobernanza |
| **S2** | ✅ Hecho | Orquestación split (Dispatcher + Redis + E2E VM) |
| **S3** | ✅ Hecho | Equipos + Notion (poller XX:10, teams.yaml, N workers) |
| **S4** | 📋 | ModelRouter + cuotas multi-modelo |
| **S5** | 📋 | Herramientas Windows (PAD/RPA) |
| **S6** | 📋 | Observabilidad (Langfuse + evals) |
| **S7** | 📋 | Hardening transversal |

