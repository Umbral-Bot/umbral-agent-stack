# Editorial Wave 2 + LinkedIn HITL — Plan (2026-06-04)

- **Veredicto:** `EDITORIAL_WAVE2_PLAN_READY`
- **Owner lead:** Cursor · **Implementación:** Codex (Worker/n8n) + Lovable/Copilot según canal
- **Gate publicación:** doble checkbox Notion + frase David `ok, publica` ([live HITL](editorial-hitl-notion-live-2026-06-04.md))

## Decisiones cerradas

| Tema | Decisión v1 |
|------|-------------|
| Canal vs formato | Una DB `Publicaciones`; copies por propiedad (`Copy LinkedIn`, etc.) — **ya en Notion** |
| Source of truth editorial | Notion HITL + `notion/schemas/publicaciones.schema.yaml`; repo = specs, evals, runbooks |
| S6 canónico | `Sistema Editorial Rick` hub → DB Publicaciones (no Bandeja como storage primario) |
| Idempotencia | `content_hash` + `idempotency_key` tras gate 1; vacíos hasta aprobación |
| SQLite | Endurecer editorial pipeline SQLite en Worker (PR separado); no bloquea HITL Notion |
| Observabilidad | `trace_id`, `publish_error`, `error_kind` en Notion; ops_log para runtime |
| Source-use | Política atribución: `docs/ops/editorial-source-attribution-policy.md` |
| LinkedIn v1 | **Preview + payload manual/HITL**; API publish solo post-`autorizar_publicacion` + orden explícita |
| Ghost | Primer canal con automatización **después** de HITL estable en Notion |
| X | Manual/asistido v1 (copy en propiedad; sin autopost) |
| Visuales | Mermaid/screenshots primero; `visual_hitl_required` obliga revisión humana |
| Generación imagen | Vertex/Freepik API-first; no automatizar UIs terceros |

## Arquitectura Wave 2 (fases)

### Fase W2.1 — HITL estable (ahora)

- [x] DB Publicaciones + gates live ([verificación](editorial-hitl-notion-live-2026-06-04.md))
- [ ] David aprueba CAND-002 gate 1 en Notion (manual)
- [ ] Documentar en Rick skill `publication-gatekeeper`: leer checkboxes antes de cualquier publish task

### Fase W2.2 — Worker publish handlers (Codex PR)

| Task | Canal | Gate |
|------|-------|------|
| `editorial.prepare_linkedin_payload` | LinkedIn | Requiere `aprobado_contenido` + Notion read |
| `editorial.publish_*` | Todos | Requiere `autorizar_publicacion` + `ok, publica` en task input |

No implementar `publish_*` hasta W2.1 probado con CAND-002.

### Fase W2.3 — Ghost primer autopublish candidato

- Webhook o n8n → Worker → Ghost Admin API
- Misma doble gate Notion
- Blog = canonical URL en `publication_url`

### Fase W2.4 — LinkedIn token lifecycle

- Inventario token/expiry (Copilot Windows / Azure Key Vault si aplica)
- Runbook reauth antes de jun 2026 sponsorship cutoff
- Marketing API: solo capabilities documentadas en skill `linkedin-marketing-api-embudo`

### Fase W2.5 — Evals

- Extender `evals/editorial/` con casos gate violation (intent publish sin autorizar)
- Mission Control / eval #462: métrica % drafts con gates correctos

## Owners

| Entregable | Agente |
|------------|--------|
| HITL live + CAND review | David + Cursor |
| Worker editorial publish | Codex |
| Ghost integration | Codex o n8n (charter) |
| LinkedIn OAuth/token | Copilot Windows |
| n8n schedule curación | Codex (skill n8n-editorial-orchestrator) |
| No publicar sin gate | Rick (publication-gatekeeper skill) |

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Confundir checkbox con orden de publicación | Exigir `ok, publica` en task |
| Autopublicación accidental | No deploy `publish_*` en prod sin flag |
| Drift schema Notion vs YAML | Diff trimestral; Mejora Continua |
| LinkedIn ToS / automation | Preview humano v1; API solo post-review |

## Prompts de implementación (post-plan)

1. Codex: `editorial.notion_gate_guard` — valida gates antes de payload
2. Codex: Ghost publish handler (tras W2.1)
3. Copilot Windows: LinkedIn token audit

## Referencias

- `docs/specs/sistema-editorial-rick-v1.md`
- `docs/ops/cand-002-source-driven-flow.md`
- `docs/ops/core-first-next-prompts-2026-06-03.md` PROMPT 6
- `docs/ops/q2-core-first-unified-plan-2026-06-04.md`
