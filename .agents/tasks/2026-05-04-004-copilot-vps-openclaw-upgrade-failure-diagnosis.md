---
id: 2026-05-04-004
title: OpenClaw upgrade FAILED via dashboard - diagnose & remediate (O14.2)
assigned_to: copilot-vps
created_by: copilot-chat
created_at: 2026-05-04
status: done
priority: high
related_plan: notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md (O14.2)
related_audit: umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md (commit 5d94e77)
related_tasks:
  - 2026-05-04-002 (O14.0 baseline, done)
  - 2026-05-04-003 (verify post-success, SUPERSEDED por esta task)
supersedes: 2026-05-04-003
---

# Contexto

David hizo click en "Update now" en el dashboard del gateway OpenClaw para upgrade `2026.4.9` → `2026.5.3`. El dashboard devolvió el siguiente error visible:

> **Update error: global install verify. See the gateway logs for the exact failure and retry once the cause is fixed.**

El banner "Update available v2026.5.3 (running v2026.4.9)" sigue presente, indicando que el swap no ocurrió y el runtime sigue en `2026.4.9`. No es un rollback — es una falla pre-swap durante el `npm install -g`.

# Objetivo

Diagnosticar la causa raíz del fallo de install global, decidir remediación, y reportar a David antes de cualquier intervención que altere el estado del runtime.

# Tareas

## 1. Confirmar runtime sigue en versión previa (sanity check)

```bash
ssh rick@<vps> "openclaw --version"
ssh rick@<vps> "systemctl --user status openclaw-gateway.service --no-pager | head -20"
```

Esperado: sigue `2026.4.9` y servicio `active (running)`. Si NO está active, escalar inmediatamente.

## 2. Capturar logs del gateway durante la ventana del intento de upgrade

```bash
# Ventana amplia desde poco antes del intento (David clickeó alrededor de 2026-05-04 ~hora local)
ssh rick@<vps> "sudo journalctl --user-unit openclaw-gateway.service --since '1 hour ago' --no-pager | tail -300"
```

Buscar específicamente:
- Líneas con `npm install`, `EACCES`, `EPERM`, `EEXIST`, `verify`, `integrity`, `ENOSPC`.
- Stack trace de Node si hubo crash del subprocess de upgrade.
- Mensajes de "global install" o "verify".

## 3. Inspeccionar estado de npm-global tras intento fallido

```bash
ssh rick@<vps> "ls -la /home/rick/.npm-global/lib/node_modules/openclaw/ | head -20"
ssh rick@<vps> "cat /home/rick/.npm-global/lib/node_modules/openclaw/package.json | grep version"
ssh rick@<vps> "npm ls -g --depth=0 2>&1 | grep -E 'openclaw|UNMET|extraneous'"
ssh rick@<vps> "df -h /home/rick /tmp /var"
```

Verificar:
- ¿Hay un dir `openclaw-XXXXX` temporal a medio bajar?
- ¿El `package.json` tiene la versión vieja o quedó parcialmente modificado?
- ¿Hay paquetes en estado UNMET / extraneous tras el intento?
- ¿Hay disco lleno?

## 4. Probar install manual reproducir el error con detalle

```bash
ssh rick@<vps> "npm install -g openclaw@2026.5.3 --verbose 2>&1 | tail -100"
```

⚠️ **NO ejecutes esto si el step 3 muestra estado inconsistente** — primero limpia o reportá.

Si corre, capturar el error exacto (probable causa: permisos, network, integrity check, peer dep).

## 5. Hipótesis comunes y check rápido por cada una

| Hipótesis | Check |
|---|---|
| Disk full | `df -h` (step 3) |
| npm cache corrupto | `npm cache verify` |
| Permisos `~/.npm-global` rotos | `ls -ld ~/.npm-global ~/.npm-global/lib` |
| Network/registry timeout | `npm ping` y `curl -I https://registry.npmjs.org/openclaw` |
| Node version incompatible con 2026.5.3 | `node --version` y comparar con `engines` en el manifest del paquete nuevo: `npm view openclaw@2026.5.3 engines` |
| Integrity hash mismatch | log de `npm install --verbose` mostrará `EINTEGRITY` |
| Peer dep nueva no satisfecha | `npm view openclaw@2026.5.3 peerDependencies` |

## 6. Output

Crear apéndice `## Upgrade attempt 2026-05-04 — FAILED` en el audit existente `umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md` con:

- Síntoma exacto del dashboard.
- Logs relevantes del gateway (snippet recortado).
- Causa raíz identificada (de las hipótesis del step 5).
- Estado actual del runtime (versión, salud, integridad de npm-global).
- **Recomendación de remediación**: una de:
  - (R1) Retry simple — fue glitch transitorio (network, npm registry).
  - (R2) Limpiar `npm cache` + retry desde dashboard.
  - (R3) Upgrade manual via CLI (`npm install -g openclaw@2026.5.3`) bypaseando el dashboard.
  - (R4) Hold en `2026.4.9` por bug del paquete nuevo o incompatibilidad de Node — escalar a upstream.
  - (R5) Otra (especificar).
- **NO ejecutes la remediación todavía** — solo recomendá. David decide.

Commit: `docs(O14.2): diagnose openclaw upgrade failure 2026-05-04 (global install verify)`

## 7. Cerrar esta task

- Si runtime sigue sano y solo hay diagnóstico → status: `done`.
- Si runtime está degradado → status: `blocked` y reportar URGENTE.

# Reglas

- **Cero acciones reversivas sin aprobación de David.** Diagnóstico, captura de logs, y `npm cache verify` (read-only) son seguros. Cualquier `npm install`, `--force`, `rm`, restart de service requiere OK explícito.
- Aplicar VPS Reality Check Rule: el repo no sabe nada del fallo, solo la VPS lo sabe.
- Si el step 1 muestra que el gateway NO está active, esa es la única acción crítica → reportar de inmediato y NO seguir con steps 2-6 hasta restablecer.

# Log

## [copilot-vps] 2026-05-04 ~19:50 -04 — Diagnóstico completado, runtime en SPLIT, recomendación R5

Apéndice publicado en `docs/audits/2026-05-04-openclaw-version-baseline.md` sección `## Upgrade attempt 2026-05-04 — FAILED (O14.2)`.

**Hallazgos clave:**

- **Install npm completó OK** (`exit 0` en `~/.npm/_logs/2026-05-04T23_19_39_043Z-debug-0.log`). Files en `~/.npm-global/lib/node_modules/openclaw/` son `2026.5.3-1` (mtime 19:19).
- **Runtime en SPLIT:** `openclaw --version` → `2026.5.3-1`, pero daemon `openclaw-gateway.service` (PID 1000650) sigue siendo el de `2026.4.9` corriendo desde 2026-04-24 — nunca reinició.
- **Causa raíz:** "global install verify" es step del orquestador `update.run` del gateway (no de npm). El RPC reporta `status=error` swallowed sin mensaje subyacente. Tres intentos visibles en journal (19:17:44, 19:19:16, 19:19:55) con duraciones consistentes con install + verify.
- **Hipótesis comunes descartadas:** disco (78G libre), npm cache (clean), permisos (OK), network (npm ping OK), node version (v24.14.0 vs `>=22.14.0` OK), peer deps (empty), integrity (sin EINTEGRITY), npm ls (clean).
- **Síntoma colateral del SPLIT visible en log:** RPCs `models.list` y `commands.list` desde la dashboard nueva pegan al daemon viejo y devuelven `INVALID_REQUEST` (`unexpected property 'view'`, `unknown method`).
- **Config sin drift:** md5 `~/.openclaw/openclaw.json` = `0df7a03297a67d88f5be8f404c262946` (mismo que baseline).

**Recomendación R5 (otra) — restart explícito del gateway:**

Plan propuesto (NO ejecutado):
1. Snapshot `~/.openclaw/openclaw.json.bak-pre-5.3-restart`.
2. `systemctl --user restart openclaw-gateway.service`.
3. Validar `openclaw status --all` → versión `5.3-1` + active.
4. Si gateway no levanta: `openclaw doctor --fix --non-interactive`.
5. Rollback de emergencia: `npm install -g openclaw@2026.4.9 && systemctl --user restart`.

**Status: `blocked`** — runtime degradado (SPLIT estado real), espera OK de David para ejecutar R5. Servicio NO está caído (active running), pero el mismatch CLI↔daemon es una degradación medible y los RPC errors observados confirman impacto funcional.

**Cero acciones reversivas ejecutadas.** Todos los comandos corridos fueron read-only (`ls`, `df`, `cat`, `grep`, `journalctl`, `npm view`, `npm ping`, `npm cache verify`, `ps`, `systemctl is-active`).

## [copilot-vps] 2026-05-04 ~20:02 -04 — Resuelto por task 005 (R5 ejecutado)

David aprobó R5. Ejecución en `.agents/tasks/2026-05-04-005-copilot-vps-openclaw-restart-r5-execute.md` (status: done). SPLIT resuelto: nuevo PID 1386078 corriendo `2026.5.3-1`. Apéndice de resolución en `docs/audits/2026-05-04-openclaw-version-baseline.md` sección `## Restart resolution 2026-05-04 — R5 EXECUTED`.

Status: `blocked` → `done`.
