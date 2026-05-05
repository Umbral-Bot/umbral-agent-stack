# CAND-004 Notion Layout Prototype Run

> **Date**: 2026-05-05
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Worktree**: `/home/rick/umbral-agent-stack-editorial`
> **Commit base**: `0acaae7`
> **Operator**: Claude (Copilot CLI) — orquestador técnico
> **Generador editorial**: rick-communication-director (OpenClaw, azure-openai-responses/gpt-5.4)
> **Mode**: prototype only · append-only · no gates · no publication

## Objetivo

Crear un prototipo CAND-004 en Notion con estructura **navegable** que reorganice las categorías heredadas de CAND-003 en un layout escaneable en menos de 2 minutos:

1. Premisa
2. Estructura del discurso (problema → arg → contra → contra-contra → solución)
3. Alternativas resumidas con característica distintiva
4. Detalle de alternativas y evaluación plegado en toggles

OpenClaw (rick-communication-director) genera la estructura/contenido editorial. Copilot/Claude prepara prompt, ejecuta, valida y materializa en Notion sin emitir copy propio.

## Resultado

```yaml
cand_004_created: true
notion_url: https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c8150a6def89cb8a27f1d
notion_page_id: 3575f443-fb5c-8150-a6de-f89cb8a27f1d
notion_parent: subpágina de CAND-003 (page_id 34b5f443-fb5c-8167-b184-e3c6cf1f6c3f)
repo_branch: rick/editorial-linkedin-writer-flow
commit_base: 0acaae7
openclaw_agents_used:
  - rick-communication-director
page_structure:
  first_screen:
    - callout estado (Prototipo · No aprobado · No publicar)
    - callout seguridad (CAND-002/003 intactos · subpágina experimental)
    - "1. Resumen Ejecutivo" + anchor links
    - "2. Premisa De La Idea" (tesis + tensión + qué no dice)
    - "3. Mapa Del Discurso" (7 piezas)
    - "4. Alternativas Para Elegir" (tabla resumen)
    - "5. Shortlist"
  alternatives_navigation: "6. Alternativas Completas — toggles V-P01, V-P02, V-P03"
  detail_sections:
    - "7. Evaluación Comparativa (toggle)"
    - "8. Trazabilidad (toggle)"
    - "9. Gates Y Seguridad (abierto, recordatorio)"
    - "10. Historial De Generación (toggle)"
    - "11. Archivo / Detalle Largo (toggle vacío)"
validation:
  yaml_parse: pass
  page_spec_schema: pass (0 errors, 0 warnings)
  page_read_back: pass
  premise_visible_top: pass
  discourse_map_visible_top: pass
  alternatives_summary_visible_top: pass
  full_alternatives_collapsed_or_separated: pass (toggles V-P01/02/03)
  gates_unchanged: pass (CAND-003: aprobado_contenido=false, autorizar_publicacion=false, gate_invalidado=false)
  no_publication: pass
  cand_002_untouched: pass (no API call)
  cand_003_untouched: pass (solo lectura de propiedades; subpage añadida sin tocar bloques top-level)
  subpage_parent_is_cand003: pass
files_changed:
  - docs/ops/cand-004-notion-layout-contract.md
  - docs/ops/cand-004-notion-layout-prototype-run.md
risks:
  - "El prototipo usa contenido editorial inventado por rick-communication-director sobre el marco temático de CAND-003; no es copy listo para publicar."
  - "El layout es experimental: si David valida el formato, requiere revisión humana antes de promoverlo a regla del template editorial."
  - "El uso de toggles esconde detalle por defecto; si David prefiere ver todo expandido, se puede ajustar con un solo flag."
recommendation:
  replicate_to_cand_002_003_now: false
  next_human_step: "David revisa CAND-004 en Notion (link arriba) y decide si este formato sirve antes de tocar CAND-002/003"
no_ejecutado:
  - merge
  - push a main
  - cambios en CAND-002 ni CAND-003 (propiedades, gates, draft activo, bloques)
  - publicación
  - aprobación de contenido
  - cambios en SKILL.md / CALIBRATION.md / ROLE.md persistentes
  - cambios en openclaw.json o env
  - persistencia de tokens
```

## Estructura final creada (55 bloques top-level)

| # | Sección | Bloques | Estado |
|---|---------|---------|--------|
| Top callouts | Estado + recordatorio de seguridad | 2 | abiertos |
| 1 | Resumen Ejecutivo | H2 + 4 bullets + 6 anchor bullets | abierto |
| 2 | Premisa De La Idea | H2 + 3 bullets | abierto |
| 3 | Mapa Del Discurso | H2 + 7 bullets (problema → cierre) | abierto |
| 4 | Alternativas Para Elegir | H2 + tabla 6 columnas × 3 filas | abierto |
| 5 | Shortlist | H2 + 5 bullets | abierto |
| 6 | Alternativas Completas | H2 + 3 toggles (V-P01, V-P02, V-P03) | plegado |
| 7 | Evaluación Comparativa | H2 + 1 toggle (dimensiones + tabla ranking) | plegado |
| 8 | Trazabilidad | H2 + 1 toggle (5 bullets) | plegado |
| 9 | Gates Y Seguridad | H2 + 7 bullets explícitos | abierto |
| 10 | Historial De Generación | H2 + 1 toggle | plegado |
| 11 | Archivo / Detalle Largo | H2 + 1 toggle (vacío) | plegado |
| Cierre | Divider + callout final de seguridad | 2 | abierto |

Las 3 alternativas son ángulos distintos sobre el marco temático de CAND-003 (no copia):

- **V-P01 — Operativa directa** (top 1)
- **V-P02 — Pregunta central** (top 2)
- **V-P03 — Aterrizaje BIM** (reserva)

Cada toggle de alternativa contiene: LinkedIn (code block), X (code block), diferencia clave, pros, riesgos, microedits, source_trace, qa_status.

## Comandos ejecutados (resumen)

```
# Phase 0
cd /home/rick/umbral-agent-stack-editorial
git status --short
git branch --show-current        # rick/editorial-linkedin-writer-flow
git rev-parse HEAD               # 0acaae7929e2412102981eb45069c8b9455a5359
git fetch origin main rick/editorial-linkedin-writer-flow  # in sync
openclaw agent --agent rick-linkedin-writer --message "Responde solo: OK" --json
  # → "OK" via azure-openai-responses/gpt-5.4

# Phase 1 — read evidence
docs/ops/cand-003-ve-architect-review-packet.md (referencia)
docs/ops/cand-003-ve-publication-options-run.md
docs/ops/cand-003-ve-notion-sync-result.md  # parent page_id de CAND-003
docs/ops/cand-003-vd3-final-microedit-run.md
openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md (parcial)

# Phase 2 — contract
write docs/ops/cand-004-notion-layout-contract.md

# Phase 3 — generate page_spec via OpenClaw (no Copilot redaction)
write /tmp/cand-004/prompt.txt
openclaw agent --agent rick-communication-director --message "$(cat /tmp/cand-004/prompt.txt)" --json
  > /tmp/cand-004/comdir-output.json (≈48KB)
extract finalAssistantVisibleText → /tmp/cand-004/page_spec.yaml (≈10KB)

# Phase 4 — validate page_spec
python3 /tmp/cand-004/validate.py
  → errors=0 warnings=0

# Phase 5 — materialize in Notion (subpage of CAND-003)
set -a; source ~/.config/openclaw/env; set +a
python3 /tmp/cand-004/write_notion.py
  → page_id 3575f443-fb5c-8150-a6de-f89cb8a27f1d
  → 55 top-level blocks built; created in 1 chunk (≤80 children)

# Phase 6 — post-write validation
python3 /tmp/cand-004/post_validate.py
  → ALL PASS (11 checks)
```

## Prompt operativo (resumen)

Prompt enviado a `rick-communication-director` (`/tmp/cand-004/prompt.txt`) pidió YAML estructurado con 7 secciones obligatorias (executive_summary, premise, discourse_map, alternatives_summary, shortlist, alternatives_full, comparative_evaluation, traceability, gates_and_safety, generation_history).

Restricciones duras incluidas en el prompt: no publicar, no marcar gates, no afirmar aprobación humana, `ready_for_publication: false`, no copiar literal CAND-003, no inventar fuentes nuevas, no incluir tokens.

Reglas de redacción incluidas: voz David sobria, AEC/BIM concreto, LinkedIn 140–180 palabras, X ≤270 chars, ángulos distintos por alternativa, "modelo BIM" no "modelo" suelto.

## Validaciones aplicadas (page_spec)

Script `/tmp/cand-004/validate.py`:

- YAML parseable
- `candidate_id == "CAND-004"`
- `ready_for_publication: false`
- `ready_for_human_review: false`
- `premise.{tesis,tension,no_dice}` presentes
- `discourse_map` con 7 claves
- `alternatives_summary` ≥3, todos los campos
- `alternatives_full` IDs alineados con summary
- `gates_and_safety.{6 flags}` todos `true`
- Frases prohibidas no presentes (aprobación, autorización, tokens)
- Mención de CAND-002/003 sólo como "intacto"

Resultado: 0 errores, 0 warnings.

## Validaciones post-write (Notion)

Script `/tmp/cand-004/post_validate.py`:

- Página existe, título contiene "CAND-004" + "Prototipo"
- Estado visible en top (callouts iniciales)
- "Premisa", "Mapa del discurso", "Alternativas para elegir", "Shortlist" presentes en los primeros 14 bloques
- Toggles `V-P*` presentes para alternativas completas
- Padre = page_id de CAND-003
- CAND-003 propiedades intactas: `aprobado_contenido=false`, `autorizar_publicacion=false`, `gate_invalidado=false`

Resultado: 11/11 checks PASS.

## ¿Replicar en CAND-002/CAND-003 ahora?

**No.** Este es un prototipo. La replicación requiere:

1. David revisa CAND-004 en Notion y valida el formato.
2. Si lo aprueba: promover este contrato (`docs/ops/cand-004-notion-layout-contract.md`) a regla del template editorial mediante un cambio explícito.
3. Recién entonces, generar layouts equivalentes para CAND-002 y CAND-003 (probablemente como subpáginas paralelas para no destruir su contenido actual).

## Qué NO se hizo

- No se modificó Notion para CAND-002 ni CAND-003.
- No se cambiaron gates en ninguna página.
- No se publicó nada.
- No se marcó aprobación.
- No se reemplazó draft activo de CAND-002/003.
- No se borraron bloques de Notion.
- No se modificaron SKILL.md / CALIBRATION.md / ROLE.md.
- No se modificaron `openclaw.json` ni el env.
- No se persistió `NOTION_API_KEY` en repo ni se imprimió.
- No se hizo merge ni force-push.
- No se afirmó aprobación humana.
- No se convirtió este prototipo en regla runtime global.

## Riesgos y consideraciones

- **Contenido editorial inventado**: las alternativas V-P01/02/03 son generadas por rick-communication-director sobre el marco temático de CAND-003 sin pasar por rick-linkedin-writer ni rick-qa. Sirven para validar el contenedor visual, no para publicar.
- **Toggles ocultan por defecto**: si David prefiere ver todo expandido, ajustar el builder Notion (un solo flag).
- **Tabla de Notion**: 6 columnas; en mobile se vuelve estrecha. Si fricciona, evaluar dividir en 2 tablas o usar `column_list`.
- **Subpágina vs página independiente**: se eligió subpágina de CAND-003 para no inyectar entradas no-publicables en `📁 Publicaciones`. Si David prefiere página independiente, reubicar.

## Recomendación para David

Abrir [CAND-004 en Notion](https://www.notion.so/CAND-004-Prototipo-de-navegaci-n-editorial-para-selecci-n-de-alternativas-3575f443fb5c8150a6def89cb8a27f1d) y verificar:

1. ¿Entendiste la premisa, el mapa del discurso y las alternativas en menos de 2 minutos sin tener que abrir toggles?
2. ¿La tabla de "Alternativas para elegir" te alcanza para decidir cuál revisar primero?
3. ¿El plegado por toggle de las alternativas completas mejora respecto a CAND-003 actual?
4. ¿El bloque "Gates y seguridad" comunica bien que esto NO es publicación?
5. Si todo bien → autorizar replicación a CAND-002/003 con esta misma estructura.
6. Si fricciona → señalar qué bloque mover, qué plegar, qué expandir, qué simplificar.

## Temporales (a eliminar en Phase 8)

- `/tmp/cand-004/prompt.txt`
- `/tmp/cand-004/comdir-output.json`
- `/tmp/cand-004/comdir-stderr.txt`
- `/tmp/cand-004/page_spec.yaml`
- `/tmp/cand-004/validate.py`
- `/tmp/cand-004/write_notion.py`
- `/tmp/cand-004/post_validate.py`
- `/tmp/cand-004/notion-page.json`
- `/tmp/cand-004/post-validation.json`
