# CAND-004 Traceability Upgrade Run

> **Date**: 2026-05-05
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Worktree**: `/home/rick/umbral-agent-stack-editorial`
> **Operator**: Claude (Copilot CLI) — operador técnico VPS
> **Editorial generator**: rick-communication-director (OpenClaw, azure-openai-responses/gpt-5.4)
> **Mode**: append-only · sin publicar · sin gates · sin borrar la versión simple

## Problema

La sección `8. Trazabilidad` de CAND-004 (base `Publicaciones`, page `3575f443-fb5c-8199-8c2d-cf4a5b965529`) era **superficial**: 2 bloques top-level (un H2 + un toggle con 5 bullets de una línea cada uno: Fuentes/Evidencia/Inferencia/Hipótesis/No verificado). David no podía reconstruir, en una sola pantalla, qué entró, qué se transformó, quién decidió qué, ni qué riesgos quedaban abiertos.

## Resultado

```yaml
traceability_upgrade_done: true
notion_page_id: 3575f443-fb5c-8199-8c2d-cf4a5b965529
notion_url: https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c81998c2dcf4a5b965529
old_h2_id: 3575f443-fb5c-816b-93ff-e0ba9d8422f0       # renombrado a "resumen simple (reemplazada por versión completa abajo)"
old_toggle_id: 3575f443-fb5c-8161-8b57-de44ff7cd3db   # preservado intacto
new_h2_text: "8. Trazabilidad — versión completa"
new_top_level_blocks_appended: 11                       # 1 H2 + 1 callout resumen + 8 toggles (subsecs 2-9) + 1 callout cierre
old_section_preserved: true
old_section_renamed: true
gates_unchanged_cand004: true                           # aprobado_contenido=false, autorizar_publicacion=false, gate_invalidado=false
gates_unchanged_cand003: true
cand_002_untouched: true                                # cero llamadas API
cand_003_untouched: true                                # solo lectura de propiedades
wrong_subpage_untouched: true                           # sigue [SUPERSEDED], no archivada
publication_unchanged: true                             # canal_publicado vacío, published_at vacío
files_changed:
  - docs/ops/cand-004-traceability-contract.md
  - docs/ops/cand-004-traceability-upgrade-run.md
validation_pre_write: 0_errors_0_warnings               # spec contra contrato (mín fuentes/decisiones/riesgos/cadena/checklist)
validation_post_write: 28_pass_0_fail                   # acceso, gates, viejo+nuevo H2, toggles, tablas, CAND-003, subpage errónea
risks:
  - "El nuevo H2 quedó al FINAL de la página (después de la sección 11), no inmediatamente debajo del H2 viejo. Notion API no permite insertar bloques en posición arbitraria por append; la única opción no destructiva era append-to-page. La señal de continuidad la lleva el rótulo del H2 viejo: '...reemplazada por versión completa abajo'."
  - "Las 8 subsecciones plegadas en toggles esconden el detalle por defecto. Si David prefiere ver todo expandido, ajustar el flag 'open' en el builder."
  - "Contenido editorial generado por rick-communication-director sobre la trazabilidad real conocida (F01..F11). Si alguna fila es inexacta, requiere microedición antes de promover el formato."
next_step_for_david: "Abrir CAND-004 en Notion → bajar al final → leer '8. Trazabilidad — versión completa'. Verificar las 9 subsecciones. Si el formato sirve, autorizar (a) archivar el bloque viejo de trazabilidad y (b) replicar el formato a CAND-002/CAND-003."
no_ejecutado:
  - publicación
  - aprobación de contenido
  - marcar gates en ninguna página
  - tocar Copy LinkedIn / Copy X / Copy Blog / Copy Newsletter en CAND-002 ni CAND-003
  - borrar el toggle viejo de trazabilidad
  - archivar la subpágina errónea bajo CAND-003
  - cambios en SKILL.md / CALIBRATION.md / ROLE.md
  - cambios en openclaw.json o env
  - persistir tokens
  - merge a main
  - force push
```

## Estructura agregada

| # | Bloque | Tipo | Estado |
|---|--------|------|--------|
| 0 | `8. Trazabilidad — versión completa` | heading_2 | abierto |
| 1 | Resumen (alcance + estado de auditoría + qué reemplaza) | callout azul | abierto |
| 2 | `2. Fuentes usadas` | toggle + tabla 5 col × 11 filas | plegado |
| 3 | `3. Transformación editorial` | toggle + tabla 5 col × 8 filas | plegado |
| 4 | `4. Evidencia / Inferencia / Hipótesis` | toggle + 3 tablas (3+2+2 filas) | plegado |
| 5 | `5. Estrategia narrativa` | toggle (premisa + 4 ángulos descartados + 6 criterios + qué se priorizó) | plegado |
| 6 | `6. Decisiones tomadas` | toggle + tabla 5 col × 7 filas | plegado |
| 7 | `7. Riesgos y límites` | toggle + tabla 4 col × 5 filas | plegado |
| 8 | `8. Cadena de custodia` | toggle + tabla 5 col × 8 filas | plegado |
| 9 | `9. Checklist antes de replicar` | toggle + 8 ítems chequeables (todos `☐`) | plegado |
| 10 | Cierre — gates summary | callout gris | abierto |

## Manejo del bloque viejo (no destructivo)

- H2 viejo (`3575f443-fb5c-816b-93ff-e0ba9d8422f0`) renombrado a:
  > `8. Trazabilidad — resumen simple (reemplazada por versión completa abajo)`
- Toggle viejo (`3575f443-fb5c-8161-8b57-de44ff7cd3db`) **preservado**, **no archivado**, **no editado**.
- Decisión de no archivar: el task pide preservar hasta autorización humana explícita.

## Limitación Notion API conocida

El nuevo H2 quedó **al final de la página**, no inmediatamente después del viejo. La API `PATCH /blocks/{page}/children` agrega siempre al final del contenedor; no soporta `position` ni `after_id` arbitrario para inserciones intercaladas. Reordenar requeriría borrar y recrear bloques posteriores — operación destructiva que el task prohíbe.

Mitigación: el rótulo del H2 viejo dirige explícitamente al lector hacia abajo (`...reemplazada por versión completa abajo`).

## Validaciones aplicadas

### Pre-write (`validate.py` sobre `traceability_spec.yaml`)

- YAML parseable.
- `candidate_id == "CAND-004"`.
- `ready_to_replace_existing_traceability: true`, `ready_for_publication: false`.
- Mínimos: fuentes ≥ 6 (11), transformación ≥ 6 (8), decisiones ≥ 5 (7), riesgos ≥ 4 (5), cadena de custodia ≥ 6 (8), checklist ≥ 6 (8).
- Cada `tipo`/`severidad`/`riesgo_error`/`accion` dentro de los enums permitidos.
- Sin frases prohibidas (aprobado, autorizar, publicar ahora, token, secret, api_key, secreto) — con excepción de los flags `no_aprobado`, `no_publicado`.
- Sin URLs externas inventadas.

Resultado: **0 errores, 0 warnings**.

### Post-write (`post_validate.py` contra Notion)

- Página accesible.
- 3 gates de CAND-004 en `false`.
- Bloques cargados: 66 top-level (55 originales + 11 nuevos).
- H2 viejo presente y renombrado correctamente.
- Toggle viejo presente, no archivado.
- Nuevo H2 presente.
- ≥ 8 toggles después del nuevo H2 (encontrados 11).
- Las 8 subsecciones esperadas presentes por título (Fuentes, Transformación, Evidencia, Estrategia, Decisiones, Riesgos, Cadena, Checklist).
- Tablas presentes en Fuentes / Transformación / Decisiones / Riesgos / Cadena.
- CAND-003 sin cambios en sus 3 gates.
- Subpágina errónea sigue con prefijo `[SUPERSEDED]` y no archivada.

Resultado: **28 PASS / 0 FAIL**.

## Comandos ejecutados (resumen)

```
cd /home/rick/umbral-agent-stack-editorial
git status --short            # clean
git rev-parse HEAD            # 50563d1
git ls-remote origin rick/editorial-linkedin-writer-flow  # confirma push previo

# Phase 0 — dump current section 8
python3 /tmp/cand-004-trace/dump_section8.py > /tmp/cand-004-traceability-before.txt
  # → 2 top-level blocks (H2 + toggle de 5 bullets)

# Phase 1 — contract
write docs/ops/cand-004-traceability-contract.md  # 9 subsecciones, schema YAML

# Phase 2 — generate spec via OpenClaw (NO Copilot redaction)
write /tmp/cand-004-trace/prompt.txt
openclaw agent --agent rick-communication-director --message "$(cat /tmp/cand-004-trace/prompt.txt)" --json
  > /tmp/cand-004-trace/comdir-output.json     # ~66KB
extract result.payloads[0].text → /tmp/cand-004-trace/traceability_spec.yaml  # ~16KB

# Phase 3 — validate spec
python3 /tmp/cand-004-trace/validate.py
  → errors=0 warnings=0

# Phase 4 — materialize in Notion
set -a; source ~/.config/openclaw/env; set +a
python3 /tmp/cand-004-trace/write_notion.py
  → renamed old H2
  → appended 11 top-level blocks (1 chunk, ≤100 children)

# Phase 5 — post-validation
python3 /tmp/cand-004-trace/post_validate.py
  → 28 PASS / 0 FAIL

# Phase 6 — evidence + commit + push
write docs/ops/cand-004-traceability-upgrade-run.md
git add docs/ops/cand-004-traceability-contract.md docs/ops/cand-004-traceability-upgrade-run.md
git commit -m "docs(editorial): upgrade CAND-004 traceability prototype"
git push origin rick/editorial-linkedin-writer-flow
```

## Qué NO se hizo

- No se publicó nada.
- No se marcó ningún gate en CAND-002, CAND-003 ni CAND-004.
- No se modificó Copy LinkedIn / Copy X / Copy Blog / Copy Newsletter en ninguna página.
- No se borró el toggle viejo de trazabilidad.
- No se archivó la subpágina errónea bajo CAND-003.
- No se modificaron skills / runtime / openclaw.json / env.
- No se persistieron secretos.
- No se hizo merge a main.
- No se afirmó aprobación humana.
- No se promovió este formato a regla runtime para CAND-002/003.

## Recomendación para David

1. Abrir [CAND-004 en Notion](https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c81998c2dcf4a5b965529).
2. Bajar hasta el final de la página → ubicar `8. Trazabilidad — versión completa`.
3. Verificar las 9 subsecciones. ¿Te alcanza para auditar de dónde salió cada decisión sin abrir otros archivos?
4. Si el formato sirve:
   - autorizar archivar el toggle viejo (`3575f443-fb5c-8161-8b57-de44ff7cd3db`) y borrar el H2 viejo, o
   - autorizar reordenar la página (mover el nuevo H2 inmediatamente después del viejo).
5. Si el formato sirve y la trazabilidad se valida → autorizar replicación a CAND-002/CAND-003 según el contrato `docs/ops/cand-004-traceability-contract.md`.
6. Si fricciona → señalar qué subsección sobra, cuál falta o qué tabla simplificar.

## Temporales (a eliminar al cerrar fase)

- `/tmp/cand-004-trace/dump_section8.py`
- `/tmp/cand-004-trace/prompt.txt`
- `/tmp/cand-004-trace/comdir-output.json`
- `/tmp/cand-004-trace/comdir-stderr.txt`
- `/tmp/cand-004-trace/traceability_spec.yaml`
- `/tmp/cand-004-trace/validate.py`
- `/tmp/cand-004-trace/write_notion.py`
- `/tmp/cand-004-trace/post_validate.py`
- `/tmp/cand-004-trace/append-result.json`
- `/tmp/cand-004-trace/new-block-ids.json`
- `/tmp/cand-004-trace/post-validation.json`
- `/tmp/cand-004-trace/blocks-preview.json`
- `/tmp/cand-004-traceability-before.txt`
