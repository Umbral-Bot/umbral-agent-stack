---
id: 2026-05-05-007
title: Notion token rotation (Rick + Supervisor) y cleanup de leak surfaces
assigned_to: copilot-chat (windows) + david (manual portal/nano) + copilot-vps (collab via SSH)
status: completed
created: 2026-05-05
completed: 2026-05-05
related: 2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration
---

## Contexto

Task 006 (audit) descubrió que los 4 archivos `~/.openclaw/agents/{rick-orchestrator,rick-ops}/sessions/*.jsonl` contenían patrones `secret_/ntn_` con los tokens reales de los bots Notion **Rick** (`NOTION_API_KEY`) y **Supervisor** (`NOTION_SUPERVISOR_API_KEY`) loggeados en plano (tool outputs históricos). Esto disparó rotación inmediata.

## Lo que se ejecutó

### 1. Rotación de tokens (David, manual)
- Generó nuevos integration tokens en portal Notion para ambos bots Rick + Supervisor.
- Backup `~/.config/openclaw/env` → `env.backup_pre_notion_rotation_20260505` (chmod 600).
- Editó `~/.config/openclaw/env` con `nano` reemplazando los 2 valores. Ambos nuevos: `len=50 prefix=ntn_`.

### 2. Worker restart + smoke test (David)
- `systemctl --user restart umbral-worker` → active running.
- Health check: ambos bots responden OK con tokens nuevos.
- Smoke test: `worker → notion.search_databases` retorna 2 DBs.

### 3. Gateway patch + restart (Copilot Chat via SSH)
**Hallazgo:** `~/.config/systemd/user/openclaw-gateway.service` tiene `EnvironmentFile=-/home/rick/.openclaw/gateway.systemd.env` (con solo 8 vars Azure/Google) MÁS ~15 líneas `Environment=KEY=<plain-secret>` hardcoded directo, incluyendo `Environment=NOTION_API_KEY=<old>` y `Environment=NOTION_SUPERVISOR_API_KEY=<old>`. systemd: las directivas `Environment=` posteriores tienen precedencia sobre `EnvironmentFile=` para misma key → el gateway estaba ignorando el env file y cargando tokens VIEJOS revocados.

**Patch aplicado** (quirúrgico, NO migración masiva):
```bash
# 1. Backup chmod 600 del .service
# 2. source ~/.config/openclaw/env (cargar tokens nuevos a vars de shell)
# 3. awk reemplazo IN-PLACE de las 2 líneas Environment=NOTION_API_KEY= y Environment=NOTION_SUPERVISOR_API_KEY= con los nuevos valores
# 4. Validaciones: line count 79=79, count NOTION_API_KEY=1 line, count NOTION_SUPERVISOR_API_KEY=1 line
# 5. mv tmp → .service, chmod 600
# 6. systemctl --user daemon-reload && systemctl --user restart openclaw-gateway
# 7. Health: gateway "ready", port 18789 LISTEN, telegram bot conectado, heartbeat activo
```

Tokens nunca impresos en stdout — sed/awk operaron via shell vars; verificación por length+prefix+grep counts.

### 4. Scrub de leak surfaces (Copilot Chat via SSH)

**Archivos shredded** (tenían tokens recién rotados en plano):
- `~/.config/openclaw/env.save`, `env.save.1`, `env.save.2` (nano backups, marzo 2026)
- `~/.config/openclaw/env.backup_pre_notion_rotation_20260505` (mi backup pre-rotación)
- `~/.config/systemd/user/openclaw-gateway.service.bak_pre_notion_rotation_20260505` (backup del .service pre-patch)

**Archivos scrubbed in-place** con `sed -i -E 's/(secret|ntn)_[A-Za-z0-9]{40,}/[REDACTED-ROTATED-20260505]/g'` y luego `.bak_pre_scrub` shredded:
- `/home/rick/.openclaw/agents/rick-orchestrator/sessions/5402c8fb-e647-48ab-be2f-13d4bddafb0b.jsonl`
- `/home/rick/.openclaw/agents/rick-orchestrator/sessions/e608726b-4bea-4c6c-bc54-60ea2840af9d.jsonl`
- `/home/rick/.openclaw/agents/rick-orchestrator/sessions/e608726b-4bea-4c6c-bc54-60ea2840af9d.trajectory.jsonl`
- `/home/rick/.openclaw/agents/rick-ops/sessions/a4d2168d-c87c-4d9a-b7c4-2d5532359222.jsonl`

Verificación: `before=1 after=0` para cada uno.

### 5. Verificación final

`grep -rIlE "secret_[A-Za-z0-9]{40,}|ntn_[A-Za-z0-9]{40,}" ~/.openclaw ~/.config` → solo:
- `~/.config/openclaw/env` (tokens nuevos vivos, esperado)
- `~/.config/systemd/user/openclaw-gateway.service` (tokens nuevos vivos, esperado)
- `~/.config/openclaw/env.pre_vm_tunnel_fix_20260315` (root:root 644, requiere sudo — pendiente David)
- 27 archivos `~/.config/openclaw/env.bak.*` (rick:rick 600 — ver §pendientes)

## Pendientes (NO scope de esta task — tasks futuras)

### Hardening masivo de backups (task 008 sugerida)
27 archivos `~/.config/openclaw/env.bak.*` (de marzo 2026, rick:rick 600) tienen:
- Tokens Notion VIEJOS REVOCADOS (riesgo Notion = 0).
- Secrets aún VIVOS de otros servicios: `GOOGLE_CALENDAR_REFRESH_TOKEN`, `GOOGLE_GMAIL_REFRESH_TOKEN`, `GOOGLE_*_CLIENT_SECRET`, `HOSTINGER_API_TOKEN`, `TAVILY_API_KEY`, `LINEAR_API_KEY`, `N8N_API_KEY`, `GPT_RICK_API_KEY` (Azure), `GOOGLE_API_KEY_*`, etc.
- Riesgo: bajo (perms 600, único user con SSH es David), pero quita-y-pon de superficie.
- Acción sugerida: shred masivo con whitelist (mantener máximo 1-2 backups recientes para rollback emergency), o rotar TODOS los secrets ahí + shred. David decide.

### Hardening estructural del .service (task 009 sugerida)
`openclaw-gateway.service` sigue siendo dumping ground: ~15 secrets como `Environment=KEY=<plain>` líneas en un unit file (default 644 readable). Patrón correcto: migrar todos los `Environment=<secret>=` a `~/.openclaw/gateway.systemd.env` (chmod 600) y dejar en el `.service` solo operacionales (PATH, HOME, OPENCLAW_*). Esto también implicaría rotación de los otros 13 secrets para invalidar las copias en disco.

### Backup root-owned
`~/.config/openclaw/env.pre_vm_tunnel_fix_20260315` (root:root 644) → David ejecuta `sudo shred -u ~/.config/openclaw/env.pre_vm_tunnel_fix_20260315` cuando le quede tiempo.

## Lecciones (memoria repo)

1. systemd unit `Environment=` posterior tiene precedencia sobre `EnvironmentFile=` para la misma key.
2. Un `.service` con secretos como `Environment=` es un leak surface estructural — los secretos deben vivir en `EnvironmentFile=` chmod 600.
3. Tool outputs (jsonl session logs) loggean tokens en plano cuando los handlers fallan o muestran request bodies — auditar antes de rotar para conocer alcance, scrubbear después.
4. `nano` deja `.save`, `.save.1`, `.save.2` con contenido completo — incluir en hardening pattern.
5. Patrón seguro de patch in-place sin imprimir tokens: cargar a vars de shell con `set -a; source env; set +a`, usar `awk -v` para sustitución, validar por counts/lengths/prefixes.
