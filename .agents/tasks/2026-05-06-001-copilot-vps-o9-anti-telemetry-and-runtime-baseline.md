---
id: "2026-05-06-001"
title: "Copilot VPS — Cerrar O9 lado VPS (anti-telemetría Anthropic) + baseline runtime check post-burn O7/O11/O16"
status: assigned
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: 2026-05-06T00:00:00-03:00
updated_at: 2026-05-06T00:00:00-03:00
---

## Contexto previo (CRÍTICO leer primero)

Esta tarea fue creada por Copilot Chat trabajando en `notion-governance`. Antes de empezar:

1. **`git pull origin main`** en `umbral-agent-stack` (en VPS, en `/home/rick/umbral-agent-stack`).
2. **Releer** `.github/copilot-instructions.md` — sección **"VPS Reality Check Rule"** (commit `fbc5dae`, 2026-05-04). El repo refleja intención; la VPS refleja realidad.
3. Leer también el runbook nuevo: `runbooks/runbook-anthropic-telemetry-off.md` (referenciado por O9 del Plan Q2-2026).

### Estado del burn de Copilot Chat (lado tarro / repo) que hay que validar/complementar

Sesión 2026-05-06 cerró/avanzó cinco objetivos del Plan Q2-2026 desde el repo:

| Obj | Lo que se hizo en el repo/tarro | Qué falta validar/hacer en VPS |
|---|---|---|
| **O7.0** | Spike subagents OpenClaw + tournament protocol promovido a ADR-017. Commit `aecc68c` + `32558a3c`. | Confirmar que ningún cambio de protocolo rompió el gateway/worker (smoke test). |
| **O16.0** | Modelo organizacional 5 áreas + 4 gerencias + N subagents promovido a ADR-017 (commit `4117dfb6`). Gaps 1+2 confirmados en `registry/agents-canonical.yaml` (commit `3a10993`). | Confirmar que `registry/agents-canonical.yaml` parsea OK en el host (yaml válido) y no rompe ningún consumer si lo hubiera. |
| **O11 fase 2** | 8 proyectos `Activos con bloqueos` triageados vía Notion MCP (5 en pausa, 1 re-scopeado, 2 mantenidos). Commit `2ec5c0f`. | No requiere VPS (es Notion runtime puro). Ignorar. |
| **O9** | PowerShell `$PROFILE` del tarro creado con env vars defensivas Anthropic (`ANTHROPIC_TELEMETRY=0`, `DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `TELEMETRY_DISABLED=1`). Commit `8c21d01`. | **Aplicar las MISMAS env vars en `~/.bashrc` del usuario `rick` en VPS** + auditar si hay alguna superficie Anthropic activa en VPS (Claude Code CLI, Claude Desktop, MCPs Anthropic). |
| **O8b.0** (vieja) | Bloqueo Google creds Granola pendiente, no es scope de esta tarea. | Solo reportar status si lo ves en logs, no investigar. |

## Objetivo

Dos bloques en orden estricto:

### Bloque A — Cerrar O9 lado VPS (prioritario)

Aplicar las env vars defensivas anti-telemetría Anthropic en `~/.bashrc` del usuario `rick` (paralelo de lo que ya se hizo en el `$PROFILE` del tarro de David), auditar si hay alguna superficie Anthropic real corriendo en VPS, y reportar.

### Bloque B — Baseline runtime check post-burn (verificación)

Snapshot de los servicios runtime para confirmar que el burn de hoy NO degradó nada en VPS:

- `umbral-worker.service` (FastAPI 127.0.0.1:8088).
- `openclaw-dispatcher.service`.
- `openclaw-gateway.service` (npm-global binary, puerto 18789).
- Granola pipeline (cron/timer + último write a Notion).
- Carga última de `registry/agents-canonical.yaml` (¿algún proceso lo lee y se rompió?).

## Procedimiento mínimo (NO saltar pasos)

### Bloque A — O9 anti-telemetría VPS

```bash
# A.0 — Sincronizar y leer regla
ssh rick@<vps>
cd ~/umbral-agent-stack && git pull origin main
sed -n '/VPS Reality Check/,/Related Repositories/p' .github/copilot-instructions.md
cat runbooks/runbook-anthropic-telemetry-off.md

# A.1 — Auditar superficies Anthropic instaladas en VPS
which claude 2>/dev/null
which claude-code 2>/dev/null
ls -la ~/.config/claude/ 2>/dev/null
ls -la ~/.config/anthropic/ 2>/dev/null
ls -la ~/.claude/ 2>/dev/null
# Procesos vivos (solo si hay binarios):
pgrep -af claude 2>/dev/null
pgrep -af anthropic 2>/dev/null
# MCPs declarados en algún lado:
grep -rE "anthropic|claude" ~/.config/ 2>/dev/null | grep -iE "telemetry|analytics|tracking|api_key" | head -30

# A.2 — Backup .bashrc y aplicar env vars defensivas
cp ~/.bashrc ~/.bashrc.bak.$(date +%F)
cat >> ~/.bashrc <<'EOF'

# === Anthropic anti-telemetry hard kill (O9 Plan Q2-2026, 2026-05-06) ===
# Defensive: NO afecta Codex/OpenAI/GitHub Copilot/Azure OpenAI.
# Ver runbooks/runbook-anthropic-telemetry-off.md
export ANTHROPIC_TELEMETRY=0
export DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
export TELEMETRY_DISABLED=1
# === fin anti-telemetry ===
EOF

# A.3 — Aplicar a sesión actual y validar
source ~/.bashrc
env | grep -E "ANTHROPIC_TELEMETRY|DISABLE_TELEMETRY|DO_NOT_TRACK|TELEMETRY_DISABLED"

# A.4 — Auditar systemd user units por si necesitan Environment= (los procesos
# de systemd no leen ~/.bashrc; si hay algún Anthropic corriendo bajo systemd
# habría que agregar Environment= en el unit file. Si no hay nada Anthropic
# bajo systemd, saltar este paso).
systemctl --user list-units --type=service --all | grep -iE "claude|anthropic" || echo "[OK] no hay units Anthropic bajo systemd"

# A.5 — Comparar repo vs VPS
# Si A.1 mostró 0 binarios/configs Anthropic, declarar:
#   "VPS no tiene superficie Anthropic activa; env vars aplicadas son defensivas/futuras."
# Si mostró algo, listar exactamente qué + acción.
```

### Bloque B — Baseline runtime check

```bash
# B.1 — Worker
curl -fsS http://127.0.0.1:8088/health && echo
systemctl --user status umbral-worker --no-pager | head -20

# B.2 — Dispatcher
systemctl --user status openclaw-dispatcher --no-pager | head -20
sudo journalctl --user-unit openclaw-dispatcher --since '6 hours ago' | tail -30

# B.3 — Gateway (npm-global, NO consume openclaw/** del repo)
systemctl --user status openclaw-gateway --no-pager | head -20
curl -fsS http://127.0.0.1:18789/health 2>&1 | head -5 || echo "[gateway no expone /health o está caído]"
which openclaw-gateway
openclaw-gateway --version 2>&1 | head -3

# B.4 — Granola pipeline
systemctl --user list-timers --all | grep -i granola
sudo journalctl --user-unit '*granola*' --since '24 hours ago' | tail -30
tail -200 ~/.config/umbral/ops_log.jsonl 2>/dev/null | jq 'select(.event | startswith("granola"))' | tail -10

# B.5 — Validar parseo de registry/agents-canonical.yaml
python3 -c "import yaml,sys; yaml.safe_load(open('$HOME/umbral-agent-stack/registry/agents-canonical.yaml')); print('[OK] yaml parseado')" 2>&1 \
  || echo "[FAIL] yaml inválido — bloquear deploy hasta que Copilot Chat lo arregle"
# Verificar también que agents-canonical-2.yaml (si existe) sigue válido:
ls ~/umbral-agent-stack/registry/agents-canonical*.yaml 2>/dev/null

# B.6 — Comparar repo vs VPS para los commits recientes
cd ~/umbral-agent-stack
git log --oneline -10
# Esperado: aparecen 4117dfb6 (gaps O16) y 32558a3c (tournament protocol).
# Si NO aparecen, el git pull falló o está en branch equivocado.
```

## Criterios de aceptación

### Bloque A
- [ ] Confirmaste lectura de "VPS Reality Check Rule" tras `git pull`.
- [ ] Listaste qué superficie Anthropic existe en VPS (binarios, configs, MCPs, procesos vivos). Si 0 → declararlo explícitamente.
- [ ] Aplicaste las 4 env vars defensivas a `~/.bashrc` con backup `.bashrc.bak.YYYY-MM-DD`.
- [ ] Validaste que `env | grep` muestra las 4 vars en la sesión actual.
- [ ] Documentaste si alguna unidad systemd necesita `Environment=` (o confirmaste que no hay).

### Bloque B
- [ ] Worker `/health` 200 + systemd `active (running)`.
- [ ] Dispatcher systemd `active (running)`, sin errores nuevos en últimas 6h.
- [ ] Gateway responde + version conocida (anotar).
- [ ] Granola: timer activo, último run reciente, último write a Notion (fecha).
- [ ] `agents-canonical.yaml` parsea OK con `yaml.safe_load`.
- [ ] `git log --oneline` muestra los 2 commits clave (`4117dfb6`, `32558a3c`).

### Reporte
- [ ] Cada hallazgo separa **"Repo dice X"** vs **"VPS muestra Y"**.
- [ ] Si encontrás algún servicio degradado o algún cambio del burn que rompió algo en VPS, NO lo arreglás todavía: registrás el síntoma + causa probable y dejás un plan de fix en el `## Log` para que David apruebe.

## Antipatrones que esta tarea explícitamente prohíbe

- ❌ "Leí el `$PROFILE` del tarro y se ve igual al `.bashrc`, así que está OK." → el tarro y la VPS son sistemas distintos, hay que aplicar y validar en VPS.
- ❌ "El runbook dice que apague Claude Desktop, pero el VPS no tiene UI, así que no aplica nada." → faltó auditar Claude Code CLI / MCPs / variables defensivas (ver A.1).
- ❌ "Worker `active (running)` significa healthy." → falta `/health` 200 + ausencia de errores recientes.
- ❌ Aplicar fixes opcionales sin pedir aprobación a David. Solo aplicar lo explicitado en el Procedimiento.

## Reportar resultados

Actualiza este mismo archivo:

1. `status: assigned` → `in_progress` al empezar, → `done` o `blocked` al cerrar.
2. Agregar bloque `### [copilot-vps] 2026-05-06 HH:MM` en `## Log` con hallazgos por bloque.
3. Si Bloque B detecta degradación atribuible a los commits del burn (`aecc68c`, `32558a3c`, `4117dfb6`, `3a10993`), poner `status: blocked` y pingear a David.

## Log

### [copilot-chat-notion-governance] 2026-05-06
Tarea creada desde sesión Copilot Chat en `notion-governance`. Trigger: David pidió validar/testear con Copilot VPS lo que se quemó en el día (O7.0, O16.0, O16 gaps 1+2, O11 fase 2, O9 80%) antes de seguir a O12. O9 quedó 80% en tarro; el 20% restante es el lado VPS + decisión de David sobre Claude Desktop UI (UI lo hace David manualmente, fuera de scope de esta tarea). Bloque B es defensivo: confirmar que los commits del día no degradaron runtime.
