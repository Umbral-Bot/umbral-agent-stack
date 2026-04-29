# Runbook — Codegen Fase 1 Smoke Test

> Validar que `code-architect` produce un plan ejecutable y lo postea en Notion para HITL gate 1, end-to-end, en menos de 10 minutos.

**Estado del rollout:** Fase 1 (solo architect activo). Sin generación de código todavía.

## Pre-requisitos

- [ ] PR de scaffold mergeado a `main` de `umbral-agent-stack`:
  - `docs/architecture/06-codegen-team-design.md`
  - `docs/roadmap/codegen-rollout-phases.md`
  - `openclaw/workspace-templates/skills/code-{architect,implementer,reviewer,debugger,scribe}/SKILL.md`
  - `config/teams.yaml` con equipo `build` agregado
  - Este runbook
- [ ] Worker Linux desplegado en VPS (port 8089) con env:
  - `WORKER_TOKEN` distinto al de la VM Windows
  - `WORKER_TASKS_ENABLED=code.architect,github.preflight,notion.add_comment`
  - `OPENCLAW_BUILD_TEAM_PHASE=1`
- [ ] Handler `code.architect` registrado en `worker/tasks/__init__.py` (TODO Fase 1)
- [ ] Página Notion "Build Team — Control Room" creada con `NOTION_BUILD_TEAM_PAGE_ID` exportado en VPS
- [ ] Branch protection en `umbral-bot-2` y `umbral-agent-stack`: agentes no pueden push a `main` con su PAT

## Smoke test paso a paso

### 1. Health check

```bash
# En la VPS
curl -s http://localhost:8089/health | jq
# Esperado: {"ok": true, "tasks_loaded": [..., "code.architect", ...]}
```

### 2. Trigger directo (sin Rick)

```bash
curl -s -X POST http://localhost:8089/run \
  -H "Authorization: Bearer $WORKER_TOKEN_CODEGEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code.architect",
    "input": {
      "intent": "Agregar endpoint GET /health/detailed al worker que devuelva versión, uptime y task handlers cargados",
      "target_repo": "umbral-agent-stack",
      "target_branch_base": "main",
      "constraints": ["no romper /health existente", "responder JSON"],
      "notion_thread_id": "'"$NOTION_BUILD_TEAM_PAGE_ID"'"
    }
  }' | jq
```

**Esperado en respuesta JSON:**
- `ok: true`
- `output.plan_md` con secciones: Objetivo, Archivos a tocar, Cambios por archivo, Tests, Riesgos, Criterios de aceptación, Estimación
- `output.notion_comment_url` apuntando a un comentario nuevo en Notion
- `output.status: "awaiting-human-approval"`
- Duración total < 90 segundos

### 3. Verificar Notion

Abrir la página "Build Team — Control Room" en Notion. Debe haber un comentario nuevo con:
- Título de la intent
- Plan resumido (no más de 50 líneas)
- Link al markdown completo (gist o adjunto)
- Instrucciones "✅ aprobar / ❌ rechazar / 💬 ajustar"

### 4. Trigger vía Rick (Notion bus)

En la página Control Room principal de Rick, comentar:

```
Rick, equipo build: diseñá un endpoint GET /health/detailed para el worker
que devuelva versión, uptime y handlers cargados. Sin romper /health.
```

**Esperado:**
- A las XX:10 (próximo poll), Rick detecta intent `build`
- Selecciona supervisor `build`
- Encola `code.architect` con el intent
- En < 5 minutos aparece comentario del architect en página Build Team
- Rick deja un comentario en página principal: "Plan listo, ver Build Team"

### 5. Validar HITL gate

En el comentario del architect, responder ✅. Esperar próximo poll.

**Esperado en Fase 1:**
- Rick acepta la aprobación
- Rick contesta: "Plan aprobado. Implementer no disponible en Fase 1. Plan archivado para implementación manual o Fase 2."
- Status de tarea en Redis: `approved-but-implementation-deferred`

(En Fase 2, esto encolaría `code.implement` automáticamente.)

## Criterios de éxito Fase 1

- [ ] 3 smoke tests consecutivos exitosos en distintas intents
- [ ] Plan generado < 90 s en cada caso
- [ ] HITL gate 1 funcional en ambos paths (directo + vía Rick)
- [ ] Cero leaks de secrets en logs (verificar con `grep -i "ghp_\|github_pat_\|sk-" logs/`)
- [ ] Costo Azure/Copilot acumulado en smoke tests < $1
- [ ] Latencia poll Notion → trigger task < 90 s

## Rollback

Si Fase 1 falla en producción:

```bash
# Desactivar equipo build sin tocar resto
ssh vps
export OPENCLAW_BUILD_TEAM_ENABLED=false
systemctl --user restart openclaw

# O bajar el Worker codegen
systemctl --user stop umbral-worker-codegen

# Verificar
openclaw status --all
```

Rick rechazará tareas `build` con mensaje: "Equipo build temporalmente desactivado. Diseño de software queda en pausa."

## Troubleshooting común

| Síntoma | Causa probable | Fix |
|---------|----------------|-----|
| `/health` 404 en :8089 | Worker codegen no levantó | `journalctl --user -u umbral-worker-codegen -n 50` |
| `code.architect` no registrado | Handler no importado en `worker/tasks/__init__.py` | Agregar import + restart |
| Plan vacío o trivial | LLM mal configurado o budget bajo | Verificar `dispatcher/model_router.py` route para architect |
| Notion no recibe comentario | `NOTION_API_KEY` o `NOTION_BUILD_TEAM_PAGE_ID` mal | Validar con `notion.add_comment` aislado |
| Rick no detecta intent build | `intent_classifier.py` no entrenado para "diseñá / planificá / build" | Agregar keywords + restart dispatcher |

## Próxima fase

Una vez Fase 1 estable (≥ 1 semana sin regresión):
1. Construir imagen `umbral/codegen-sandbox:0.1`
2. Implementar handler `code.implement`
3. Configurar branch protection en repos target
4. Generar PAT scope script
5. Ver `docs/roadmap/codegen-rollout-phases.md` Fase 2
