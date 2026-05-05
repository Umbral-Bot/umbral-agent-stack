# CAND-004 Notion Location Fix

> **Date**: 2026-05-05
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Worktree**: `/home/rick/umbral-agent-stack-editorial`
> **Operator**: Claude (Copilot CLI) — operador técnico VPS
> **Mode**: corrección de ubicación · sin publicar · sin gates · sin borrar

## Problema

CAND-004 fue creado por error como **subpágina de CAND-003** en lugar de como **item de la base `Publicaciones`**. El contenido (estructura navegable, 11 secciones, 130 bloques) era correcto, pero la ubicación no lo dejaba aparecer en la base donde David revisa los candidatos editoriales.

## Resultado

```yaml
location_fix_done: true
wrong_page_id: 3575f443-fb5c-8150-a6de-f89cb8a27f1d
correct_database_or_parent_id: e6817ec4-698a-4f0f-bbc8-fedcf4e52472  # base "Publicaciones"
new_cand_004_page_id: 3575f443-fb5c-8199-8c2d-cf4a5b965529
new_cand_004_url: https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c81998c2dcf4a5b965529
wrong_page_marked_as_superseded: true   # title prefix [SUPERSEDED] + callout rojo al pie con link al nuevo
wrong_page_archived: false              # no se archivó; queda pendiente decisión humana de David
cand_002_untouched: true                # cero llamadas API
cand_003_untouched: true                # solo lectura de propiedades; props sin cambio
gates_unchanged: true                   # aprobado_contenido=false, autorizar_publicacion=false, gate_invalidado=false
publication_unchanged: true             # no publicación; canal_publicado vacío; published_at vacío
repo_commit: pending                    # se completará al cerrar la fase
files_changed:
  - docs/ops/cand-004-notion-location-fix.md
validation:
  correct_parent: pass                  # parent.database_id == Publicaciones DB id
  content_present: pass                 # 55 top-level blocks replicados (130 nodos incluyendo nested)
  first_screen_structure: pass          # premise, mapa del discurso, alternativas para elegir, shortlist visibles
  alternatives_navigation: pass         # toggles V-P01 / V-P02 / V-P03 presentes
risks:
  - "Subpágina errónea no archivada — sigue accesible bajo CAND-003 con prefijo [SUPERSEDED] y callout al pie. Si David quiere archivarla, requiere autorización explícita."
  - "El nuevo item entra a la base con Estado=Borrador y aparece en la vista activa de Publicaciones; si esto rompe la vista de revisión humana, ajustar Estado o filtrar."
  - "Notion API no soporta insertar bloques en posición 0; el callout de superseded quedó al final de la subpágina, no al inicio. La señal de tope está dada por el prefijo [SUPERSEDED] en el título."
next_step_for_david: "Abrir el nuevo CAND-004 en la base Publicaciones (link arriba). Si la ubicación es correcta, decidir si archivar la subpágina errónea bajo CAND-003."
no_ejecutado:
  - publicación
  - aprobación de contenido
  - marcar gates
  - tocar Copy LinkedIn / Copy X / Copy Blog / Copy Newsletter de CAND-002 ni CAND-003
  - borrar bloques en la subpágina errónea
  - archivar la subpágina errónea
  - cambios en SKILL.md / CALIBRATION.md / ROLE.md
  - cambios en openclaw.json o env
  - persistir tokens
  - merge a main
  - fuerzas push
```

## Detección y target

- Target propuesto: `e6817ec4-698a-4f0f-bbc8-fedcf4e52472`.
- API confirma `object: database`, título `Publicaciones`.
- Propiedades clave detectadas: `Título` (title), `Estado` (status), `Canal` (select), `Tipo de contenido` (select), `Prioridad` (select), `aprobado_contenido` / `autorizar_publicacion` / `gate_invalidado` (checkbox), `Premisa` / `Ángulo editorial` / `Claim principal` (rich_text), `Creado por sistema` (checkbox).
- Búsqueda previa por título "CAND-004": 0 resultados → no había duplicado.

## Replicación de contenido

- Se leyó el árbol completo de bloques de la subpágina errónea (`3575f443-fb5c-8150-a6de-f89cb8a27f1d`): 55 top-level + nested (130 nodos totales).
- Se transformaron los bloques eliminando campos read-only (`id`, `created_time`, `created_by`, `last_edited_*`, `archived`, `parent`, `has_children`, `request_id`) y campos `null` que rechaza el endpoint de creación.
- `tables` se reconstruyeron con `table_width`, `has_column_header`, `has_row_header` y filas como children.
- Toggles, callouts, paragraphs y list items soportan `children` inline en la creación, así que se preservó la jerarquía completa en una sola pasada.
- Página creada con primer chunk de 80 bloques; el resto (≤80) se anexó por `PATCH /blocks/{id}/children`.

## Propiedades del nuevo item

| Campo | Valor |
|---|---|
| Título | `CAND-004 — Prototipo de navegación editorial para selección de alternativas` |
| Estado | `Borrador` |
| Canal | `linkedin` |
| Tipo de contenido | `linkedin_post` |
| Prioridad | `baja` |
| aprobado_contenido | `false` |
| autorizar_publicacion | `false` |
| gate_invalidado | `false` |
| Creado por sistema | `true` |
| Premisa | `PROTOTIPO de estructura navegable. No publicar.` |
| Ángulo editorial | `prototype_layout` |
| Copy LinkedIn / X / Blog / Newsletter | **vacío** (no se rellenaron como draft activo) |
| canal_publicado / published_at / published_url | **vacío** |

## Validaciones (12 / 12 PASS)

- `parent_is_database` — parent es la base `Publicaciones`.
- `title_correct` — título empieza con `CAND-004` y contiene `Prototipo`.
- `estado_borrador` — Estado=`Borrador`.
- `gates_unmarked` — los tres gates en `false`.
- `top_block_count_55` — los 55 bloques top-level se replicaron.
- `premise_top` — primeros 14 bloques mencionan "premisa" / "tesis".
- `discourse_top` — primeros 14 bloques mencionan "mapa del discurso" / "problema".
- `alternatives_top` — primeros 14 bloques referencian "Alternativas para elegir" / "Shortlist".
- `alternatives_in_toggles` — toggles `V-P01`, `V-P02`, `V-P03` presentes.
- `cand003_aprobado_false` / `cand003_autorizar_false` / `cand003_gate_false` — CAND-003 props sin cambio.

## Manejo de la subpágina errónea (no destructivo)

- Título cambiado a `[SUPERSEDED] CAND-004 — …` (señal visible en el árbol bajo CAND-003).
- Callout rojo agregado al final de la página con link al nuevo CAND-004 y texto:
  > ⚠️ Esta subpágina fue creada por error. La versión correcta de CAND-004 está en la base Publicaciones: `<link>`. No usar esta página para revisión.
- **No se archivó.** El task pide preservar hasta verificar y autorización humana explícita.
- Limitación Notion API: no se puede insertar bloque en posición 0. El callout quedó al pie. La señal de tope la lleva el prefijo `[SUPERSEDED]` del título.

## Comandos ejecutados (resumen)

```
cd /home/rick/umbral-agent-stack-editorial
git status --short          # clean
git fetch origin main rick/editorial-linkedin-writer-flow
GET /databases/e6817ec4...  -> object=database, title=Publicaciones
GET /blocks/3575f443.../children (recursive, 4 niveles)
POST /pages (parent=database_id, props seguras, children=primeros 80 bloques)
  -> page_id 3575f443-fb5c-8199-8c2d-cf4a5b965529
PATCH /blocks/.../children (no fue necesario, 55 ≤ 80)
GET /pages/<new>            -> validación post-write
GET /pages/<CAND-003>       -> verificación props intactas
PATCH /pages/<wrong>        -> título prefix [SUPERSEDED]
PATCH /blocks/<wrong>/children -> callout rojo con link al nuevo
```

## Qué NO se hizo

- No se publicó nada.
- No se marcó ningún gate.
- No se modificó Copy LinkedIn / Copy X / Copy Blog / Copy Newsletter en CAND-002 ni CAND-003.
- No se borraron bloques.
- No se archivó la subpágina errónea.
- No se modificaron skills / runtime / openclaw.json / env.
- No se persistieron secretos.
- No se hizo merge a main.
- No se afirmó aprobación humana.

## Recomendación para David

1. Abrir el nuevo CAND-004 en la base Publicaciones: <https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c81998c2dcf4a5b965529>.
2. Verificar que aparece en la vista de la base como item.
3. Si la ubicación y la estructura son correctas → autorizar archivar la subpágina errónea bajo CAND-003 (`3575f443-fb5c-8150-a6de-f89cb8a27f1d`).
4. Si el formato de la nueva página sigue válido → autorizar replicación a CAND-002/003 según contrato `docs/ops/cand-004-notion-layout-contract.md`.
