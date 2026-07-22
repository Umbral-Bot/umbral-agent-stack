# P1 Shortlist — snapshot live (2026-07-22)

> **Estado:** informativo — mirror docs/schema de un cambio ya ejecutado en
> Notion por David + Notion AI. Este documento NO crea, edita, ni consulta
> Notion (no se hizo ninguna llamada a la API de Notion en este PR; los
> IDs/URLs de abajo son los reportados por David). NO cablea runtime.

## Qué se ejecutó (P1, contrato §9 / roadmap §2)

David ejecutó P1 del [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md)
vía **Notion AI** (setup manual asistido — no el Worker; ver
[rick-editorial/ROLE.md](../../openclaw/workspace-agent-overrides/rick-editorial/ROLE.md):
"Notion AI may support manual setup of pages/DBs, but does not participate in
recurring editorial operations"):

1. Creó la BD **Alternativas / Shortlist** con los campos del
   [contrato §6](editorial-norte-hitl-contract-2026-07-22.md#6-recomendación-de-schema-híbrido-proposed---decide-david).
2. Añadió a **Publicaciones**: `origen_alternativa` (relation → Shortlist) y
   `listo_rrss` (checkbox — decisión D2, locked).

## IDs / URLs reportados

| Superficie | Valor |
|---|---|
| DB Alternativas / Shortlist — página | https://app.notion.com/p/978766172abe46c9989bdcc031ea65c3 |
| DB Alternativas / Shortlist — data source | `collection://5d9ca959-1783-4b99-af59-a0ca535fff08` |
| Parent (ambas DBs, decisión D1 — co-ubicadas) | **Sistema Editorial Rick** — https://app.notion.com/p/5894ba351e2749729077ca971fd9f52a |
| Publicaciones — data source | `collection://dc833f1f-07d9-49d0-82ec-fdfad1c808c4` |
| Publicaciones — campos nuevos | `origen_alternativa` (relation → Shortlist), `listo_rrss` (checkbox) |

## Discrepancia detectada (no resuelta aquí)

El parent live reportado es **"Sistema Editorial Rick"**. El
`recommended_parent` documentado en
[publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
dice **"Sistema Editorial Automatizado Umbral"**. No está confirmado si es la
misma página renombrada o dos páginas distintas — se deja como nota, sin
tocar `recommended_parent` sin que David lo confirme. Ver comentario inline
en el YAML.

## Repo espejado en este PR (docs/schema-only)

- **Nuevo:** [notion/schemas/alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml)
  — mirror de campos/opciones del contrato §6.
- **Editado (aditivo, sin tocar el resto):**
  [notion/schemas/publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
  — documenta `origen_alternativa` + `listo_rrss` (`version: 0.1.0 → 0.2.0`).
- **Env template (placeholders, sin valores reales/secretos):** `.env.example`
  y `openclaw/env.template` — añadida entrada comentada
  `NOTION_SHORTLIST_DS_ID` (naming: se usó el prefijo `NOTION_` existente en
  el repo — no `UMBRAL_*` — para seguir la convención real de
  `worker/config.py`; confirmar con Cursor/David si se prefiere otro nombre).
  Ningún ID real de este documento es secreto (son IDs de recurso Notion, no
  credenciales), pero el template mantiene el patrón `CHANGE_ME_*` del resto
  del archivo por consistencia.

## Qué NO se hizo en este PR

- Ninguna llamada a la API de Notion (ni lectura ni escritura).
- Ningún write de filas/contenido en Notion.
- Ningún cambio de schema live (el schema ya lo creó David + Notion AI; este
  PR sólo lo documenta en el repo).
- No se cableó el poller de promoción (P2.1) ni ningún otro paquete P2.
- No se tocó `docs/policies/05-change-management-and-automation-safety.md` en
  el monorepo `notion-governance` — ese clone local tiene cambios sin commitear
  de una rama no relacionada (`feat/notion-capitalizacion-v21-pilot`); anotar
  el boundary ahí queda como checklist para Cursor/David (ver PR body).

## Siguiente

- P1.4 (roadmap): este PR **es** P1.4.
- P2.1 (poller Aprobar→promueve): depende de este PR + de que el poller lea
  `alternativa_id` / escriba `promovido_a` + `origen_alternativa`.
- Confirmar con David: naming `NOTION_SHORTLIST_DS_ID` y la discrepancia de
  `recommended_parent`.

## Referencias

- [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §6, §9
- [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) P1, P1.4
- [alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml)
- [publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
