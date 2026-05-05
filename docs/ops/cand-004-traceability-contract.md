# CAND-004 Traceability Contract (experimental prototype)

> **Date**: 2026-05-05
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Status**: experimental — prototype only, NOT a runtime rule
> **Scope**: define la estructura de auditoría editorial ("Trazabilidad") que reemplaza la versión simple de 5 bullets en la subpágina sección `8. Trazabilidad` de CAND-004 en la base `Publicaciones`. Aplicado primero a CAND-004 como prototipo. Replicación a CAND-002 / CAND-003 requiere autorización humana explícita.

## Problema observado

La sección `8. Trazabilidad` actual de CAND-004 contiene **2 bloques top-level** (un H2 + un toggle con 5 bullets de una línea cada uno: Fuentes / Evidencia / Inferencia / Hipótesis / No verificado). Es declarativa, no auditable: David no puede reconstruir, ante una sola pantalla, **de dónde salió cada decisión**, **qué se transformó**, **qué se inventó**, **quién tocó qué**.

Para que la trazabilidad sirva como auditoría editorial debe permitir, sin abrir otros archivos, responder a:

1. ¿Qué entró como insumo?
2. ¿Qué se transformó y por qué?
3. ¿Qué es evidencia dura vs inferencia vs hipótesis?
4. ¿Qué decisiones se tomaron y quién las tomó?
5. ¿Qué riesgos quedaron abiertos?
6. ¿Quién tocó qué archivo / endpoint / artefacto?
7. ¿Qué falta cumplir antes de replicar este formato a CAND-002/003?

## Categorías obligatorias (9 subsecciones)

Orden y contenido mínimo. Todas las subsecciones bajo el H2 `8. Trazabilidad — versión completa`. Subsecciones largas van plegadas en toggles; la subsección 1 (Resumen) abierta.

| # | Subsección | Plegado | Contenido mínimo |
|---|------------|---------|------------------|
| 1 | Resumen de la trazabilidad | abierto | Una frase de qué se está trazando + alcance + estado de auditoría (`prototipo / no replicado / no aprobado`) |
| 2 | Fuentes usadas | toggle | Tabla: id, tipo (`doc_repo` / `notion_page` / `agent_output` / `runtime_state`), ubicación (path o page_id), cómo se usó (1 frase), limitación |
| 3 | Transformación editorial | toggle | Cadena ordenada: insumo → operación → operador (agente / humano / herramienta) → output. Bullets o tabla. Cubre desde V-D3 base hasta selección final de alternativas en CAND-004 |
| 4 | Evidencia / Inferencia / Hipótesis | toggle | 3 tablas separadas (o 1 tabla con columna `tipo`): qué afirmación, qué la respalda, riesgo de error |
| 5 | Estrategia narrativa | toggle | Premisa elegida, ángulos descartados y por qué, criterios de selección (voz David, AEC/BIM, claim discipline), qué se priorizó |
| 6 | Decisiones tomadas | toggle | Tabla: decisión, quién (agente / humano / contrato), cuándo, alternativa rechazada, motivo |
| 7 | Riesgos y límites | toggle | Tabla: riesgo, severidad (`alto` / `medio` / `bajo`), mitigación aplicada, qué queda abierto |
| 8 | Cadena de custodia | toggle | Tabla: actor, archivo / endpoint, acción (`read` / `write` / `patch` / `comment`), timestamp aproximado, evidencia repo (path al run-doc) |
| 9 | Checklist antes de replicar | toggle | Lista chequeable (`[ ]`) de condiciones a cumplir antes de aplicar este formato a CAND-002/003 |

## Reglas de UX

1. **Resumen abierto, detalle plegado**. Subsección 1 abierta, subsecciones 2–9 en toggles.
2. **Tablas sobre paredes de texto**. Fuentes, decisiones, riesgos, cadena de custodia y evidencia/inferencia/hipótesis van en `table` Notion.
3. **Cita interna, no de internet**. Cada fuente debe poder ubicarse en el repo o en una página Notion conocida; no inventar URLs externas.
4. **Atribución por agente, no por modelo**. Citar `rick-communication-director` / `rick-linkedin-writer` / `rick-qa` / `Copilot CLI` / `David`, no el nombre del modelo subyacente.
5. **No publicar nada en la trazabilidad**. La sección no contiene copy publicable.
6. **No marcar gates**. La sección no toca propiedades de la página padre.

## Schema `traceability_spec` (YAML)

```yaml
candidate_id: CAND-004
ready_to_replace_existing_traceability: true
ready_for_publication: false
ready_for_human_review: false

resumen:
  alcance: <1–2 frases>
  estado_auditoria: prototipo
  reemplaza_a: "8. Trazabilidad (versión simple, 5 bullets)"

fuentes:                       # mínimo 6 entradas
  - id: F01
    tipo: doc_repo|notion_page|agent_output|runtime_state
    ubicacion: <path o page_id>
    como_se_uso: <1 frase>
    limitacion: <1 frase>
  # ...

transformacion_editorial:      # mínimo 6 pasos en orden cronológico
  - paso: 1
    insumo: <ref a F0x o estado previo>
    operacion: <verbo concreto>
    operador: rick-communication-director|rick-linkedin-writer|rick-qa|Copilot|David|contrato
    output: <ref a artefacto>
  # ...

evidencia_inferencia_hipotesis:
  evidencia:                   # afirmaciones con respaldo verificable en repo / Notion
    - afirmacion: <texto>
      respaldo: <ref a F0x>
      riesgo_error: bajo|medio|alto
  inferencia:                  # afirmaciones derivadas, no citadas literalmente
    - afirmacion: <texto>
      base: <ref a F0x>
      riesgo_error: bajo|medio|alto
  hipotesis:                   # afirmaciones no respaldadas, marcadas como tales
    - afirmacion: <texto>
      por_que_se_mantiene: <1 frase>
      riesgo_error: bajo|medio|alto

estrategia_narrativa:
  premisa_elegida: <1–2 frases>
  angulos_descartados:
    - angulo: <texto>
      motivo_descarte: <1 frase>
  criterios_seleccion:
    - <criterio>
  que_se_priorizo: <1–2 frases>

decisiones:                    # mínimo 5
  - decision: <texto>
    quien: rick-communication-director|rick-linkedin-writer|rick-qa|Copilot|David|contrato
    cuando: <fecha o fase>
    alternativa_rechazada: <texto o "ninguna">
    motivo: <1 frase>

riesgos:                       # mínimo 4
  - riesgo: <texto>
    severidad: alto|medio|bajo
    mitigacion: <1 frase>
    queda_abierto: <texto o "no">

cadena_de_custodia:            # mínimo 6 entradas
  - actor: <agente / humano / herramienta>
    archivo_o_endpoint: <path / endpoint Notion / agente>
    accion: read|write|patch|comment|create
    cuando: <fecha aprox>
    evidencia_repo: <path a run-doc o "n/a">

checklist_antes_de_replicar:   # mínimo 6 ítems
  - item: <texto chequeable>
    cumplido: false

gates_y_seguridad:
  no_publicado: true
  no_aprobado: true
  no_gates_marcados: true
  cand_002_intacto: true
  cand_003_intacto: true
```

## Validaciones requeridas (pre-write sobre `traceability_spec`)

- YAML parseable.
- `candidate_id == "CAND-004"`.
- `ready_to_replace_existing_traceability: true`.
- `ready_for_publication: false`.
- `ready_for_human_review` ausente o `false`.
- `resumen.{alcance, estado_auditoria, reemplaza_a}` presentes.
- `fuentes` ≥ 6, cada una con `{id, tipo, ubicacion, como_se_uso, limitacion}` no vacíos.
- `transformacion_editorial` ≥ 6 pasos en orden, todos con `{insumo, operacion, operador, output}`.
- `evidencia_inferencia_hipotesis` con las 3 sub-claves (cualquiera puede ser ≥1).
- `estrategia_narrativa.{premisa_elegida, criterios_seleccion, que_se_priorizo}` presentes; `angulos_descartados` ≥ 1.
- `decisiones` ≥ 5; cada una con `{decision, quien, cuando, alternativa_rechazada, motivo}`.
- `riesgos` ≥ 4; cada uno con `{riesgo, severidad, mitigacion, queda_abierto}`.
- `cadena_de_custodia` ≥ 6; cada una con `{actor, archivo_o_endpoint, accion, cuando, evidencia_repo}`.
- `checklist_antes_de_replicar` ≥ 6.
- `gates_y_seguridad` con los 5 flags en `true`.
- Frases prohibidas ausentes: `aprobado`, `autorizar`, `publicar ahora`, `token`, `secret`, `api_key`.
- Sin URLs externas inventadas (sólo repo paths o `notion://` / `https://www.notion.so/...` ya conocidas).

## Validaciones requeridas (post-write en Notion)

- Página CAND-004 (`3575f443-fb5c-8199-8c2d-cf4a5b965529`) accesible.
- Nuevo H2 `8. Trazabilidad — versión completa` presente, ubicado **inmediatamente después** del toggle de la versión simple antigua.
- ≥ 8 toggles directos (subsecciones 2–9) bajo el nuevo H2; subsección 1 (Resumen) puede ser callout o paragraph abierto.
- Tablas presentes en al menos: Fuentes, Decisiones, Riesgos, Cadena de custodia.
- H2 antiguo renombrado a `8. Trazabilidad — resumen simple (reemplazada por versión completa abajo)`.
- Toggle antiguo (`3575f443-fb5c-8161-8b57-de44ff7cd3db`) **no eliminado**, **no archivado**.
- CAND-002 y CAND-003 sin cambios en propiedades ni en bloques.
- Subpágina errónea (`3575f443-fb5c-8150-a6de-f89cb8a27f1d`) sin cambios desde el location-fix.
- Gates en CAND-004 sin marcar (`aprobado_contenido=false`, `autorizar_publicacion=false`, `gate_invalidado=false`).

## Restricciones de seguridad obligatorias

- No publicar.
- No marcar gates en ninguna página.
- No tocar Copy LinkedIn / Copy X / Copy Blog / Copy Newsletter de CAND-002/003.
- No borrar bloques en CAND-004 (la versión simple queda preservada y rotulada).
- No archivar la subpágina errónea de CAND-003.
- No persistir secretos.
- No emitir copy publicable en la trazabilidad.
- No inventar fuentes externas.
- No afirmar aprobación humana.

## Operador editorial

`rick-communication-director` (OpenClaw, `azure-openai-responses/gpt-5.4`) genera el `traceability_spec` YAML. Copilot CLI **no** redacta el contenido editorial: prepara el prompt, valida el spec, materializa los bloques en Notion y escribe la evidencia en repo.

## Qué este contrato NO hace

- No promueve este layout a regla runtime para CAND-002/CAND-003.
- No modifica `SKILL.md`, `CALIBRATION.md` ni `ROLE.md` persistentes.
- No define un nuevo agente.
- No automatiza la replicación.
- No archiva, borra ni reemplaza la subpágina errónea ni la versión simple existente.

Una vez David valide la versión completa de la trazabilidad de CAND-004 como formato, se evaluará promover este contrato a regla del template editorial mediante un cambio explícito y revisado.
