---
id: "2026-05-04-002"
title: "Copilot VPS — O14.0 Diagnóstico de versión OpenClaw (baseline pre-upgrade)"
status: assigned
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: medium
sprint: Q2-2026
created_at: 2026-05-04T00:00:00-03:00
updated_at: 2026-05-04T00:00:00-03:00
---

## Contexto previo (leer antes de empezar)

Esta tarea cierra el sub-objetivo **O14.0** del Plan Q2-2026 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` §O14, agregado 2026-05-04 commit `408b91a`).

O14 (Mantenimiento OpenClaw) se incorporó al plan tras detectar que el plan menciona OpenClaw 20+ veces como runtime pero **nunca como target de upgrade**. O14.0 es el primer paso: producir un baseline factual de la versión actual antes de decidir upgrade vs hold (O14.1).

Antes de empezar:

1. `cd ~/umbral-agent-stack && git pull origin main`.
2. Releer `.github/copilot-instructions.md` — sección **"VPS Reality Check Rule"** (commit `fbc5dae`).
3. Esta tarea es **lectura pura** (no instala, no actualiza, no modifica `~/.openclaw/openclaw.json`). El upgrade en sí es O14.2, una tarea futura separada.

## Objetivo

Producir el archivo de baseline:

`umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md`

con: versión instalada, fuente de instalación (npm global vs pip vs binario), versión upstream actual, delta de releases entre instalada y upstream, breaking changes anunciados que afecten cómo Umbral usa OpenClaw (gateway + dispatcher + nodos + skills).

## Procedimiento mínimo (NO saltar pasos)

```bash
# 1. Versión y origen del binario en uso
ssh rick@<vps> "which openclaw && openclaw --version"
ssh rick@<vps> "ls -la \$(which openclaw)"

# 2. Si es npm global, listar contexto npm
ssh rick@<vps> "npm ls -g --depth=0 2>/dev/null | grep -i openclaw"
ssh rick@<vps> "npm view <paquete-openclaw> version time --json 2>/dev/null | head -50"

# 3. Si es pip, equivalente
ssh rick@<vps> "pip show openclaw 2>/dev/null || pip3 show openclaw 2>/dev/null"

# 4. Estado actual del runtime (NO modificar nada)
ssh rick@<vps> "openclaw status --all"
ssh rick@<vps> "openclaw models status 2>&1 | head -30"
ssh rick@<vps> "systemctl --user status openclaw-gateway --no-pager 2>&1 | head -20"

# 5. Buscar release notes upstream
#    (en GitHub del proyecto OpenClaw: comparar tag instalado vs latest)
#    Capturar cantidad de releases entre ambos y leer changelog/breaking-changes.

# 6. Snapshot del openclaw.json actual SOLO para referencia (no editar)
ssh rick@<vps> "wc -l ~/.openclaw/openclaw.json && md5sum ~/.openclaw/openclaw.json"
```

## Criterios de aceptación

- [ ] Archivo `umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md` existe en `origin/main` con las siguientes secciones:
  - **Versión instalada en VPS** (output literal de `openclaw --version` + path del binario + manager: npm/pip/otro).
  - **Versión upstream actual** (tag/release más reciente del proyecto upstream + fecha).
  - **Delta** (cantidad de releases entre instalada y upstream + lista resumida).
  - **Breaking changes relevantes** que afecten: gateway, dispatcher CLI flags, formato `openclaw.json`, comandos `status`/`models`/`sessions_list`. Si no hay breaking changes que afecten a Umbral, decirlo explícito.
  - **Health snapshot pre-upgrade** (output de `openclaw status --all` + `systemctl --user status openclaw-gateway`).
  - **Recomendación para O14.1** (insumo, no decisión): (a) upgrade ya, (b) upgrade tras O13.1 estable, (c) hold con razón. La decisión final la toma David.
- [ ] El archivo separa explícitamente **"Repo dice X" vs "VPS muestra Y"** si encuentra divergencia (ej: pinned version en algún script vs versión real instalada).
- [ ] Commit + push a `main` con mensaje `audit(O14.0): openclaw version baseline 2026-05-04`.
- [ ] Status de esta tarea actualizado a `done` con link al commit del audit en el `## Log`.

## Antipatrones que esta tarea prohíbe

- ❌ Ejecutar el upgrade (`npm i -g openclaw@latest` o equivalente). Eso es O14.2, **no esta tarea**.
- ❌ Modificar `~/.openclaw/openclaw.json`, `openclaw-gateway.service`, o cualquier unit systemd.
- ❌ Reportar versión upstream sin verificar (asumiendo que latest es X). Confirmar con `npm view` o GitHub releases.
- ❌ Cerrar la tarea sin el archivo de audit committeado a `origin/main`.
- ❌ Saltar el health snapshot pre-upgrade (necesario para O14.2 rollback si pasa a ejecución).

## Bloqueantes potenciales

- Si `openclaw --version` no existe (CLI no responde a `--version`): documentar el comando alternativo usado y por qué.
- Si el upstream no tiene releases públicas o no es identificable (binario propietario): documentarlo y proponer estrategia alternativa para O14.1.

## Dependencias

- **Bloquea:** O14.1 (decisión upgrade vs hold), O14.2, O14.3, O14.4.
- **No bloquea:** O13.1 (Mission Control dashboard puede arrancar en paralelo — son carriles independientes per plan §O14 alcance estricto).
- **Independiente de:** task `2026-05-04-001` (esa es debugging de cron, no plataforma OpenClaw).

## Log

- **2026-05-04** (copilot-chat-notion-governance): Tarea creada como delegación de O14.0 del Plan Q2. Aplicada skill `delegate-to-copilot-vps`. Justificación de delegación: O14.0 requiere SSH real a VPS (`openclaw --version`, `openclaw status --all`, `systemctl --user status`), Copilot Chat no tiene SSH. Owner per plan §3.5: O14 → `umbral-agent-stack`, ejecutado por Copilot VPS. Trigger: usuario pidió "O14" tras cierre de O13.0 (ADR-009 commit `1c6d5da`).
