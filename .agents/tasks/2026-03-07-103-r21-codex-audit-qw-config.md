# Task R21 — Quick Wins Auditoría: Config (Codex)

**Fecha:** 2026-03-07  
**Ronda:** 21  
**Agente:** Codex (GPT-5.4)  
**Rama:** `codex/audit-qw-config` — trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar código:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/audit-qw-config`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/audit-qw-config`, abrir PR a main. No mergear el PR tú mismo salvo que se te indique.

---

## Objetivo

Implementar el quick win QW-4 de la auditoría 2026-03: limpiar `.env.example` y scripts de Bitácora (SEC-2, SEC-3, SEC-5). Plan: [docs/plan-implementacion-auditoria-2026-03.md](../../docs/plan-implementacion-auditoria-2026-03.md).

---

## Tareas

### QW-4: Limpiar .env.example y scripts Bitácora

1. **En `.env.example`:**
   - Reemplazar cualquier IP real de Tailscale por placeholders: `<VPS_TAILSCALE_IP>` y `<VM_TAILSCALE_IP>` (o equivalentes en comentarios).
   - Añadir `LINEAR_WEBHOOK_SECRET=` con comentario p. ej. `# required for webhook HMAC validation`.
   - Añadir `NOTION_BITACORA_DB_ID=` con comentario p. ej. `# required for bitacora scripts (add_resumen_amigable, enrich_bitacora_pages)`.

2. **En `scripts/add_resumen_amigable.py`:**
   - Eliminar el valor por defecto hardcodeado del DB ID de Notion (p. ej. el default en `os.getenv("NOTION_BITACORA_DB_ID", "...")`). Leer solo de env; si no está definido, fallar con un mensaje claro (sys.exit o raise con texto que indique definir `NOTION_BITACORA_DB_ID`).

3. **En `scripts/enrich_bitacora_pages.py`:**
   - Igual: eliminar default hardcodeado del DB ID; exigir variable de entorno y fallar con mensaje claro si no está definida.

4. Verificar que ningún test dependa del DB ID hardcodeado en esos scripts (si hay tests que los invocan, ajustar para usar env o mock).

---

## Criterios de éxito

- [ ] `.env.example` sin IPs reales; incluye `LINEAR_WEBHOOK_SECRET` y `NOTION_BITACORA_DB_ID` documentados.
- [ ] Los dos scripts de Bitácora exigen `NOTION_BITACORA_DB_ID` y fallan con mensaje claro si falta.
- [ ] Tests pasan. PR abierto a main con título `fix(R21-103): audit quick wins — config (.env.example, bitacora scripts)`.

---

## Restricciones

- No modificar `worker/`, ni `dispatcher/`, ni lógica de ops_log (eso va en ramas worker y dispatcher). Solo `.env.example` y los dos scripts indicados.
- No mergear a main. Solo push de tu rama y abrir PR.
