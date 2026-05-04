---
id: 2026-05-04-003
title: OpenClaw upgrade verify post-dashboard (O14.2 + O14.3)
assigned_to: copilot-vps
created_by: copilot-chat
created_at: 2026-05-04
status: open
priority: medium
related_plan: notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md (O14.2, O14.3)
related_audit: umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md (commit 5d94e77)
related_task: 2026-05-04-002 (O14.0 baseline, done)
---

# Contexto

David ejecutó el upgrade de OpenClaw vía botón **"Update now"** del dashboard del gateway (mismo flujo que siempre usa). Pre-upgrade:

- Versión instalada: `2026.4.9`
- Versión target: `2026.5.3` (banner del dashboard)
- Audit baseline: 0 breaking changes que afecten Umbral.
- Default model pre-upgrade: Azure gpt-5.4.

# Objetivo

Cerrar **O14.2 (ejecución upgrade)** y **O14.3 (verificación post)** del plan Q2-2026 con evidencia real desde la VPS.

# Tareas

1. **Confirmar versión nueva instalada en runtime real:**
   ```bash
   ssh rick@<vps> "openclaw --version && npm ls -g --depth=0 | grep openclaw"
   ```

2. **Estado del gateway tras el upgrade:**
   ```bash
   ssh rick@<vps> "systemctl --user status openclaw-gateway.service --no-pager | head -30"
   ssh rick@<vps> "sudo journalctl --user-unit openclaw-gateway.service --since '30 minutes ago' | tail -80"
   ```
   - Verificar que el unit está `active (running)`.
   - Verificar que no hay errores de arranque ni warnings de breaking change inesperados.

3. **Health checks funcionales:**
   ```bash
   ssh rick@<vps> "openclaw status --all && openclaw models status"
   ssh rick@<vps> "bash ~/umbral-agent-stack/scripts/vps/verify-openclaw.sh"
   ```
   - Confirmar default model sigue siendo Azure gpt-5.4 (o documentar cambio si lo hubo).
   - Confirmar nodos visibles igual que pre-upgrade.

4. **Smoke test mínimo del worker contra OpenClaw** (si aplica al setup actual): un request real al gateway y confirmar respuesta no degradada.

5. **Output:** apéndice al audit existente `umbral-agent-stack/docs/audits/2026-05-04-openclaw-version-baseline.md` con sección `## Post-upgrade 2026-05-04` que contenga:
   - Versión confirmada post-upgrade.
   - Tiempo de restart del gateway.
   - Diff de comportamiento observado vs pre-upgrade (modelos, nodos, defaults).
   - Cualquier warning o nota de release que ahora aplica.
   - Veredicto: **GO** (todo OK) o **ROLLBACK NEEDED** (con razón).

# Criterio de done

- Apéndice committed a `main` de `umbral-agent-stack` con mensaje `docs(O14.2/3): post-upgrade openclaw 2026.5.3 verify`.
- Esta tarea cerrada con `status: done` y commit hash en el footer.
- Si rollback necesario: status `blocked` y reportar a David antes de cualquier acción reversiva.

# No hacer

- No tocar configuración del gateway más allá del upgrade ya ejecutado.
- No cambiar default model salvo que el upgrade lo haya roto.
- No declarar GO sin journalctl + status reales.
