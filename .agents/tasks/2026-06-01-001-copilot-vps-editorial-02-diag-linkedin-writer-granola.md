---
id: "2026-06-01-001"
title: "EDITORIAL-02 — Diag read-only: rick-linkedin-writer FailoverError + silencio granola.classify_raw"
status: done
assigned_to: copilot
created_by: cursor-chat-editorial-sistema2
priority: high
sprint: Q2-2026
created_at: "2026-06-01"
updated_at: "2026-06-01"
---

## Contexto previo

Diagnóstico **read-only estricto** del flujo editorial (Sistema 2 — LinkedIn,
human-in-the-loop). Continúa el runtime check
[`2026-05-19-001`](2026-05-19-001-copilot-vps-core-q2-sistemas-runtime-check.md)
(status `done`, 2026-05-20).

Releé la **VPS Reality Check Rule** en `.github/copilot-instructions.md`
(commit `fbc5dae`, 2026-05-04) antes de empezar: verificar runtime con
SSH/`journalctl`/`systemctl`, no con `grep` al repo.

### Hallazgos EDITORIAL-01 (a confirmar en VPS)

- `rick-linkedin-writer` falla cada ~2h: `FailoverError: provider rejected
  schema or tool payload` (provider `azure-openai-responses` / modelo
  `gpt-5.4`).
- `granola.classify_raw`: última ejecución **2026-05-11**, cero invocaciones
  en ~3 semanas (consistente con el HTTP 500 del poller V2 reportado en
  `2026-05-19-001` §Sistema 3).
- `discovery-publish-cron` aparece pausado y con script faltante (ruido en
  log) — verificar si es ruido o un fallo real.

## Objetivo

Producir un diagnóstico read-only que responda:

A. Origen del trigger ~2h de `rick-linkedin-writer` (archivo/ruta exacta).
B. Causa probable del `FailoverError` (schema vs tools vs modelo).
C. Por qué `granola.classify_raw` no se invoca (código vs no hay filas vs flag).
D. Opciones EDITORIAL-03 ordenadas (sin ejecutar): pausar lane vs fix schema
   vs redeploy skill vs reactivar path Granola.
E. Confirmaciones de que todo el pase fue read-only.

**Scope guard:** este pase es solo `rick-linkedin-writer` + `granola.classify_raw`.
No mezclar con C9/D0 salvo que la evidencia muestre dependencia directa de
Granola en el flujo editorial.

## Procedimiento mínimo

```bash
cd ~/umbral-agent-stack && git pull origin main

# === FASE 1 — Localizar scheduler linkedin-writer ===
grep -riE 'linkedin-writer|rick-linkedin|session:agent:rick-linkedin' \
  ~/.openclaw ~/.config/openclaw ~/umbral-agent-stack/openclaw 2>/dev/null \
  | grep -iv node_modules | head -40
find ~/.openclaw -maxdepth 4 -type f \( -name '*.json' -o -name '*.yaml' -o -name '*.md' \) 2>/dev/null \
  | xargs grep -l 'linkedin-writer' 2>/dev/null | head -15
ls -la ~/.openclaw/agents/rick-linkedin-writer 2>/dev/null \
  || ls -la ~/.openclaw/workspace/agents 2>/dev/null | head -20

# === FASE 2 — Último error completo (REDACTAR secretos) ===
journalctl --user --since "48 hours ago" --no-pager 2>/dev/null \
  | grep -iE 'rick-linkedin-writer|FailoverError|schema|tool payload' \
  | tail -30 | sed -E 's/(Bearer |sk-|ghp_)[^ ]+/\1[REDACTED]/g'

# === FASE 3 — Config agente linkedin-writer (SIN secretos) ===
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.openclaw/openclaw.json")
d = json.load(open(p, encoding="utf-8"))
for a in d.get("agents", {}).get("list", []):
    if a.get("id") == "rick-linkedin-writer":
        safe = {k: a.get(k) for k in ("id", "model", "tools", "skills", "subagents")}
        print(json.dumps(safe, indent=2)[:2000])
PY

# === FASE 4 — Por qué Granola dejó de invocarse ===
grep -n 'classify_raw\|granola' ~/umbral-agent-stack/dispatcher/notion_poller.py | head -30
grep -n 'classify_pending_granola\|GRANOLA' ~/umbral-agent-stack/dispatcher/notion_poller.py | head -20
tail -n 200 /tmp/notion_poller.log | grep -iE 'granola|classify|skip|0 classified' | tail -40

# === FASE 5 — Repo vs runtime writer skill ===
diff -q ~/umbral-agent-stack/openclaw/workspace-agent-overrides/rick-linkedin-writer/ \
        ~/.openclaw/workspace/agents/rick-linkedin-writer/ 2>/dev/null \
  || echo "diff paths N/A"
ls ~/umbral-agent-stack/openclaw/workspace-templates/skills/linkedin-david/ 2>/dev/null
ls ~/.openclaw/workspace/skills/linkedin-david/ 2>/dev/null \
  || echo "skill not deployed in workspace"
```

## Criterios de aceptación

- [ ] Entregable cierra con `VEREDICTO: EDITORIAL_02_DIAG_READY` o
      `EDITORIAL_02_BLOCKED`.
- [ ] Para A–E: bloque explícito **"Repo dice X" vs "VPS muestra Y"**.
- [ ] FASE 2 reporta el último `FailoverError` completo con secretos redactados.
- [ ] FASE 4 distingue las tres hipótesis de C (código roto vs sin filas vs
      flag) con evidencia, no suposición.
- [ ] D entrega opciones EDITORIAL-03 ordenadas por riesgo/impacto, **sin
      ejecutar ninguna**.
- [ ] E confirma: no fix, no restart, no publish, no edición de `openclaw.json`.

## Antipatrones que esta tarea prohíbe (stop conditions)

- ❌ Intentar cualquier fix, `restart`, redeploy o `publish`.
- ❌ Editar `~/.openclaw/openclaw.json` o cualquier config runtime.
- ❌ Imprimir tokens/credenciales en claro (siempre redactar).
- ❌ Declarar "está activo/roto" por `grep` al repo sin evidencia
      `journalctl`/log de runtime.
- ❌ Reactivar el path Granola o tocar C9/D0 en este pase.

Si algo requiere un write para confirmar la causa, **parar y reportar
`EDITORIAL_02_BLOCKED`** con el bloqueo exacto.

## Referencias

- Trigger: EDITORIAL-01 (hallazgos arriba) + `2026-05-19-001` §Sistema 2/3.
- Regla: `.github/copilot-instructions.md` — "VPS Reality Check Rule" (`fbc5dae`).
- Contrato de flujo editorial: `docs/ops/editorial-agent-flow.md`.
- Plan canal LinkedIn: `docs/plans/linkedin-publication-pipeline.md`.
- Skill de delegación: `notion-governance/.agents/skills/delegate-to-copilot-vps/SKILL.md`.

## Log

### 2026-06-01 — Creación (Cursor, Windows)

Tarea creada como handoff read-only a Copilot-VPS. Cursor (Windows) no ejecuta
en la VPS; diseña el diagnóstico. Pendiente: Copilot-VPS hace `git pull`,
ejecuta FASE 1–5, reporta hallazgos A–E en este Log separando repo-vs-VPS, y
cierra con el VEREDICTO. Ningún write autorizado en este pase.

### 2026-06-01 — Diagnóstico ejecutado (Copilot-VPS, READ-ONLY)

Ejecutado en la VPS real (`srv1431451`) sobre runtime vivo. `git pull origin
main` OK. Secretos redactados. Sin fix / restart / publish / edición de
`openclaw.json`. Único cambio en repo: frontmatter `status` + este Log.

> **Marco VPS Reality Check:** cada hallazgo separa **Repo dice X** (intención de
> diseño) vs **VPS muestra Y** (estado runtime verificado por journal/log/redis).

---

#### A — ¿Quién dispara a `rick-linkedin-writer` cada ~2h?

- **Repo dice X:** `~/.openclaw/cron/jobs.json` tiene 8 jobs; **ninguno** apunta
  a `rick-linkedin-writer` ni corre cada 2h. `agents.defaults.heartbeat =
  {"every":"1h"}` y el agente tiene `heartbeat: null` / `schedule: null` →
  por config heredaría 1h, no 2h.
- **VPS muestra Y:** la lane de `rick-linkedin-writer` dispara **cada 2h en
  punto a HH:09** (00:09, 02:09, 04:09 … confirmado en 48h de gateway journal).
  El trigger **no está en `cron/jobs.json`** ni coincide con el heartbeat
  default (1h). La cadencia 2h@:09 es **interna al binario `openclaw-gateway`**
  (npm-global, `--port 18789`), no observable como cron/timer de systemd.
- **Conclusión A:** el origen del disparo NO es un cron del repo ni el heartbeat
  configurable; es scheduling interno del gateway. Cualquier "pausa" de la lane
  requiere acción sobre el gateway, no sobre `cron/jobs.json`.

#### B — Causa raíz del `FailoverError`

- **Repo dice X:** el mensaje genérico de OpenClaw dice *"provider rejected the
  request schema or tool payload"* → sugiere mismatch de tools/schema.
- **VPS muestra Y:** el `rawError` real (redactado) es
  `400 Item with id 'rs_[REDACTED]' not found. Items are not persisted when
  'store' is set to false. Try again with 'store' set to true, or remove this
  item …`. Es el bug de **persistencia de reasoning-items de Azure OpenAI
  Responses API**: con `store=false`, los items de razonamiento cifrados
  (`rs_…`) no pueden referenciarse en el turno siguiente. **NO es** mismatch de
  schema/tools.
- **Alcance cross-agent (48h):** `FailoverError` por agente → orchestrator=52,
  rick-linkedin-writer=31, comm-director=24. Errores embebidos →
  `gpt-5.4 / azure-openai-responses`=48, `gpt-5.2-chat / azure-openai-responses`=17
  (y aparte `gemini-3.1-pro-preview / google-vertex`=48, falla distinta).
- **Conclusión B:** el `FailoverError` **no es específico del writer**; afecta a
  todos los agentes que usan `azure-openai-responses`. Raíz = `store=false` +
  reasoning items, no el payload de tools del writer.

#### C — ¿Por qué `granola.classify_raw` está en silencio desde 2026-05-11?

- **Repo dice X:** EDITORIAL-01 / `ops_log` → última invocación de
  `granola.classify_raw` el **2026-05-11T22:22:58**, hipótesis previa = HTTP 500
  del poller V2. Comentario en `~/.config/openclaw/env` (línea aparte):
  *"# DISABLED 2026-05-22 (F4 fix granola-500): V1 DB retirada, ver REPORT.md"*.
- **VPS muestra Y:**
  - `NOTION_GRANOLA_DB_ID` está **activo** (env línea 54, sin comentar).
  - El `openclaw-dispatcher` corre desde 2026-05-28; el path V2 classify se
    ejecuta **cada ciclo de poll (~75s)**.
  - Log vivo (`/tmp/notion_poller.log`, 139 MB, últimas horas) repite de forma
    consistente: **`V2 classify scan: 10 scanned, 0 classified, 10 skipped,
    0 errors`**.
  - Redis: **10 keys** `umbral:notion_poller:classified:*` y **0 keys**
    `umbral:notion_poller:classify_fail:*`.
  - **No hay HTTP 500 actual** del poller V2 (0 errors sostenido).
- **Conclusión C (hipótesis distinguidas):**
  - ❌ *Código roto* — descartado: el scan corre con `0 errors`.
  - ❌ *DB vacía / sin filas* — descartado: `10 scanned` por ciclo.
  - ❌ *Flag deshabilitado / DB apuntando a V1 retirada* — descartado: DB id
    activo y la lectura devuelve 10 páginas.
  - ✅ **Causa real:** las 10 páginas escaneadas están **todas ya clasificadas**
    (presentes en el set de dedup Redis `classified:`, `estado_agente` en
    `{Procesada, Revisión requerida}`), por eso `10 skipped / 0 classified`. El
    HTTP 500 que motivó el "fix" del 2026-05-22 **ya no ocurre**. El silencio de
    `classify_raw` **no es una falla**: es **ausencia de input nuevo** dentro de
    la ventana de scan (`V2_SCAN_LIMIT=10`). La última página realmente nueva se
    clasificó el 2026-05-11 y desde entonces no entraron páginas Granola nuevas
    al top-10 del scan.
  - ⚠️ **Caveat (riesgo de diseño, no falla actual):** el scan sólo lee las
    primeras 10 páginas (`V2_SCAN_LIMIT=10`). Si entraran páginas nuevas más
    allá de esa ventana, podrían no verse. No se confirmó existencia de páginas
    pendientes fuera de la ventana (eso requeriría query adicional a Notion,
    fuera del alcance read-only).

#### Hallazgo lateral — Worker 503 / VM OFFLINE

- **VPS muestra Y:** journal `openclaw-dispatcher` → `503 Service Unavailable`
  en `http://127.0.0.1:8088/run` (May 31 14:00 y 20:00, varias tareas), y
  `❌ VM declared OFFLINE after 2 consecutive failures` (Jun 01 05:30:41,
  health timeout a `100.109.16.40:8088`). GET /health 200 OK a 00:36 y 04:48.
- **Relevancia:** si en algún ciclo hubiera una página Granola nueva para
  clasificar mientras el worker está 503/OFFLINE, `wc.run("granola.classify_raw")`
  fallaría. No es la causa del silencio actual (no hay input nuevo), pero es un
  riesgo latente para EDITORIAL-03.

#### FASE 5 — Repo vs runtime (skill / overrides)

- **Skill `linkedin-david`:** `openclaw/workspace-templates/skills/linkedin-david/SKILL.md`
  (repo) **IDÉNTICO** a `~/.openclaw/workspace/skills/linkedin-david/SKILL.md`
  (runtime). Sin drift.
- **Overrides agente:** `openclaw/workspace-agent-overrides/rick-linkedin-writer/`
  vs `~/.openclaw/workspace/agents/rick-linkedin-writer/` → diff N/A (path no
  presente en uno de los dos lados; no hay drift detectable).

#### D — Opciones para EDITORIAL-03 (ordenadas por riesgo/impacto — SIN ejecutar)

1. **Pausar la lane de `rick-linkedin-writer`** *(menor riesgo)* — detiene el
   ruido de `FailoverError` cada 2h mientras se resuelve B. Requiere acción
   sobre el gateway (el trigger es interno, no cron). Reversible.
2. **Fix raíz B: `store=true` para `azure-openai-responses`** *(impacto alto,
   beneficia a TODOS los agentes afectados: orchestrator/writer/comm-director)* —
   ajuste de config del provider Responses para persistir reasoning items.
   Requiere editar runtime config (autorización explícita de David).
3. **Endurecer disponibilidad del worker** — mitigar 503/VM OFFLINE
   (`100.109.16.40:8088`) para que un futuro `classify_raw` no falle. Riesgo
   medio, toca worker/VM.
4. **Reactivar / validar el path Granola end-to-end** *(mayor cuidado)* — sólo
   si se confirma que existen páginas Granola pendientes fuera de la ventana de
   scan o se decide ampliar `V2_SCAN_LIMIT`. Hoy el path está sano pero ocioso;
   reactivar sin input nuevo no aporta. **Bloqueado por la stop-condition C9/D0.**

#### E — Confirmación READ-ONLY

- ✅ Sin fix, sin restart, sin redeploy, sin publish.
- ✅ Sin editar `~/.openclaw/openclaw.json` ni ningún config runtime.
- ✅ Secretos/tokens redactados (`rs_…`, Bearer, etc.).
- ✅ Estados runtime afirmados sólo con evidencia `journalctl` / log vivo /
  `redis-cli`, no por grep al repo.
- ✅ Path Granola NO reactivado; C9/D0 no tocados.
- ✅ Único cambio en repo: `status` + este Log (`git status` limpio salvo este
  archivo de tarea).

---

**VEREDICTO: EDITORIAL_02_DIAG_READY**
