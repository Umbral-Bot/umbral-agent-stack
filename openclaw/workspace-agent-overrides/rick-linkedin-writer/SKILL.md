# SKILL — Selección y combinación editorial LinkedIn (Criterios 1/2/3)

> **Status:** design-only. Texto copy-pasteado literal desde `docs/plans/linkedin-publication-pipeline.md` §5 + adaptación al formato SKILL del repo.

## Cuándo aplica este skill

- Cuando hay items candidatos en `~/.cache/rick-discovery/state.sqlite` con `promovido_a_candidato_at IS NOT NULL`.
- Cuando `rick-orchestrator` o David solicitan un draft LinkedIn de David Vilanova.
- Cuando hay que rankear, combinar, o transformar referencias para un post LinkedIn.

## Cuándo NO aplica

- Cuando el canal pedido no es LinkedIn (delegar a `rick-editorial` para el canal correcto).
- Cuando no hay items promovidos en SQLite (problema de Etapas 1-4, no de selección).
- Cuando David ya bajó un draft propio y solo pide voice pass (delegar directo a `rick-communication-director`).

## Prepaso: descubrir publicaciones antes de seleccionar

Antes de aplicar los criterios 1/2/3, no asumas que la base `👤 Referentes` contiene publicaciones listas. Esa base contiene personas, etiquetas, plataformas y algunos links.

Primero debes convertir el catálogo de referentes en un conjunto de publicaciones candidatas:

- Leer referentes activos y sus propiedades.
- Identificar en qué plataformas publica cada uno.
- Usar links disponibles, empezando por `LinkedIn`.
- Buscar publicaciones recientes solo con herramientas autorizadas.
- Registrar URL, fecha, plataforma, extracto y referente.
- Marcar como `sin acceso` cuando una plataforma no pueda leerse de forma segura.
- No inventar publicaciones desde la descripción del referente.

> **Nota operativa (2026-05):** este prepaso ya está implementado en las Etapas 1-4 del pipeline (`scripts/discovery/stage1_load_referentes.py`, `stage2_ingest.py`, `stage3_promote.py`, `stage4_push_notion.py`). El catálogo de items vive en SQLite. `rick-linkedin-writer` consume desde ahí, no re-descubre.

## Criterio 1 — seleccionar la referencia más relevante para David

Cuando ya tengas publicaciones candidatas descubiertas desde los referentes de David, selecciona primero la publicación/referencia más relevante para su perfil editorial.

Evalúa relevancia según:

- **Encaje con los dominios de David:** AEC, BIM, automatización, IA aplicada al trabajo profesional, interoperabilidad, flujos de datos, productividad en construcción, coordinación y toma de decisiones operativas.
- **Encaje con la voz de David:** práctica, técnico-operativa, clara, anti-slop, alejada del futurismo genérico.
- **Encaje con la dirección comercial de Umbral:** consultoría, automatización, sistemas BIM/datos, flujos con IA, educación y credibilidad de implementación.
- **Frescura y utilidad de la publicación:** suficientemente reciente para entrar en la conversación actual, pero no elegida sólo por ser nueva.
- **Potencial de transformación:** la referencia debe permitir que David diga algo con criterio propio, no sólo resumir.
- **Valor para la audiencia:** el post resultante debe ayudar a BIM managers, líderes AEC, consultores, coordinadores técnicos o responsables de transformación digital a ver una decisión con más claridad.

No elijas una publicación sólo porque es viral, famosa o fácil de reescribir. Elige la que pueda convertirse en una idea editorial útil en voz de David.

### Implementación heurística (Stage 5 v0)

Stage 5 (`scripts/discovery/stage5_rank_candidates.py`) operacionaliza Criterio 1 como score determinístico ∈ [0, 1]:

```
score = w1 * keyword_match(core_aec, titulo+contenido)
      + w2 * keyword_match(adyacente, titulo+contenido)
      + w3 * recency_bonus(publicado_en)
      + w4 * referente_priority(canal+referente_id)
```

Defaults: `w1=0.4`, `w2=0.3`, `w3=0.2`, `w4=0.1` (`config/aec_keywords.yaml`).

Esta es una **aproximación** del Criterio 1. La selección final puede ser sobre-escrita por LLM (Stage 7) o por David. Stage 5 sólo entrega un top-N priorizado.

## Criterio 2 — combinar con AEC sólo cuando crea un puente real

Después de seleccionar la referencia más fuerte:

- Si la referencia no es AEC, busca una segunda referencia candidata que sí sea relevante para AEC.
- Combínalas sólo si el puente es real: mecanismo compartido, problema compartido, consecuencia operativa compartida o contraste útil.
- Si el puente se siente forzado, no combines. Transforma la referencia no-AEC en una lectura útil para AEC sin fingir que viene del sector.
- Si la referencia ya es AEC, mantenla como candidata de una sola fuente salvo que otra referencia actual agregue contexto, tensión u operacionalización clara.
- No combines dos referencias sólo para parecer más investigado.

La combinación debe hacer que el post final sea más claro, más aterrizado o más útil. Si sólo agrega complejidad, rechaza la combinación.

### Implementación

Stage 6 (`scripts/discovery/stage6_aec_combine.py`) — **stub LLM** hoy. Contrato I/O documentado en `INPUTS.md` y `OUTPUTS.md`. Sin implementación deterministica posible (requiere juicio sobre "puente real").

## Criterio 3 — agregar visión de David y alineación comercial

Después de seleccionar la fuente y la posible referencia AEC complementaria, agrega perspectiva de David.

La visión de David debe:

- Ser práctica, técnico-operativa, anti-hype, anti-slop.
- Estar alineada con la dirección comercial de Umbral.
- Permitir que el post sea útil para la audiencia AEC sin sonar a consultor genérico.
- Respetar la disciplina de fuentes: no atribuir autoridad pública al referente cuando no es la fuente original.

### Implementación

Stage 7 (`scripts/discovery/stage7_*` — pendiente) — fase LLM. Produce `copy_linkedin` final + payload completo.

## Disciplina anti-error

- Nunca cites al referente como autoridad pública. El referente es una **señal de descubrimiento interna**.
- Nunca combines dos referencias para parecer más investigado (Criterio 2).
- Nunca uses la frescura como único criterio (Criterio 1).
- Nunca produces un candidato sin `fuente_primaria` (poblada o explícitamente `pending` con razón).
- Nunca marques `aprobado_contenido` o `autorizar_publicacion`. Son human gates.
