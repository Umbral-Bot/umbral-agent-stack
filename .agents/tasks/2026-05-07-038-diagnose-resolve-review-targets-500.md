---
id: 2026-05-07-038
title: Diagnose 500 errors in `_resolve_review_targets` (rama `session_capitalizable`)
status: open
priority: P1
assigned_to: copilot-vps
created_at: 2026-05-07
created_by: claude (post-037 deploy, side-finding capitalizado en cierre O15.1b)
parent: 2026-05-07-037
relates_to: 2026-05-07-035
blocks: nothing (NON-blocker, candidata Ola 2)
---

# 038 — Diagnose 500 errors en `_resolve_review_targets` (`session_capitalizable`)

## Contexto

Detectado durante el deploy post-037 (cierre O15.1b al 100%, 2026-05-07T22:42Z). En logs del poller daemon (pid 120685) post-deploy aparecen 500 errors recurrentes en la rama `session_capitalizable` de `_resolve_review_targets`.

**NO es regresión de task 037** — bug pre-existente latente, ortogonal al fix de `page_id` Control Room. La cadena Control Room → handler funciona end-to-end (verificado visualmente con bot Rick replicando `/health` JSON real en el thread del comment de David). Esta rama de targets es independiente.

**Por qué no bloquea**: el `except Exception` en `dispatcher/notion_poller.py:208` (`logger.warning("Failed to resolve session_capitalizable review targets", exc_info=True)`) captura el 500 silenciosamente y sigue iterando con los demás targets (`deliverable`, `project`, `control_room`). El path Control Room (que es el que alimenta a Rick mention router) NO depende de este target.

**Por qué importa igual**:
1. **Logs ruidosos** — cada ciclo `*/5` del poller emite warning + stacktrace, contamina `journalctl` y `tail /tmp/notion_poller.log`.
2. **Capability degradada** — la idea original de `session_capitalizable` era exponer páginas en estado capitalizable de la DB Sesiones (transcripciones Granola review path). Si esa rama está muerta, el poller no detecta menciones `@Rick` en esas páginas.
3. **Capitalización de governance V2** — atado a O8 (Granola loop) + flujo `notion-session-capitalization` skill. Si la rama vuela, hay que decidir: arreglar, deprecar, o reemplazar por path V2 directo desde `Transcripciones Granola`.

## Root cause sospechado (NO confirmado, parte del scope de este task)

Cadena `dispatcher/notion_poller.py` líneas 196-209:

```python
session_capitalizable_db_id = _session_capitalizable_db_id()
if session_capitalizable_db_id:
    try:
        session_resp = wc.run(
            "notion.read_database",
            {
                "database_id_or_url": session_capitalizable_db_id,
                "max_items": min(20, max_items),
            },
        )
        for page_id in _unique_page_ids(_extract_read_database_items(session_resp)):
            targets.append({"page_id": page_id, "page_kind": "session_capitalizable"})
    except Exception:
        logger.warning("Failed to resolve session_capitalizable review targets", exc_info=True)
```

Hipótesis a evaluar (en este orden):

- **H1** — `NOTION_SESSION_CAPITALIZABLE_DB_ID` (o el env var que `_session_capitalizable_db_id()` lea) apunta a un database id que no existe / fue archivado / movido. Notion API responde 404, capturado por worker y re-raised como 500.
- **H2** — La integration `Rick` (token `NOTION_API_KEY` en `~/.config/openclaw/env`) no tiene Connection a esa DB. Notion API responde 403, mismo path.
- **H3** — El database existe y está conectado, pero tiene una propiedad con tipo no soportado por `_extract_read_database_items` o por el filter del worker `notion.read_database` → 500 en parsing local.
- **H4** — Bug en el worker handler `notion.read_database` (no en el dispatcher) que devuelve 500 envelope-level para inputs específicos.

## Scope de este task

**READ-ONLY diagnosis**, NO fix inline. Misma forma que task 031 sobre el 400 `rick.orchestrator.triage`.

Entregables esperados en el handoff:

1. **Captura empírica del error real** desde VPS:
   ```bash
   ssh vps-umbral "tail -200 /tmp/notion_poller.log | grep -A 20 'Failed to resolve session_capitalizable'"
   ssh vps-umbral "sudo journalctl --user -u openclaw-dispatcher --since '24 hours ago' | grep -A 20 'session_capitalizable'"
   ```
   Reportar exactamente: traceback, status code Notion (si lo loggea el worker), database id afectado (prefix-only 8 chars per `secret-output-guard` #8).

2. **Verificar el database id resuelto** — `_session_capitalizable_db_id()`:
   ```bash
   ssh vps-umbral "cd ~/umbral-agent-stack && source .venv/bin/activate && python -c 'from dispatcher.notion_poller import _session_capitalizable_db_id; print(repr(_session_capitalizable_db_id()))'"
   ```

3. **Reproducir el call directo** contra Notion API con el token real (no leakear, fingerprint-only):
   ```bash
   ssh vps-umbral "source ~/.config/openclaw/env && curl -fsS -H \"Authorization: Bearer \$NOTION_API_KEY\" -H 'Notion-Version: 2022-06-28' https://api.notion.com/v1/databases/<db_id>" 2>&1 | head -50
   ```
   Reportar status code real (404 vs 403 vs 200 con shape inesperado).

4. **Verdict por hipótesis** — para H1/H2/H3/H4, marcar PASS / FAIL / no-aplica con evidencia. Si es H1/H2: proponer fix de gobernanza (arreglar env var o agregar Connection). Si es H3/H4: proponer fix de código en task 038-fix.

5. **Recomendación**: ¿arreglar (asignar task 038-fix), deprecar (eliminar el bloque + env var), o reemplazar (migrar a path V2 directo `Transcripciones Granola` per skill `notion-session-capitalization`)?

## Salvavidas

- **NO restart** ningún servicio. Diagnosis read-only.
- **NO touch** `openclaw.json`, `model.primary`, gateway pid `75421` (Vertex Fase 1 hasta 2026-05-14).
- **NO leakear** `NOTION_API_KEY`. Fingerprint-only en logs (per `secret-output-guard` #8).
- **No imprimir database ids completos** — prefix-only 8 chars en el handoff.
- **F-INC-002** estricto antes de cualquier push.

## Acceptance

- Handoff con evidencia empírica (logs reales, no fabricados — SOUL Regla 22).
- Verdict por hipótesis (H1-H4) con PASS/FAIL.
- Recomendación clara: fix / deprecate / migrate.
- 0 cambios en código de producción en este task (solo diagnosis).
- Si recomienda fix → spec de task 038-fix abierta como handoff secundario.
- Si recomienda deprecate → list de archivos a tocar + env var a remover.
- Si recomienda migrate → referencia a skill `notion-session-capitalization` + path V2 directo.

## Capitalización

Una vez resuelto, actualizar plan Q2 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`) en O15.2 (Ola 2) o en O8 (Granola loop) según corresponda al verdict, y board entry `2026-05-07-038`.
