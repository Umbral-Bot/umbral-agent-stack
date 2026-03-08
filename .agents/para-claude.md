# Mensaje para Claude Code

**Fecha:** 2026-03-07  
**De:** David / Cursor

---

## Tarea asignada: test VPS + fix (incorpora PR 108 de Rick)

Leí el **PR 108** que hizo Rick (rama `rick/vps`). Incorpora modelo Linear-first, identity/, .rick/, mejoras en `linear_create_issue.py`, runbook, scripts SSH VM. Necesito que:

1. **Testees en la VPS** que lo declarado en los docs existe y está configurado como se describe.
2. **En particular: n8n** — la documentación dice que n8n está instalado y configurado (Rick confirmó 2026-03-03). Verificá en vivo en la VPS:
   - Si n8n existe (`which n8n`, `~/.npm-global/bin/n8n`)
   - Si el servicio systemd user está activo (`systemctl --user status n8n`)
   - Si el puerto 5678 escucha
   - Si el PATH está en .bashrc según `scripts/vps/n8n-path-and-service.sh`
3. **Documentá los resultados** en `docs/audits/vps-test-results-YYYY-MM-DD.md` — scorecard OK/WARN/FAIL por cada check.
4. **Con esos resultados, solucioná todo lo que esté mal**: token mismatch (P0), n8n si no está bien configurado, sync de branches, etc.

### Instrucciones detalladas

Tarea completa: **`.agents/tasks/2026-03-07-100-claude-test-vps-and-fix.md`**

Incluye:
- Antecedentes del PR 108
- Checklist de comandos para test (infra, n8n, E2E, token)
- Referencias a docs (37-n8n-vps-automation, audit-results, runbook)
- Fase 3: acciones correctivas por prioridad (P0 token, P1 n8n, P2 sync, P3 VM)
- Criterios de aceptación

### Conexión VPS

- SSH: `rick@100.113.249.25` o `rick@srv1431451` (Tailscale)
