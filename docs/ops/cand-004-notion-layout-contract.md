# CAND-004 Notion Layout Contract (experimental prototype)

> **Date**: 2026-05-05
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Status**: experimental — prototype only, NOT a runtime rule
> **Scope**: defines a reusable navigable layout for editorial candidate pages in Notion. Applied first to CAND-004 as a prototype. Replication to CAND-002/CAND-003 requires explicit human approval.

## Objetivo

Especificar una estructura de página Notion **navegable, escaneable en menos de 2 minutos**, que mantenga las categorías de información ya producidas para CAND-003 pero las reorganice por jerarquía y plegado para evitar la saturación visual de la página actual de CAND-003.

CAND-004 es un prototipo de presentación. NO es publicación, NO marca gates, NO sustituye drafts activos.

## Problema observado en CAND-003

- 343 bloques top-level tras append de V-E (10 alternativas + ranking + QA).
- Toda la información clave (premisa, ranking, alternativas) compite con detalle de evidencia.
- Para decidir qué alternativa elegir David tiene que scrollear por contenido auxiliar.
- No hay primera-pantalla ejecutiva.
- Categorías existentes son correctas; el problema es el orden y el plegado.

## Categorías heredadas (mantener)

- Premisa / tesis
- Mapa argumental (problema → arg → contra → solución)
- Alternativas (V-Exx) con LinkedIn + X
- Evaluación (ComDir, QA, ranking interno)
- Trazabilidad y fuentes
- Gates y seguridad
- Historial de generación

## Reglas de UX

1. **Primera pantalla = decisión humana**. Estado, premisa, mapa del discurso y alternativas resumidas deben caber en menos de 2 minutos de lectura.
2. **Detalle largo va plegado**. Toggles para alternativas completas, evaluación dimensional, trazabilidad y QA.
3. **Toggles preferidos** sobre subpáginas mientras el contenido quepa. Subpáginas sólo si una alternativa supera ~50 bloques o si la API obliga por límite de children.
4. **No paredes de texto**. Tablas para resúmenes, bullets para listas, code blocks sólo para copy publicable.
5. **Estado siempre visible arriba** y repetido abajo: `prototipo / no aprobado / no publicar / no gates marcados`.
6. **Source trace** en cada alternativa, no como bloque global suelto.

## Estructura de página obligatoria

Orden y nivel de cada sección. H1 reservado para el título de página.

| # | Sección | Nivel | Plegado | Contenido mínimo |
|---|---------|-------|---------|------------------|
| 1 | Resumen Ejecutivo | H2 | abierto | Estado + recomendación pendiente + qué decide David + 4–6 anchor links |
| 2 | Premisa De La Idea | H2 | abierto | Una frase de tesis + tensión editorial + qué NO está diciendo |
| 3 | Mapa Del Discurso | H2 | abierto | Problema, Argumento 1, Argumento 2, Contraargumento, Contra-contraargumento, Solución, Cierre/pregunta — bullets |
| 4 | Alternativas Para Elegir | H2 | abierto | Tabla resumen: ID · Nombre · Característica · Cuándo elegirla · Riesgo principal · Estado |
| 5 | Shortlist | H2 | abierto | Top 1, Top 2, Reserva, Por qué, Microedición requerida |
| 6 | Alternativas Completas | H2 | toggles | Una toggle por V-Exx con LinkedIn + X + diferencia clave + pros + riesgos + microedits + source_trace + qa_status |
| 7 | Evaluación Comparativa | H2 | toggles | Tabla dimensional (voz, claridad, naturalidad, AEC/BIM, claim discipline, abstracción, tono consultor, ranking) dentro de toggle |
| 8 | Trazabilidad | H2 | toggle | Fuentes · Evidencia · Inferencia · Hipótesis · No verificado |
| 9 | Gates Y Seguridad | H2 | abierto | No publicado · No aprobado · No gates marcados · Draft activo intacto · Qué falta para publicar |
| 10 | Historial De Generación | H2 | toggle | Agentes · Prompts · Validaciones · Archivos de evidencia |
| 11 | Archivo / Detalle Largo | H2 | toggle | Cualquier dump pesado adicional |

## Decisión toggle vs subpágina

- **Toggle** por defecto.
- **Subpágina** si la alternativa contiene >50 bloques o supera límite Notion de children por request.
- Para el prototipo CAND-004, alternativas se modelan como **toggles** (cumplen el límite y mejoran legibilidad).

## Restricciones de seguridad obligatorias

- No tocar propiedades de la página padre.
- No modificar `Estado`, `aprobado_contenido`, `autorizar_publicacion`, `gate_invalidado`, `Copy LinkedIn`, `Copy X`, `canal_publicado`, `published_at`, `published_url` en CAND-002/CAND-003.
- No crear claims aprobatorios en el contenido.
- No persistir secretos.
- No reemplazar drafts activos.

## Validaciones requeridas (pre-write)

Sobre el `page_spec` YAML/JSON producido por OpenClaw:

- `candidate_id == "CAND-004"`.
- `ready_for_publication: false`.
- `ready_for_human_review` ausente o `false`.
- `premise` no vacío.
- `discourse_map` con las 7 claves.
- `alternatives_summary` con al menos 3 entradas y campos completos.
- `alternatives_full` alineado a IDs de `alternatives_summary`.
- `gates_and_safety` presente con marca de no publicado.
- Sin claims de aprobación humana.
- Sin instrucciones para marcar gates.
- Sin tokens, secretos, ni mención a CAND-002/CAND-003 que altere su estado.

## Validaciones requeridas (post-write)

- Página existe en Notion bajo CAND-003 como subpágina prototipo.
- Título contiene `CAND-004` y la palabra `Prototipo`.
- Bloques principales presentes en orden.
- Premisa, mapa del discurso y resumen de alternativas en la primera pantalla.
- Alternativas completas dentro de toggles (no expuestas top-level).
- Marcadores `prototipo / no aprobado / no publicar` presentes.
- CAND-002 y CAND-003 sin cambios en propiedades ni en bloques.

## Qué este contrato NO hace

- No promueve este layout a regla runtime para CAND-002/CAND-003.
- No modifica `SKILL.md`, `CALIBRATION.md` ni `ROLE.md` persistentes.
- No define un nuevo agente.
- No automatiza la replicación.

Una vez David valide CAND-004 como formato, se evaluará promover este contrato a regla del template editorial mediante un cambio explícito y revisado.
