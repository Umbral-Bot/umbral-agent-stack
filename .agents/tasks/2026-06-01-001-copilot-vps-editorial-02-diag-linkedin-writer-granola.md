---
id: "2026-06-01-001"
title: "EDITORIAL-02 — Diag read-only: rick-linkedin-writer FailoverError + silencio granola.classify_raw"
status: assigned
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
