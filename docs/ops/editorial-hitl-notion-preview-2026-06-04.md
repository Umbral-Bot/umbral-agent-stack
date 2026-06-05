# Editorial HITL — Preview Notion (dry-run 2026-06-04)

- **Veredicto:** `EDITORIAL_HITL_NOTION_PREVIEW_OK` (desde spec + CAND docs; live Notion requiere MCP en sesión con auth).
- **DB canónica:** `Publicaciones` — `e6817ec4698a4f0fbbc8fedcf4e52472`
- **Spec:** `docs/specs/sistema-editorial-rick-v1.md` §5–§6
- **Cero publicación:** ningún canal externo; gates en `false` hasta orden explícita de David.

## Flujo en 5 pasos (lo que David debe ver en Notion)

```text
1. Rick crea/actualiza fila (Estado: draft / ready_for_review)
2. David revisa copy + asset → marca Aprobado contenido = true  (GATE 1)
3. David revisa canal/momento → marca Autorizar publicación = true (GATE 2)
4. Rick (o automatización) prepara payload LinkedIn/Ghost — sin publicar aún
5. David dice "ok, publica" en chat → única salida externa permitida
```

## Tabla de gates (propiedades Notion)

| Propiedad (spec v1) | Tipo | Quién puede `true` | Qué desbloquea | Valor en dry-run |
|---------------------|------|-------------------|----------------|------------------|
| `Aprobado contenido` | Checkbox | **Solo David** | Pasar a autorización de salida | `false` |
| `Autorizar publicación` | Checkbox | **Solo David** (requiere gate 1) | Preparar/publicar por canal | `false` |
| `ready_for_publication` (si existe en live) | Checkbox | Automación solo si ambos gates true | Worker/n8n handoff | `false` |
| `Estado` / pipeline | Select | Rick propone; David corrige | Visibilidad en board | `draft` o `ready_for_review` |
| `Publication URL` | URL | Post-publicación | Evidencia | vacío |
| `Last publish error` | Text | Sistema | Debug | vacío |

Rick **nunca** debe marcar los dos checkboxes de aprobación.

## UX recomendada en Notion

1. **Vista “Cola David”** — filtro: `ready_for_review` AND `Aprobado contenido` = false.
2. **Vista “Listo para autorizar”** — `Aprobado contenido` = true AND `Autorizar publicación` = false.
3. **Vista “Autorizado (sin publicar)”** — ambos true AND `Publication URL` empty — para revisar payload antes de `ok, publica`.

Si las propiedades live difieren del spec, registrar drift en Mejora Continua (no renombrar sin gobernanza).

## CAND de referencia

| Candidato | Uso |
|-----------|-----|
| CAND-002 | Source-driven; DB Publicaciones documentada |
| CAND-001 | Opinion operativa |

Para dry-run live: crear fila título `[DRY-RUN] HITL preview 2026-06-04` o abrir CAND-002 y **solo leer** gates.

## Wave 2 (siguiente PRs, no este doc)

- Ghost primer canal automatizable con HITL.
- LinkedIn: token lifecycle + preview; ver `docs/ops/core-first` PROMPT 6.
- Separar plan de implementación de torneos/MC.

## Verificación live (pendiente agente con Notion MCP)

```text
Query DB e6817ec4698a4f0fbbc8fedcf4e52472 — 1 fila CAND-002 o DRY-RUN
Confirmar nombres exactos de propiedades Aprobado contenido / Autorizar publicación
Screenshot o URL de página para David
```
