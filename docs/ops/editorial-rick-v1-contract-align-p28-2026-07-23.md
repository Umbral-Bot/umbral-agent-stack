# P2.8 — Rick-editorial V1 contract alignment (2026-07-23)

> **Estado:** docs/prompt alineados. **No activa nada** — `rick-editorial` sigue
> `design-only / not active` (activación real requiere GO explícito de David,
> sin cambios aquí a `openclaw.json`/`config/teams.yaml`). Ningún gate se
> abre, ningún publish, ninguna escritura en Notion, ninguna simulación de
> Rick creando filas reales. Cablea el paquete P2.8 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3.

## Qué es

Antes de este paquete, `rick-editorial`'s `ROLE.md` y su payload template
sólo conocían el flujo **V2** (candidato final estilo Publicaciones —
`copy_linkedin`, `copy_blog`, etc.). No mencionaban en absoluto los tres
campos obligatorios que el contrato (§3) exige para toda **Alternativa V1**
(`arco_narrativo`, `estructura_discurso`, `fuente_pieza_url`) — a pesar de que
el propio contrato, la política de atribución y el schema Shortlist ya
nombraban a `rick-qa` como el enforcer de esas reglas. `rick-qa`'s `ROLE.md`,
por su parte, sólo tenía QA de voz/benchmark para copy final (V2) — cero
checklist estructural para una Alternativa V1.

**Nota de auditoría:** `SKILL.md` de `editorial-source-curation`,
`shortlist-format.md`, `docs/67-editorial-source-curation.md` §5.1 y
`docs/68-editorial-phase-1-manual.md` §6.1 **ya estaban alineados** al
contrato (verificado antes de tocar nada) — sólo `rick-editorial/ROLE.md`, el
payload template, y `rick-qa/ROLE.md` tenían la brecha.

## Qué cambia

1. **`openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`**:
   - Nueva sección `## Output contract — V1 Alternativa (Shortlist)` con el
     yaml exacto de `notion/schemas/alternativas-shortlist.schema.yaml`,
     marcando los tres campos **OBLIGATORIO**.
   - Nueva `## Acceptance criteria for a V1 alternativa` (checklist
     separado del de V2).
   - `Mission`/`Scope`/`Source discipline`/`Handoff triggers` actualizados
     para nombrar explícitamente la etapa V1 y la regla de fuente-pieza-
     concreta (contrato §3, política de atribución #7).
   - La sección V2 existente (`Output contract — candidate payload`, ahora
     `V2 candidate payload`) queda intacta, sólo re-etiquetada para
     distinguirla de la nueva V1.

2. **`docs/ops/rick-editorial-candidate-payload-template.md`**: mismo
   tratamiento — nueva plantilla + checklist V1, plantilla V2 existente
   re-etiquetada, y una nueva sección **"Negative-examples-log hook"**
   documentando cómo (opcionalmente) consultar
   `scripts/editorial/sync_negative_examples.py --check-topic-key` (P2.5,
   ya implementado, sin llamada a Notion) antes de cerrar un veredicto —
   explícitamente **no** cableado a disparar solo dentro de una pasada de
   QA en vivo de Rick (eso requeriría tocar runtime real de OpenClaw, fuera
   de alcance, GO aparte).

3. **`openclaw/workspace-agent-overrides/rick-qa/ROLE.md`**: nueva sección
   `## Editorial V1 alternativa structural QA (Shortlist, pre-HITL-1)` con:
   - Rechazo duro (`blocked_missing_field`) si falta `arco_narrativo` y/o
     `estructura_discurso` y/o `fuente_pieza_url`.
   - Rechazo duro (`blocked_source_not_concrete`) si `fuente_pieza_url` es
     una home/feed en vez de la pieza concreta.
   - Chequeos no-bloqueantes (arco genérico/templado, `resultado_revision`
     no tocado por `rick-editorial`).
   - El mismo hook de consulta de negativos, documentado igual que en el
     payload template.
   - Tabla de veredictos `structural: pass | blocked_missing_field |
     blocked_source_not_concrete`, separada de los veredictos de voz (V2)
     ya existentes.
   - `Scope` actualizado para nombrar la responsabilidad V1 explícitamente.

## Qué NO hace (por diseño)

- No activa `rick-editorial` ni `rick-qa` — el banner "design-only / not
  active" y las "Activation conditions" de `rick-editorial/ROLE.md` quedan
  sin tocar.
- No crea ni modifica ningún schema Notion — los tres campos ya viven en
  `notion/schemas/alternativas-shortlist.schema.yaml` desde P1.
- No escribe en Notion, no crea filas, no simula a Rick generando una
  Alternativa real.
- No abre gates (`aprobado_contenido`/`autorizar_publicacion`) ni toca el
  gate `telegram_confirmed` (P2.6) ni `listo_rrss` (P2.7).
- No cablea el consumo de negativos como llamada automática dentro del
  runtime vivo de Rick — queda documentado como paso manual/Cursor-
  orquestado, con el hook ya funcional desde P2.5.
- No añade un validador Python nuevo — no existía ninguno previo para estos
  tres campos (confirmado, greenfield) y esta tarea es alineación de
  prompt/docs, no de código; por eso no se agregan tests nuevos (mission:
  "tests si hay validadores en repo").

## Tests

Ninguno nuevo — no hay validador de código para `arco_narrativo` /
`estructura_discurso` / `fuente_pieza_url` en el repo (confirmado antes de
editar), y esta tarea es puramente docs/prompt. Se corrió la suite existente
que referencia `rick-qa`/`rick-editorial` como identificadores de sesión
(`tests/test_openclaw_runtime_snapshot.py`,
`tests/test_sync_openclaw_workspace_governance.py`,
`tests/test_pit_tournament_run.py`) y la suite de P2.5
(`tests/test_sync_negative_examples.py`, cuyo hook de consulta se
documenta aquí) para confirmar que ningún archivo tocado las afecta — las
55 pasan sin cambios.

## Referencias

- Contrato §3 (Alternativa V1), §4 (HITL-1): [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md)
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.8, MP-2.8
- Matriz de brecha: [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md) fila A
- ROLE `rick-editorial`: `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- ROLE `rick-qa`: `openclaw/workspace-agent-overrides/rick-qa/ROLE.md`
- Payload template: `docs/ops/rick-editorial-candidate-payload-template.md`
- Schema Shortlist (ya vivo): `notion/schemas/alternativas-shortlist.schema.yaml`
- Política de atribución: `docs/ops/editorial-source-attribution-policy.md`
- SKILL curation (ya alineada): `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`
- Store de negativos (P2.5): [editorial-negative-loop-p25-2026-07-23.md](editorial-negative-loop-p25-2026-07-23.md)
