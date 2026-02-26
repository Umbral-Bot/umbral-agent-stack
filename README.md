# Umbral Agent Stack

> Arquitectura híbrida para un sistema de agentes AI: VPS gateway (OpenClaw + Telegram) + Worker local (Windows FastAPI) conectados por Tailscale.

---

## 🏗️ Arquitectura Actual (v1.5)

```
Usuario ──► Telegram ──► VPS (OpenClaw 24/7) ──Tailscale──► Worker Windows (FastAPI :8088)
                              │
                              ├── OpenAI Codex 5.3 (LLM default)
                              └── Control UI (localhost:18789 vía SSH tunnel)
```

- **VPS (Hostinger, Ubuntu 24 LTS)**: OpenClaw Gateway corriendo 24/7 como servicio systemd, con Telegram habilitado.
- **Worker Windows (Hyper-V o host)**: FastAPI + Uvicorn en `0.0.0.0:8088`, ejecutado como servicio (NSSM).
- **Red privada**: Tailscale conecta VPS ↔ Windows. Sin puertos públicos expuestos.
- **LLM**: OpenAI Codex (`openai-codex/gpt-5.3-codex`) como provider principal.
- **Acceso UI**: Exclusivamente por SSH port-forwarding (`18789`/`18791`).

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
cd C:\openclaw-worker
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info
```

### Windows — Levantar worker (servicio NSSM)

```powershell
.\scripts\setup-openclaw-service.ps1
nssm status openclaw-worker
```

## 📂 Estructura del Repositorio

```
├── docs/              # Documentación completa paso a paso
├── runbooks/          # Procedimientos operativos (runbooks)
├── worker/            # Código FastAPI del worker
├── openclaw/          # Config templates, scripts, systemd units
├── scripts/           # Scripts de utilidad (VPS bash + Windows PS1)
├── infra/             # Docker compose scaffolds (Fase 2/3), diagramas
└── changelog/         # Log de cambios por fecha
```

## 📖 Documentación Clave

| Doc | Descripción |
|-----|-------------|
| [00-overview](docs/00-overview.md) | Visión general del sistema |
| [01-architecture](docs/01-architecture-v2.3.md) | Arquitectura v2.3 y variaciones |
| [02-implementation-log](docs/02-implementation-log.md) | Cronología de implementación |
| [03-setup-vps](docs/03-setup-vps-openclaw.md) | Setup VPS + OpenClaw |
| [04-setup-telegram](docs/04-setup-telegram-vps.md) | Telegram en VPS |
| [05-setup-tailscale](docs/05-setup-tailscale.md) | Tailscale VPS ↔ Windows |
| [06-setup-worker](docs/06-setup-worker-windows.md) | Worker Windows (FastAPI) |
| [07-api-contract](docs/07-worker-api-contract.md) | Contrato API del worker |
| [08-operations](docs/08-operations-runbook.md) | Runbook de operaciones |
| [09-troubleshooting](docs/09-troubleshooting.md) | Problemas comunes y soluciones |
| [10-security](docs/10-security-notes.md) | Notas de seguridad |
| [11-roadmap](docs/11-roadmap-next-steps.md) | Roadmap y próximos pasos |

## ⚠️ Seguridad

- **NUNCA** commitear tokens, claves API o archivos `.env`.
- Todos los secretos usan placeholders: `CHANGE_ME_*`.
- Acceso a Control UI solo por SSH tunnel o Tailscale — **nunca exponer puertos públicos**.
- Ver [docs/10-security-notes.md](docs/10-security-notes.md) para detalles completos.

> **Nota sobre bash history**: Si un token contiene `!`, usar comillas simples en comandos curl para evitar "event not found". Ejemplo: `-H 'Authorization: Bearer token_con_!_aquí'`

## 📋 Estado del Proyecto

| Fase | Estado | Descripción |
|------|--------|-------------|
| **1.0** | ✅ Hecho | VPS + OpenClaw + Telegram |
| **1.5** | ✅ Hecho | Tailscale + Worker Windows + scripts |
| **2.0** | 📋 Planificado | LangGraph + LiteLLM + Redis |
| **3.0** | 📋 Planificado | Langfuse + ChromaDB + PAD |
