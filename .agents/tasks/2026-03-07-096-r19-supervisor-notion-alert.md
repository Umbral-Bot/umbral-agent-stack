# Task R19 — Verificar aviso Notion del supervisor (Codex u otro)

**Fecha:** 2026-03-07  
**Ronda:** 19  
**Agente:** Codex (o quien ejecute en VPS)  
**Branch:** `codex/096-supervisor-notion-alert` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

El supervisor ya llama a **POST /run** (corregido desde /task). Verificar en VPS que el aviso a Notion se publique al reiniciar Worker/Dispatcher y, si falla, documentar requisitos de env (NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID) en runbook.

---

## Contexto

- `scripts/vps/supervisor.sh`: tras reiniciar Worker o Dispatcher, hace POST a `${WORKER_URL}/run` con `task: notion.add_comment` y `input: { text: "..." }`.
- El Worker usa `NOTION_CONTROL_ROOM_PAGE_ID` por defecto si no se pasa `page_id` en el input.
- Si en VPS no están definidas NOTION_API_KEY y/o NOTION_CONTROL_ROOM_PAGE_ID en el env del Worker, el comentario fallará.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b codex/096-supervisor-notion-alert`.

2. **Verificación (en VPS o local con Worker + Notion configurados):**
   - Ejecutar `bash scripts/vps/supervisor.sh` cuando Worker esté arriba (no hace falta que esté caído).
   - Si no se reinició nada, no se envía alert. Para probar: temporalmente hacer que el script crea que hubo restart (o llamar a mano):  
     `curl -s -X POST "http://127.0.0.1:8088/run" -H "Authorization: Bearer $WORKER_TOKEN" -H "Content-Type: application/json" -d '{"task":"notion.add_comment","input":{"text":"Test supervisor alert"}}'`
   - Comprobar que en la página Control Room de Notion aparece el comentario (o que la respuesta del Worker es 200 y sin error).

3. **Documentación (si hace falta):**
   - En `docs/62-operational-runbook.md` (o en el script), añadir una línea indicando que para que el aviso Notion del supervisor funcione, el Worker debe tener en su entorno: `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID` (y opcionalmente `page_id` en el input si se usa otra página).

4. **PR:** Un único PR desde `codex/096-supervisor-notion-alert` a main. Título: "docs(R19-096): verificar/documentar aviso Notion del supervisor". Solo docs o comentarios; no cambiar lógica del supervisor salvo si hay bug claro.

---

## Criterios de éxito

- [ ] Verificado que POST /run con notion.add_comment funciona (en VPS o local).
- [ ] Runbook o script documentan env necesaria para el alert.
- [ ] PR abierto a main.

---

## Restricciones

- No cambiar la lógica de reinicio del supervisor. Solo verificación y documentación.
