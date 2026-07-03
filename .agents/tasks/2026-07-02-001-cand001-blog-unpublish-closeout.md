---
id: "2026-07-02-001"
title: "CAND-001 blog-only closeout + editorial unpublish (Codex PR #494)"
status: done
assigned_to: cursor
created_by: cursor
priority: high
sprint: editorial-cand001
created_at: "2026-07-02"
updated_at: "2026-07-02"
---

## Objetivo

Cerrar el ejemplo editorial CAND-001 (blog Azure), confirmar uso del endpoint unpublish de Codex para eliminar fixture smoke, y dejar bitácora al día para el siguiente frente (CAND-004+).

## Contexto

- CAND-001: pieza opinión, blog manual sin `autorizar_publicacion`.
- Fixture smoke `criterios-de-aceptacion-antes-de-automatizar-bim` debía salir del CDN.
- Codex implementó unpublish en PR #494; Cursor verificó prod + Notion + merge.

## Criterios de aceptación

- [x] Endpoint unpublish en `main` (PR #494 merged)
- [x] Fixture smoke eliminado del índice y SWA 404
- [x] CAND-001 blog live en SWA + blob
- [x] Gates Notion intactos (`aprobado_contenido` / `autorizar_publicacion` false)
- [x] Doc closeout `docs/ops/cand-001-closeout-2026-07-02.md`
- [x] Board actualizado
- [ ] Hero Alt 1 republicado (defer — mismatch documentado)

## Log

### [codex] 2026-07-01 / 2026-07-02
- Implementó `POST /api/unpublish-editorial-post`, Worker task, tests, smoke script.
- Deploy `func-umbral-editorial-prod`; smoke unpublish fixture `criterios-de-aceptacion-antes-de-automatizar-bim`.
- Evidencia: `C:\coord-ag-evidence\cand-001-unpublish-fixture\`
- PR #494: commits `761f6ec` + `1237e55` (YAML Perplexity + handoff).

### [cursor] 2026-07-02
- Merge PR #494 → `main` @ `1660538` (admin; CI billing lock).
- Verificación browser: SWA CAND-001 200; fixture 404; `/noticias` solo 1 post.
- Notion (sesión David): gates false; `Selección imagen` Alt 1; hero live = Alt 2 (`7d3b9a`) — documentado.
- Bitácora: `docs/ops/cand-001-closeout-2026-07-02.md`, handoff unpublish actualizado, board § Editorial CAND-001.

## Referencias

- Closeout: `docs/ops/cand-001-closeout-2026-07-02.md`
- Handoff copy: `docs/ops/cand-001-completion-handoff-2026-06-07.md`
- Siguiente frente: `docs/ops/cand-full-pipeline-next-2026-06-07.md`
- Unpublish handoff: `docs/ops/MEGAPROMPT-codex-editorial-unpublish-deploy.md`
