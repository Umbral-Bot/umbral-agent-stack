---
id: "2026-06-01-001"
title: "G-D1a — Elevar maxSpawnDepth a 2 en openclaw.json (VPS), patch mínimo, sin restart"
status: done
assigned_to: copilot
created_by: cursor
priority: high
sprint: W-A
created_at: 2026-06-01T05:21:00-04:00
updated_at: 2026-06-01T05:27:00-04:00
owner: copilot-vps
reviewer: cursor
phase: Q2-v2-D1
depends_on:
  - notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md (D1.1 / gate G-D1a)
  - notion-governance/docs/audits/2026-05-30-q2-tournament-multiagent-openclaw-diagnostic.md (B2)
  - docs/79-tournament-protocol-openclaw-native.md (§5 pre-condición maxSpawnDepth >= 2)
---

## Objetivo

Aplicar el **patch mínimo** que eleva `agents.defaults.subagents.maxSpawnDepth` a `2` en
`~/.openclaw/openclaw.json` (VPS), pre-condición dura de O7/D1.1 para que la jerarquía
`main → rick-orchestrator → 6 workers` pueda spawnear (depth >= 2) en torneos/multi-agente.

Cierra el gate **G-D1a** del Plan Q2 v2 §6. Es WRITE sobre runtime de producción.

## Superficie y rol

- **Ejecuta:** Copilot-VPS (skill `openclaw-vps-operator`). Cursor (Windows) NO ejecuta runtime VPS.
- **NO restart** del gateway en este turno. El restart para tomar efecto es un gate separado
  (`G-D1a-RESTART`) que requiere autorización explícita de David en el mismo mensaje.

## Preflight repo (Copilot-VPS — obligatorio, primer paso)

Cursor debe haber hecho **push a `main`** antes de este handoff. En VPS:

```bash
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-001-gd1a-set-maxspawndepth.md && echo TASK_FILE_OK || echo TASK_FILE_MISSING
```

Si `TASK_FILE_MISSING` → STOP y reportar a Cursor (falta sync).

## Autorización de David (citada textualmente)

> "Superficie: VPS (Copilot-VPS). WRITE autorizado por David para patch minimo en openclaw.json."
> (sesión 2026-06-01, /goal G-D1a)

Restart NO autorizado este turno (David: "NO reiniciar openclaw-gateway.service salvo David
autorice G-D1a-RESTART en el mismo mensaje").

## Contexto D0.2-POST-C9

- 8 agentes: `main` (default) → `rick-orchestrator` → 6 workers vía `allowAgents`.
- `maxSpawnDepth` **NO seteado** en config → default implícito OpenClaw (probablemente 1).
- Worker healthy, gateway activo, sin restart previo requerido.
- C9-05 cerrado (VM OpenClaw 2026.5.28, gateway VPS sin cambios, 1002 resuelto;
  1008 auth pairing pendiente fuera de scope).

## Preflight obligatorio (read-only primero)

```bash
hostname && whoami                         # confirmar VPS + rick
systemctl --user is-active openclaw-gateway
test -f ~/.openclaw/openclaw.json && echo CONFIG_OK
mkdir -p ~/.coord-ag-evidence/G-D1a
cp -a ~/.openclaw/openclaw.json ~/.coord-ag-evidence/G-D1a/openclaw.json.bak.$(date +%Y%m%d%H%M)
```

Estado actual (sin exponer secretos):

```bash
python3 - <<'PY'
import json, os
p=os.path.expanduser("~/.openclaw/openclaw.json")
d=json.load(open(p, encoding="utf-8"))
ag=d.get("agents",{})
for a in ag.get("list",[]):
    if a.get("id") in ("main","rick-orchestrator"):
        print(a.get("id"), "subagents=", a.get("subagents"))
print("defaults.subagents=", ag.get("defaults",{}).get("subagents"))
PY
```

Verificar default efectivo si el valor es ambiguo (read-only): `openclaw doctor` / logs
con `journalctl --user -u openclaw-gateway` filtrando secretos.

## Patch mínimo (solo si procede)

- Preferir `agents.defaults.subagents.maxSpawnDepth = 2`.
- Si no existe `agents.defaults.subagents`, crear el bloque mínimo (solo esa clave).
- `maxChildrenPerAgent` / `maxConcurrent`: **NO tocar** salvo que el read muestre que faltan
  y el spine lo exija. El protocolo (`docs/79-...md §1` invariante) ya asume
  `maxChildrenPerAgent: 5`; no re-declarar si ya existe.
- **NO** cambiar `model.primary`. **NO** tocar `allowAgents` salvo que el patch lo exija.
- Mostrar **diff** antes de aplicar; aplicar solo tras confirmar diff razonable.

## Post-patch

```bash
python3 -c 'import json; json.load(open("/home/rick/.openclaw/openclaw.json"))' && echo JSON_OK
grep -n maxSpawnDepth ~/.openclaw/openclaw.json || true
```

## Criterios de aceptación

- [x] Backup creado en `~/.coord-ag-evidence/G-D1a/openclaw.json.bak.202606010525` (32389 bytes).
- [x] Estado previo documentado: `agents.defaults.subagents` AUSENTE → `maxSpawnDepth` `<NOT SET>` (default implícito ~1).
- [x] Diff mostrado y razonable (única adición `subagents.maxSpawnDepth: 2`; sin tocar tokens/modelos/allowAgents).
- [x] `JSON_VALID` post-patch; `maxSpawnDepth = 2` confirmado.
- [x] Gateway NO reiniciado (`active` desde 2026-05-21 11:15:35, sin cambio tras patch 05:25).
- [x] `secret-output-guard` respetado (sin tokens crudos en el reporte).
- [x] VEREDICTO emitido: `G_D1a_PATCH_OK`.
- [x] Evidencia: backup + reporte VEREDICTO de Copilot-VPS (sesión 2026-06-01 05:25).

## Stop conditions

Secreto en stdout · diff fuera de scope · servicio crash · JSON inválido (rollback inmediato
con backup) · superficie no-VPS · falta backup antes de aplicar.

## Entregable (formato de reporte)

```
VEREDICTO: <G_D1a_PATCH_OK | G_D1a_BLOCKED | G_D1a_NOOP_DEFAULT_ALREADY_2>
backup_path: ~/.coord-ag-evidence/G-D1a/openclaw.json.bak.<ts>
default_previo: <valor real o "ausente">
diff_resumido: <solo líneas de maxSpawnDepth>
maxSpawnDepth_final: <2 | sin cambio>
requiere_restart_para_efecto: <sí/no + por qué>
```

## Log
### [cursor] 2026-06-01 05:21
Handoff creado como D1.1 / gate G-D1a del Plan Q2 v2. WRITE autorizado por David (patch mínimo).
Restart explícitamente NO autorizado este turno (gate separado G-D1a-RESTART). Ejecuta Copilot-VPS
bajo skill `openclaw-vps-operator`. Al recibir VEREDICTO, Cursor capitaliza en D0.3/D1 dashboard.

### [copilot-vps] 2026-06-01 05:25 — VEREDICTO G_D1a_PATCH_OK
Superficie VPS `srv1431451`/`rick` confirmada. Preflight: gateway `active`, `CONFIG_OK`,
backup `openclaw.json.bak.202606010525` (32389 bytes). Estado previo: `agents.defaults` existe
pero `subagents` ausente → `maxSpawnDepth` `<NOT SET>`. Patch: única adición
`agents.defaults.subagents.maxSpawnDepth: 2` (indent 2-space preservado). `JSON_VALID`; diff
semántico = 1 bloque. **NO restart** (gateway sin cambio, activo desde 2026-05-21 11:15:35).
requiere_restart_para_efecto: **SÍ** → config en disco con depth=2, runtime aún en default
hasta `G-D1a-RESTART`. secret-output-guard respetado.

### [cursor] 2026-06-01 05:27 — capitalización
Cerrada como done. Board + spine D1.1 actualizados; outcome gobernado D0.3 redactado
(`notion-governance/docs/audits/2026-05-30-vps-reality-check-q2v2-d0.md`) con sección G-D1a
verificada y campos D0.2 (Granola/worker-drift/provider) marcados PENDING hasta el paste completo.
Boundary de runtime NO cambia hasta el restart → registry/policy-05 sin tocar todavía.
