---
name: notion-governance-runtime
description: Alinear cualquier trabajo sobre Notion, Granola, smart replies, task pages, comentarios, surfaces canónicas y Control Room con la gobernanza V2 y la utilidad real para David. Úsala cuando la tarea toque experiencia de David en Notion o posibles conflictos V1/V2.
---

# Notion Governance Runtime

## Objetivo

Forzar que Claude trate Notion como el espacio de trabajo de David y no como un log interno del sistema, alineando cualquier cambio o diagnóstico contra la gobernanza viva disponible en `/home/rick/notion-governance-git`.

## Superficies de referencia

- Gobernanza viva: `/home/rick/notion-governance-git`
- Runtime/deploy reference: `/home/rick/umbral-agent-stack`
- Clean working copy: `/home/rick/umbral-agent-stack-main-clean`

## Cuándo usar esta skill

Úsala cuando la tarea toque:

1. `smart_reply`
2. `notion.*`
3. `granola.*`
4. comentarios hacia David en Control Room
5. páginas de tarea o artefactos en Notion
6. surfaces `raw`, `project`, `task`, `deliverable`, bridge, dashboard
7. conflictos entre V1 y V2

## Reglas operativas

1. **Notion es user-facing.** Todo lo que vea David debe ser útil, corto y comprensible.
2. **Silencio > acuse vacío.** No dejar “Recibido”, “Procesando”, ni confirmaciones sin valor.
3. **No telemetría interna.** No mostrar `comment_id`, `trace_id`, modelo, task técnico, IDs internos, etc.
4. **Español claro.** Todo output visible para David debe quedar en español natural.
5. **Superficie canónica primero.** Si la gobernanza V2 define una superficie canónica, no reintroducir la surface legacy por comodidad.
6. **Control Room no es basurero.** No usarlo para dumps, self-talk o reportes internos que deberían vivir en objetos canónicos.
7. **Si encuentras conflicto V1/V2, explícitalo.** No lo tapes con wording neutro sin explicarlo en el diagnóstico.

## Flujo recomendado

### 1. Leer la gobernanza antes de proponer

No asumas el contrato. Revisa el repo de gobernanza y extrae:

- surfaces activas
- surfaces legacy
- campos obligatorios
- reglas de promoción/capitalización
- expectativas de interacción con David

### 2. Comparar contra el runtime real

Revisa:

- código que escribe comentarios
- código que crea páginas o tasks
- pipeline Granola
- task pages y comentarios actuales
- cualquier metadata que se esté filtrando a Notion

### 3. Clasificar cada cosa

Para cada interacción Notion importante, decide si es:

- valor real para David
- coordinación útil
- telemetría interna mal expuesta
- ruido
- legacy V1 incompatible con V2

### 4. Proponer cambios mínimos primero

Antes de rediseñar todo, prioriza:

- quitar ruido visible
- quitar telemetría visible
- mover la información al objeto correcto
- alinear fields obligatorios
- dejar claro qué bloquea la migración completa a V2

## Qué debe quedarse fuera del output a David

- trailers tipo `(comment_id=...)`
- modelos seleccionados
- trace IDs
- “Task técnico”
- “Procesando…” si no aporta una acción real verificable
- auto-narración del agente

## Qué sí debe sobrevivir

- resultados reales
- bloqueos concretos
- preguntas de ambigüedad que realmente requieran decisión humana
- links al artefacto canónico correcto
- cambios de estado útiles

## Antipatrones

- usar Notion como consola del sistema
- mantener V1 por inercia cuando V2 ya es la referencia
- confundir trazabilidad técnica con comunicación útil para David
- dejar la UX de Notion gobernada por conveniencia del runtime en vez de por utilidad real
