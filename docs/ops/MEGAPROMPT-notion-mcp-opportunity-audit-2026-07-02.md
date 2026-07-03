MEGAPROMPT — Auditoría Notion MCP · umbral-agent-stack
Versión: NOTION-MCP-AUDIT-v1 · 2026-07-02
Modo: diagnóstico / read-only · NO implementación producción

================================================================================
ROL
================================================================================
Sos agente de investigación en umbral-agent-stack (Codex o Cursor en hilo nuevo).
Diagnosticás, auditás y proponés oportunidades de mejora ante el **Notion MCP oficial**
(OAuth HTTP, tools ricas, HTML via attachments). NO implementás cambios runtime ni writes
Notion en esta pasada.

================================================================================
CONTEXTO EXTERNO (leer primero)
================================================================================
Página demo Notion "What is MCP?":
https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0

Puntos clave a contrastar con nuestro stack:
- MCP = host/client/server; modelo propone → host ejecuta → resultado como texto
- Discovery via tools/list (descripciones = interfaz del modelo)
- Tools: notion-create-pages, notion-create-attachment, etc.
- Transport: stdio (local) vs Streamable HTTP (cloud) — Notion @ mcp.notion.com OAuth
- HTML/interactivos embebibles vía attachment tool (nuevo anuncio LinkedIn)

================================================================================
PREFLIGHT CLON
================================================================================
cd C:\GitHub\umbral-agent-stack-copilot
git remote get-url origin   # Umbral-Bot/umbral-agent-stack.git
git fetch origin main
git checkout main && git pull --ff-only origin main
git checkout -b codex/notion-mcp-opportunity-audit

Task: .agents/tasks/2026-07-02-005-notion-mcp-opportunity-audit.md

================================================================================
LECTURA INTERNA OBLIGATORIA (repo UAS)
================================================================================
1. .agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md
2. docs/adr/ADR-007-notion-como-hub-editorial.md
3. docs/editorial-pipeline/notion-schema.md + notion-helpers-policy.md
4. docs/plans/linkedin-publication-pipeline.md (§ audit MCP / REST runtime)
5. worker/ + dispatcher/ — grep NOTION, notion_client, poller
6. tests/test_mcp_server* (si existen wrappers MCP internos)
7. openclaw/workspace* — referencias notion en AGENTS/SKILL (expectativa vs realidad)

Cross-repo read-only (si accesible):
- C:\GitHub\notion-governance\docs\policies\02-permissions-by-surface.md
- C:\GitHub\notion-governance\registry\runtime-bridge-contract.yaml

================================================================================
FASE A — Inventario baseline (evidencia en repo)
================================================================================
Construir tabla:

| Superficie | Mecanismo hoy | Auth | Read/Write | Archivos clave |
|------------|---------------|------|------------|----------------|
| Worker Rick | REST API | NOTION_API_KEY | … | … |
| Notion Poller | … | … | … | … |
| Editorial pipeline | … | … | … | … |
| IDE agents (Cursor/Copilot) | Notion MCP OAuth | host MCP | … | mcp.json / settings |
| Rick VPS OpenClaw | ¿MCP? (audit 006) | … | … | … |
| n8n | node Notion | … | … | … |

Responder explícito: ¿dónde hay **duplicación** REST + MCP?

================================================================================
FASE B — Notion MCP actual (live si disponible)
================================================================================
Si tenés Notion MCP conectado en el host (Cursor/Copilot):
- tools/list → catalogar tools relevantes (create-pages, update, search, attachment, …)
- Anotar transport (HTTP vs stdio), OAuth scope, limitaciones observadas
- Probar SOLO read-only: notion-fetch / search en página demo o Control Room (sin writes)

Si MCP no conectado → documentar BLOCKED parcial y usar docs públicos Notion + página demo.

================================================================================
FASE C — Gap matrix (REST vs MCP)
================================================================================
Por flujo operativo (editorial, poller, granular pipeline, supervisor, dev governance):

| Flujo | REST hoy | MCP podría | Gap | Migrar? (sí/no/parcial) |
|-------|----------|------------|-----|-------------------------|

Incluir HTML/attachments: ¿impacto en Stage visual editorial, runbooks, páginas demo?

================================================================================
FASE D — Oportunidades (priorizadas)
================================================================================
Clasificar cada oportunidad:
- **Quick win** (≤1 día, bajo riesgo)
- **Strategic** (1–2 semanas, requiere ADR)
- **Defer** (no ahora)

Ejemplos a evaluar (no asumir válidos):
- Unificar dev agents en Notion MCP HTTP vs tokens sueltos
- Rick OpenClaw: registrar MCP Notion vs mantener REST Worker
- Editorial: rich HTML briefs en Notion via attachment tool
- Reducir scripts one-off REST donde MCP tools/list ya cubre
- Observabilidad: logging tool calls vs REST audit log

================================================================================
FASE E — Riesgos y gates
================================================================================
- NO-TOUCH surfaces (ADR-007, editorial gates aprobado_contenido / autorizar_publicacion)
- Rate limits Notion API vs MCP
- Seguridad OAuth por usuario vs integration token Rick
- Drift schema: MCP tool schemas vs worker/notion_client hardcoded
- Gobernanza notion-governance: qué writes requieren policy update

================================================================================
FASE F — Roadmap recomendado (O0–O3)
================================================================================
| Ola | Alcance | Gate David |
|-----|---------|------------|
| O0 | Esta auditoría + smoke read-only MCP | — |
| O1 | Dev workflow (Cursor/Copilot) — tool descriptions, HTML attachments en docs internos | G-NMCP-1 |
| O2 | Rick runtime eval (VPS) — MCP vs REST híbrido | G-NMCP-2 |
| O3 | Editorial producción — solo si O0–O2 OK | G-NMCP-3 |

NO proponer O2/O3 como hecho — solo recomendación.

================================================================================
PROHIBIDO
================================================================================
- Writes Notion producción (Publicaciones, Control Room, hubs editorial)
- Tocar VPS/OpenClaw gateway sin task separada
- Rotar tokens / commitear secretos
- Cambiar schema DB Notion
- Merge PR sin revisión

================================================================================
ENTREGABLES
================================================================================
1. docs/audits/notion-mcp-opportunity-audit-2026-07-02.md
   Secciones: Resumen ejecutivo · Baseline · MCP capabilities · Gap matrix ·
   Oportunidades (top 10) · Riesgos · Roadmap O0–O3 · Preguntas abiertas David
2. Actualizar Log task 2026-07-02-005 + .agents/board.md
3. PR opcional solo con doc audit (David decide merge)

================================================================================
FORMATO RESPUESTA A DAVID
================================================================================
NOTION_MCP_AUDIT_READY | oportunidades=N | quick_wins=N | riesgo_alto=N | recomendacion_ola=O?

5 bullets + link al doc audit.
