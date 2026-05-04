---
id: 2026-05-04-005
title: Execute R5 - restart openclaw gateway to resolve SPLIT (CLI 5.3-1 / daemon 4.9)
assigned_to: copilot-vps
created_by: copilot-chat
created_at: 2026-05-04
status: open
priority: high
related_plan: notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md (O14.2, O14.3)
related_audit: umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md
related_tasks:
  - 2026-05-04-002 (O14.0 baseline, done)
  - 2026-05-04-004 (diagnóstico, blocked → será marcada done por esta task)
approved_by: David (2026-05-04, vía Copilot Chat)
---

# Contexto

Task 004 diagnosticó SPLIT post-upgrade: CLI ya es `2026.5.3-1` pero daemon (PID 1000650) sigue corriendo `2026.4.9` desde 2026-04-24. Recomendación R5 propuesta y **aprobada por David**: restart explícito del gateway service.

Plan original en el apéndice del audit. Esta task es la **ejecución autorizada**.

# Plan de ejecución (sigue al pie de la letra)

## Step 1: Snapshot defensivo del config

```bash
ssh rick@<vps> "cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-5.3-restart && md5sum ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-5.3-restart"
```

Esperado: dos md5 idénticos = `0df7a03297a67d88f5be8f404c262946`. Si difieren, ABORTAR.

## Step 2: Capturar estado pre-restart

```bash
ssh rick@<vps> "openclaw --version; ps -o pid,etime,cmd -p 1000650; systemctl --user status openclaw-gateway.service --no-pager | head -10"
```

Confirmar que sigue siendo el SPLIT documentado en task 004.

## Step 3: Restart del servicio

```bash
ssh rick@<vps> "systemctl --user restart openclaw-gateway.service"
sleep 3
```

## Step 4: Verificar nuevo PID + versión efectiva

```bash
ssh rick@<vps> "systemctl --user status openclaw-gateway.service --no-pager | head -15"
ssh rick@<vps> "openclaw status --all 2>&1 | head -40"
ssh rick@<vps> "openclaw models status 2>&1 | head -30"
```

**Criterios de éxito:**
- Servicio `active (running)` con PID **distinto** de 1000650.
- `openclaw status --all` reporta versión `2026.5.3-1` en daemon.
- Modelos visibles, default Azure gpt-5.4 sigue presente.
- Sin `INVALID_REQUEST` en `models.list` ni `commands.list`.

## Step 5: Verificar logs limpios post-restart

```bash
ssh rick@<vps> "sudo journalctl --user-unit openclaw-gateway.service --since '2 minutes ago' --no-pager | tail -50"
```

Buscar: arranque limpio, sin tracebacks, sin warnings de breaking change inesperados.

## Step 6: Smoke test funcional

```bash
ssh rick@<vps> "bash ~/umbral-agent-stack/scripts/vps/verify-openclaw.sh 2>&1 | tail -30"
```

Pasa = GO. Falla = ir a Step 7.

## Step 7 (solo si Step 4-6 fallan): Doctor

```bash
ssh rick@<vps> "openclaw doctor --fix --non-interactive 2>&1 | tail -40"
```

Y repetir Step 4. Si sigue fallando → Step 8.

## Step 8 (rollback de emergencia, solo si Step 7 falla):

```bash
ssh rick@<vps> "npm install -g openclaw@2026.4.9 && systemctl --user restart openclaw-gateway.service"
sleep 3
ssh rick@<vps> "openclaw --version && openclaw status --all | head -20"
```

Reportar URGENTE a David antes de cerrar la task.

# Output

Apéndice nuevo en `docs/audits/2026-05-04-openclaw-version-baseline.md` sección `## Restart resolution 2026-05-04 — R5 EXECUTED` con:

- Resultado de cada step (1-6, y 7-8 si aplicó).
- PID nuevo del daemon.
- Versión final efectiva (CLI + daemon).
- Veredicto final: **GO** (SPLIT resuelto, runtime sano en 5.3-1) o **ROLLBACK EXECUTED** (volvió a 4.9, escalar a upstream).

Commit: `docs(O14.2/3): execute R5 restart, resolve SPLIT post-upgrade`

# Cierre

- Esta task → `done` con commit hash.
- Task 004 → actualizar status de `blocked` a `done` (referencia esta task como resolución).
- Si rollback: status `done` igual (la acción se ejecutó), pero veredicto ROLLBACK + escalación.

# Reglas

- David aprobó R5. NO necesitás re-confirmar Steps 1-6.
- Step 7 (doctor) ejecutalo solo si fallan Steps 4-6, sin re-confirmar.
- Step 8 (rollback) ejecutalo solo si Step 7 falla, sin re-confirmar — es el path de seguridad pre-aprobado.
- Cualquier comportamiento NO previsto en este plan (config drift, errores raros, requiere acción fuera del plan) → DETENER y reportar antes de actuar.
