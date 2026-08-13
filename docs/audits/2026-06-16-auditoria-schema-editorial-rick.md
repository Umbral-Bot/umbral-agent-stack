# Auditoría de Schema Editorial Rick — Fuente de Verdad y Flexibilidad

**Autor**: Copilot (auditoría técnica)  
**Fecha**: 2026-06-16  
**Objetivo**: Validar si los supuestos sobre el esquema editorial de Rick (Observatorio Umbral BIM, 9 artículos) son reales, flexibles o solo documentación.

**Estado de los 9 artículos**: NO EXISTEN en el repositorio actual. Esta auditoría es **preventiva** antes de su generación.

> **Nota de cierre — 2026-08-13 (PKG-MACRO-P5-L1-T4).** `audience_stage` admite **cinco**
> valores, no cuatro: `awareness | consideration | trust | conversion | **retention**`.
> La opción `retention` existía en la base viva de Publicaciones desde antes de mayo; el
> schema local se alineó en 0.3.0 (PKG-MACRO-P5-L1-T3, GO de David = opción A: el spec sigue
> a la base y la opción NO se borra de Notion), y este paquete cierra el desfase que quedaba
> en las dos superficies que esta auditoría declara **fuente de verdad para enums**:
> `infra/editorial_gold_set.py` y `evals/editorial/gold-set.schema.json`, que hasta hoy
> rechazaban una pieza `retention` como `invalid audience_stage`.
>
> Qué cambia y qué no en este documento: las **listas prescriptivas** («usar estos valores»),
> los checklists y el **prompt copiable de §13** pasan a cinco valores, porque son lo que se
> sigue usando. Las **mediciones del 2026-06-16 quedan intactas** —incluidos los bloques que
> citan el código tal como estaba ese día— para que la auditoría siga contando lo que
> encontró. El conflicto `cold/warm/hot` de la spec v1 **no se reabre aquí**: sigue abierto y
> fuera del alcance de este paquete.

---

## 1. Resumen Ejecutivo

### Conclusión: Schema Rick es **PROPUESTO + PARCIALMENTE IMPLEMENTADO + FLEXIBLE PERO CON RESTRICCIONES**

- **Fuente de verdad**: Múltiple y con **inconsistencias críticas** no resueltas.
- **Código como autoridad**: Los validadores en `infra/editorial_gold_set.py` son la fuente de verdad **más reciente** (diferente de la spec documental).
- **Frontmatter YAML**: NO hay validador local. La validación ocurre en Notion API.
- **Flexibilidad detectada**:
  - ✅ Acepta valores nuevos si no conflictúan con enums
  - ✅ Permite español e inglés en la mayoría de campos
  - ❌ `audience_stage` tiene restricción FUERTE (inconsistencia grave a resolver)
  - ❌ Status tienen máquina de estado rígida
  - ❌ Sin `aprobado_contenido=true` ni `autorizar_publicacion=true`, nada publica

### Riesgos inmediatos

| Riesgo | Severidad | Acción |
|--------|-----------|--------|
| `audience_stage`: spec dice `cold/hot`, código valida `awareness/trust` | 🔴 CRÍTICA | Usar valores del **código** (`awareness`, `consideration`, `trust`, `conversion`, `retention` desde 2026-08-13). Ignorar spec v1.md |
| 9 artículos generados con valores de spec antiguo | 🔴 CRÍTICA | Validar contra código en `infra/editorial_gold_set.py`, no contra docs |
| `planbim.cl` usado como fuente primaria | 🟡 MEDIA | NO usar. Reemplazar por fuentes vigentes (CORFO, MINVU, buildingSMART, etc.) |
| Frontmatter markdown SIN validación local | 🟡 MEDIA | Copilot debe validar antes de escribir Notion. No confiar en Notion API como gate único |
| Gates humanos (`aprobado_contenido`, `autorizar_publicacion`) requeridos | 🟢 INFO | Esperado. David marca manualmente; Rick respeta gates |

---

## 2. Fuente de Verdad Encontrada

### 2.1 Jerarquía de autoridad (en orden de confiabilidad)

| Orden | Fuente | Ubicación | Estado | Conflictos | ✓ Usar para |
|-------|--------|-----------|--------|-----------|------------|
| **1** | **Código validador** | `infra/editorial_gold_set.py` | VIVO, activo | `audience_stage`: usa `awareness|consideration|trust|conversion` — **+ `retention` desde 2026-08-13** | **FUENTE DE VERDAD PARA ENUMS** |
| **2** | **Spec v1** | `docs/specs/sistema-editorial-rick-v1.md` | PROPUESTO | `audience_stage`: dice `cold|warm|hot` (CONFLICTO) | Flujos, gates, decisiones producto |
| **3** | **Schema YAML Notion** | `notion/schemas/publicaciones.schema.yaml` | draft | Menciona `awareness` pero también `cold/warm/hot` | Estructura Notion DB |
| **4** | **ADRs** | `docs/adr/ADR-005/-008/-010/-011` | Accepted | Complementan spec v1 | Decisiones arquitectónicas |
| **5** | **Oro-set editorial** | `evals/editorial/gold-set.schema.json` | vivo | Ejemplos de casos de evaluación | Ejemplos de uso |
| **6** | **Worker code** | `worker/tasks/editorial_publish.py` | vivo | Valida gates y publica | Integración blog |

### 2.2 Conflictos resueltos

**CONFLICTO CRÍTICO ENCONTRADO**: `audience_stage`

```yaml
# Spec v1.md (línea 99):
"Audiencia": Select | "cold" / "warm" / "hot"

# Código (infra/editorial_gold_set.py, línea 33):
VALID_AUDIENCE_STAGES = frozenset({
    "awareness",
    "consideration", 
    "trust",
    "conversion",
})

# Gold set (evals/editorial/gold-set-minimum.yaml):
audience_stage: awareness    # NO "cold"
audience_stage: consideration  # NO "warm"
audience_stage: trust         # NO "hot"
```

**RESOLUCIÓN**: El **código es la autoridad**. Use `awareness`, `consideration`, `trust`, `conversion`, `retention`.

_(El bloque de código de arriba cita el validador tal como estaba el 2026-06-16, con cuatro
valores; `retention` se sumó el 2026-08-13 — ver la nota de cierre al principio.)_

---

## 3. Tabla de Campos Frontmatter — Análisis Completo

| Campo | Existe en Spec | Existe en Código | Obligatorio | Valores Permitidos | Flexible | Control | Recomendación |
|-------|---|---|---|---|---|---|---|
| **title** | ✅ Sí | ✅ (worker) | ✅ Sí | Texto libre, max 300 | ✅ Alto | Notion status | Texto libre. Max 120 chars recomendado para LinkedIn |
| **slug** | ✅ Sí | ✅ (worker) | ✅ Sí | `^[a-z0-9]+(?:-[a-z0-9]+)*$` | ❌ Rígido | Regex | Lowercase kebab-case. Generado automático o manual validado |
| **status** | ✅ Sí | ✅ (worker) | ✅ Sí | `draft \| ready_for_review \| content_approved \| publish_authorized \| scheduled \| published \| archived` | ❌ Máquina de estado | Notion status type | Sigue transiciones. Rick no toca `ready_for_review`→`content_approved` (David humano) |
| **author** | ✅ Sí | ✅ (worker) | ❌ No (default: "David Moreira") | Texto libre | ✅ Alto | Rich text | Generalmente "David Moreira". Permite otros autores |
| **publication_type** o **tipo_pieza** | ✅ Sí (spec §5) | Parcial (spec example) | ✅ Sí | `tecnico_corto \| reflexivo \| producto \| post_mortem \| caso_estudio \| tutorial \| opinion \| recap \| docencia \| respuesta_publica` | ✅ Medio (valores predefinidos) | Notion select | Usar valores predefinidos. El código NO valida esto en gold-set (gap) |
| **primary_channel** o **canal** | ✅ Sí (spec §5) | ✅ (code: `linkedin\|blog\|x` al 2026-06-16) | ✅ Sí | `blog \| linkedin \| x \| newsletter` | ✅ Medio | Notion select | **Los 4 desde 2026-08-13**: el «solo 3 en v1 / newsletter para v2» se levantó por GO de David (misma higiene que `retention`), y `VALID_CHANNELS` ya acepta `newsletter` |
| **secondary_channels** | ✅ Sí (spec §5) | Parcial | ❌ No (opcional) | Subset de canales primarios | ✅ Medio | Notion multi-select | Opcional. Valor default: none |
| **series** | ✅ Sí (spec §5) | Parcial | ❌ No (opcional) | Texto libre (nombre serie) | ✅ Alto | Notion select o rich text | Opcional. "Observatorio Umbral BIM" para 9 artículos |
| **category** | ✅ Sí (spec implícito via tags) | Parcial | ❌ No | Texto libre | ✅ Alto | Notion multi-select | Opcional. Tags preferido |
| **tags** | ✅ Sí (spec §11) | ✅ (worker: `list[str]`) | ✅ Sí (≥1) | Texto libre, lista | ✅ Alto | Notion multi-select | Mínimo 1 tag. Texto libre, idioma flexible |
| **audience** (sinónimo de audience_stage) | ✅ Sí (spec §5) | ❌ NO (usa `audience_stage`) | ✅ Sí | ⚠️ **CONFLICTO**: Spec dice `cold/warm/hot` | ❌ **USAR CÓDIGO** | Notion select | **CRÍTICO**: Usar `awareness`, `consideration`, `trust`, `conversion`, `retention` (del código) |
| **objective** | ✅ Sí (spec §5, §10.1) | Parcial | ✅ Sí | `autoridad \| enablement \| validacion \| activacion \| memoria` | ✅ Medio | Notion select | Valores predefinidos |
| **cta_type** | ✅ Sí (spec §10.1) | Parcial | ✅ Sí (o `no_cta_reason` si none) | `none \| conversacion \| validacion_problema \| recurso \| diagnostico \| discovery \| producto \| educacion` | ✅ Medio | Notion select | Valores predefinidos. Rate-limiting aplicado |
| **cta_strength** | ✅ Sí (spec §5) | Parcial | ✅ Sí | `none \| soft \| medium \| strong` | ✅ Bajo | Notion select | Valores rígidos. Reglas en spec §10.3 |
| **audience_stage** | ✅ Sí (spec §5) | ✅ **CÓDIGO** | ✅ Sí | **`awareness \| consideration \| trust \| conversion \| retention`** | ❌ **RÍGIDO EN CÓDIGO** | Notion select | **USAR VALORES DEL CÓDIGO, no de spec** (`retention` desde 2026-08-13) |
| **evidence_density** | ✅ Sí (spec §5) | Parcial | ✅ Sí | `low \| med \| high` | ✅ Bajo | Notion select | Valores rígidos |
| **funnel_stage** | ✅ Sí (spec §5, §10.5) | Parcial | ✅ Sí | `memory \| enablement \| validation \| activation` | ✅ Bajo | Notion select | Valores rígidos (mapean a §10.5 capas) |
| **commercial_intent** | ✅ Sí (spec §5) | Parcial | ✅ Sí | `none \| low \| med \| high` | ✅ Bajo | Notion select | Valores rígidos |
| **needs_fact_check** | ✅ Sí (spec implícito) | ❌ NO EN CÓDIGO | ❌ No (opcional) | `true \| false` | ✅ Flexible | Checkbox o nota | **RECOMENDACIÓN**: Implementar como metadata. Ver §5 abajo |
| **source_files** | ✅ Sí (spec §11) | Parcial | ❌ No | URLs lista | ✅ Alto | URL multi o rich text | Archivos fuente para fact-check |
| **primary_sources** | ✅ Sí (spec implícito) | ✅ (spec §5, gold-set) | ✅ Sí (si no es `no_external_source`) | URLs, referencias normaivas | ✅ Medio | Notion url + rich text | **CRÍTICO**: NO usar `planbim.cl`. Ver §6 abajo |
| **image.idea** o **featured_image_idea** | ✅ Sí (spec §9) | Parcial | ❌ No (opcional) | Texto descripción | ✅ Alto | Rich text | Brief de asset visual |
| **image.description** o **featured_image_description** | ✅ Sí (spec §9) | Parcial | ❌ No | Texto descripción | ✅ Alto | Rich text | Descripción para diseñador/IA |
| **image.alt** o **featured_image_alt** | ✅ Sí (spec §11) | ✅ (worker: condicional) | ✅ Condicional (si `featured_image_url` presente) | Texto libre | ✅ Alto | Rich text | **OBLIGATORIO si hay imagen**. Max 125 chars recomendado |
| **hashtags** | ✅ Sí (spec implícito) | ❌ NO EN CÓDIGO | ❌ No (opcional) | `#tag1 #tag2` formato | ✅ Flexible | Rich text | Para LinkedIn/X. Opcional |
| **aprobado_contenido** | ✅ Sí (spec §6) | ✅ (worker: gate) | ✅ Sí (gate humano) | `true \| false` | ❌ NO (David solo) | Checkbox | **Rick NUNCA marca true**. Solo David. Gate 1. |
| **autorizar_publicacion** | ✅ Sí (spec §6) | ✅ (worker: gate) | ✅ Sí (gate humano) | `true \| false` | ❌ NO (David solo) | Checkbox | **Rick NUNCA marca true**. Solo David. Gate 2. Requiere `aprobado_contenido=true` |

---

## 4. Mapping de Valores — Recomendaciones

### 4.1 `audience_stage`: **CORRECCIÓN OBLIGATORIA**

Tabla de mapping (De valores humanos o antiguos → Valores del código):

| Valor Propuesto | Código Aceptado | Mapa a |
|-----------------|-----------------|---------|
| `cold` | ❌ NO VÁLIDO | → `awareness` (first-time awareness) |
| `warm` | ❌ NO VÁLIDO | → `consideration` (exploring options) |
| `hot` | ❌ NO VÁLIDO | → `trust` (ready to engage) + `conversion` (ready to buy) |
| `awareness` | ✅ VÁLIDO | *uso directo* |
| `consideration` | ✅ VÁLIDO | *uso directo* |
| `trust` | ✅ VÁLIDO | *uso directo* |
| `conversion` | ✅ VÁLIDO | *uso directo* |
| `retention` | ✅ VÁLIDO (desde 2026-08-13) | *uso directo* |
| `TOFU` (top-of-funnel) | N/A | → `awareness` |
| `MOFU` (mid-of-funnel) | N/A | → `consideration` |
| `BOFU` (bottom-of-funnel) | N/A | → `trust` o `conversion` |

**Acción**: Reemplazar en todos los 9 artículos los valores `cold/warm/hot` (si aparecen) por `awareness/consideration/trust/conversion`, según el mapping de arriba. (`retention` es válido desde 2026-08-13, pero ningún valor de `cold/warm/hot` mapea a él: se elige a propósito, no por conversión automática.)

### 4.2 Otros mappings idiomáticos

| Valor Humano/ES | Valor Código | Notas |
|-----------------|--------------|-------|
| `conversación` | `conversacion` | Español sin tilde en código. Normalizar a código |
| `autodiagnóstico` | `diagnostico` | Normalizar: código es versión corta |
| `bajo` | `low` | Código usa inglés |
| `medio` | `med` | Código usa inglés (`med` no `medium`) |
| `alta` | `high` | Código usa inglés |
| `técnico corto` | `tecnico_corto` | Snake-case sin tildes |
| `reflexivo` | `reflexivo` | OK tal cual |
| `opinión` | `opinion` | Sin tilde en código |
| `aprobado contenido` | `aprobado_contenido` | Snake-case en Notion |
| `autorizar publicación` | `autorizar_publicacion` | Snake-case sin tilde |

---

## 5. Análisis de Flexibilidad Detectada

### 5.1 Campos RÍGIDOS (no acepta valores nuevos)

- ✅ `status`: máquina de estado fija. No acepta valores custom.
- ✅ `slug`: regex obligatorio `^[a-z0-9]+(?:-[a-z0-9]+)*$`. No acepta spaces, tildes ni mayúsculas.
- ✅ `audience_stage`: validador en código rechaza valores fuera de set fijo. **NO FLEXIBLE**.
- ✅ `primary_channel`: los 4 del select `Canal` (`blog`, `linkedin`, `x`, `newsletter`).
  El «solo 3 en v1 / `newsletter` para v2» rigió hasta el 2026-08-13, cuando el GO de
  David lo levantó y `VALID_CHANNELS` sumó `newsletter` — ver la fila de §3 y la nota de
  cierre al principio.
- ✅ `cta_strength`: solo 4 valores (`none|soft|medium|strong`).
- ✅ `cta_type`: 8 valores predefinidos. Sin personalizaciones.
- ✅ `evidence_density`: 3 valores (`low|med|high`). Binning fijo.
- ✅ `funnel_stage`: 4 capas (spec §10.5). No escalables.
- ✅ `commercial_intent`: 4 niveles (`none|low|med|high`).

### 5.2 Campos FLEXIBLES (acepta valores nuevos o texto libre)

- ✅ `title`: texto libre. Max 120 chars recomendado (no validado si menor).
- ✅ `tags`: lista libre. Notion crea selects nuevos automáticamente.
- ✅ `series`: texto libre o select. Notion puede crear nueva opción.
- ✅ `category`: texto libre.
- ✅ `author`: texto libre. Default "David Moreira".
- ✅ `featured_image_idea`, `featured_image_description`: texto libre.
- ✅ `objective`: predefinido pero sin validación en código (spec §5).
- ✅ `tipo_pieza`: predefinido pero sin validación en código (spec §5).
- ✅ `hashtags`: texto libre.
- ✅ `source_files`, `primary_sources`: URLs libres.

### 5.3 Campos CONDICIONALES (dependen de otros)

- ❓ `aprobado_contenido`: solo David puede marcar `true`. Rick puede dejar `false`.
- ❓ `autorizar_publicacion`: requiere `aprobado_contenido = true` primero. David solo.
- ❓ `featured_image_alt`: obligatorio SI `featured_image_url` presente. Sino, opcional.
- ❓ `cta_text`: obligatorio SI `cta_type ≠ none`. Sino, puede ser empty.
- ❓ `no_cta_reason`: obligatorio SI `cta_type = none`. Else, N/A.

---

## 6. Fuentes y Regla sobre `planbim.cl`

### 6.1 Búsqueda de `planbim.cl` en repo

**Resultado**: NO aparece en el repositorio actual. Es un **riesgo preventivo** a evitar.

### 6.2 Regla editorial obligatoria

**NO USAR `planbim.cl` COMO FUENTE PRIMARIA.** 

Razones:
- Dominio no conforme con vigencia reglamentaria BIM Chile (CORFO/MINVU).
- Riesgo de link rot o contenido desactualizado.
- Mejor usar fuentes oficiales:

| Categoría | Fuentes Válidas | Evitar |
|-----------|---|---|
| **Legislación BIM Chile** | CORFO oficial, MINVU decreto, Construye2025 | planbim.cl (no oficial) |
| **Estándares** | buildingSMART ISO 19650, UK BIM Framework, RICS, NIST, ISO 27000 | Blogs no verificados |
| **Organismos** | Red BIM Gobiernos Latinoamericanos, IDB/BID, buildingSMART | Medium, substack |
| **Académico** | Papers DOI/arXiv, publicaciones peer-reviewed | Preprints sin revisión |
| **Empresarial** | Autodesk blogs oficiales, Trimble whitepapers, reportes Gartner | Agregadores genéricos |

### 6.3 Acción para los 9 artículos

- ✅ Revisar cada `primary_sources` y `source_files` en cada artículo.
- ✅ Si aparece `planbim.cl`, reemplazar por fuente verificable (ej: enlace CORFO directo).
- ✅ Si no hay fuente verificable, marcar `needs_fact_check: true` o degradar esa sección a "contexto editorial" en lugar de "hecho verificado".

---

## 7. Validación de los 9 Artículos (Estructura Esperada)

### 7.1 Nombres de archivos esperados

(Según request del usuario)

```
14_Articulos/Copilot/
├── 01_el-proceso-primero-la-ia-despues.md
├── 02_gobernar-datos-antes-que-modelar-mas-rapido.md
├── 03_cde-no-es-carpeta.md
├── 04_bep-documento-vivo.md
├── 05_antes-de-responder-preguntar.md
├── 06_que-sabe-que-asume-que-valida.md
├── 07_bim-manager-datos-decisiones-agentes.md
├── 08_profesional-aec-flujos-verificables.md
├── 09_tendencias-bim-2026-interoperabilidad-agentes-trazabilidad.md
├── 00_auditoria_schema_rick_cursor.md (ESTE ARCHIVO)
```

**Estado actual**: ❌ NO existen. Auditoría preventiva.

### 7.2 Frontmatter esperado por artículo

```yaml
---
title: "..."
slug: el-proceso-primero-la-ia-despues
status: ready_for_review
author: David Moreira
publication_type: tecnico_corto
primary_channel: linkedin
secondary_channels: [blog]
series: Observatorio Umbral BIM
category: Automatización
tags: [BIM, IA, Procesos, Automatización]
audience: awareness                          # ← USAR CÓDIGO: awareness/consideration/trust/conversion/retention
objective: autoridad
cta_type: conversacion
cta_strength: soft
cta_destination: null                        # ← Si cta_type = none, usar no_cta_reason
evidence_density: high
funnel_stage: memory
commercial_intent: none
needs_fact_check: false
source_files: []
primary_sources:
  - url: "https://buildingsmart.org/..."
    title: "buildingSMART Specification"
image:
  idea: "Diagrama de proceso BIM-IA iterativo"
  description: "Mostrar flujo: Datos → IA → Validación → Decisión"
  alt: "Diagrama de bucle iterativo entre proceso BIM e IA"
hashtags: "#BIM #IA #Automatización #AEC"
---

# El proceso primero, la IA después

...contenido markdown...
```

### 7.3 Validaciones pre-publicación

**Checklist** (antes de marcar `ready_for_review`):

- [ ] `slug`: Lowercase kebab-case, <60 chars, único
- [ ] `title`: <120 chars
- [ ] `audience_stage`: Uno de: `awareness|consideration|trust|conversion|retention` (**NO** `cold/warm/hot`)
- [ ] `cta_type`, `cta_strength`: Valores de spec §10.1
- [ ] Si `featured_image_url` existe: `featured_image_alt` presente y <125 chars
- [ ] Si `cta_type ≠ none`: `cta_text` y `cta_destination` lleños
- [ ] Si `cta_type = none`: `no_cta_reason` presente
- [ ] `tags`: ≥1 tag
- [ ] `primary_sources`: URLs verificables. ❌ NO `planbim.cl`
- [ ] Si fuente no verificable: `needs_fact_check: true`
- [ ] `author`: Default "David Moreira" o explícito
- [ ] Gates: `aprobado_contenido=false` (Rick), `autorizar_publicacion=false` (David)

---

## 8. Decisión Específica: `needs_fact_check`

### 8.1 Estado actual del campo

- ✅ Existe en **spec** (mencionado, implícito)
- ❌ NO existe en **código** de validación (editorial_gold_set.py)
- ❌ NO tiene validador en worker/editorial_publish.py

### 8.2 Recomendación

**IMPLEMENTAR `needs_fact_check` como METADATA EDITORIAL**, no como gate de publicación:

```yaml
# Opción A: Checkbox en Notion (más explícito)
needs_fact_check: false        # Si true → David revisa antes de aprobado_contenido

# Opción B: Tag (menos recomendado)
tags: [BIM, fact-check-needed]

# Opción C: Nota en campo 00_notas_de_fact_check.md (más manual)
00_notas_de_fact_check: "Verificar: dato de adopción BIM en Chile (§3)"
```

**Acción recomendada**: Usar **Opción A** (checkbox). David verifica antes de marcar `aprobado_contenido=true`.

---

## 9. Lista de Archivos que Requieren Corrección (Hallazgos)

### 9.1 Documentación conflictiva

| Archivo | Línea(s) | Conflicto | Acción |
|---------|----------|----------|--------|
| `docs/specs/sistema-editorial-rick-v1.md` | 99 | `audience_stage: cold/warm/hot` vs código | Actualizar a `awareness|consideration|trust|conversion|retention` o marcar como DEPRECATED — **sigue abierto** |
| `notion/schemas/publicaciones.schema.yaml` | (opciones) | Menciona `cold/warm/hot` | Actualizar opciones a código — **hecho** 2026-08-13 para `retention` (schema 0.3.0, PKG-MACRO-P5-L1-T3); el `cold/warm/hot` sigue abierto |
| `evals/editorial/gold-set.schema.json` | 58-62 | Enum correctos (`awareness|consideration|trust|conversion`) | OK. Mantener como fuente de verdad — **enum ampliado** el 2026-08-13 con `retention` (PKG-MACRO-P5-L1-T4) |

### 9.2 Código sin validadores

| Módulo | Campo | Estado | Acción |
|--------|-------|--------|--------|
| `infra/editorial_gold_set.py` | `tipo_pieza` | Predefinido en spec, NO validado en código | Agregar VALID_PUBLICATION_TYPES si se requiere validación fuerte |
| `infra/editorial_gold_set.py` | `objective` | Predefinido en spec, NO validado en código | Agregar VALID_OBJECTIVES |
| `worker/tasks/editorial_publish.py` | `needs_fact_check` | Campo propuesto, NO implementado | Agregar como gate opcional (warning log) |

---

## 10. Lista de Campos que NO Deben Tocarse

### 10.1 Gates humanos (PROHIBICIÓN EXPLÍCITA)

- ❌ **`aprobado_contenido`**: Rick NUNCA marca como `true`. Solo David.
- ❌ **`autorizar_publicacion`**: Rick NUNCA marca como `true`. Solo David.
- ❌ **`status` transiciones**: Solo transiciones válidas en máquina de estado (spec §6).

### 10.2 Campos auto-computados

- ❌ **`content_hash`**: Generado por worker. Rick no toca.
- ❌ **`published_at`**: Auto asignado en publicación exitosa.
- ❌ **`canonical_url`**: Generado por sistema (o David manualmente post-publicación).
- ❌ **`platform_post_id`**: Asignado por plataforma (LinkedIn/Ghost/X).
- ❌ **`last_publish_error`**: Auto-asignado por sistema.

---

## 11. Lista de Fuentes que Deben Reemplazarse

### 11.1 Búsqueda realizada

**Consulta**: Búsqueda repo-wide por `planbim`, referencias genéricas, links rot.

**Resultado**: 
- ✅ NO encontrado `planbim.cl` en repo actual.
- ❌ Riesgo preventivo a evitar en 9 artículos nuevos.

### 11.2 Fuentes por artículo a validar

(Este análisis se realiza UNA VEZ se generen los artículos)

---

## 12. Recomendación: `ready_for_review` vs `draft`

### 12.1 Estado actual de los 9 artículos

**Recomendación**: Mantener en **`draft`** hasta que:

1. ✅ Frontmatter completo y válido
2. ✅ `audience_stage` en `awareness|consideration|trust|conversion|retention` (NO `cold/warm/hot`)
3. ✅ Sin `planbim.cl` o fuentes no verificables
4. ✅ `featured_image_alt` presente si hay imagen
5. ✅ `tags` ≥ 1
6. ✅ `aprobado_contenido` = false, `autorizar_publicacion` = false

Recién ENTONCES → **`ready_for_review`** (Rick puede marcar).

David revisa, y si aprueba → marca **`aprobado_contenido = true`** → estado **`content_approved`**.

---

## 13. Prompt Final Recomendado para Copilot

Cuando generes los 9 artículos, sigue ESTE prompt:

```markdown
### Generación de 9 Artículos: Observatorio Umbral BIM

**Fuente de Verdad**: 
- Validar todos los valores de frontmatter contra infra/editorial_gold_set.py
- audience_stage: USAR awareness|consideration|trust|conversion|retention (NO cold/warm/hot)
- Otros campos: Ver tabla de §3 de 00_auditoria_schema_rick_cursor.md

**Checklist de Frontmatter** (por cada artículo):
1. title: <120 chars
2. slug: lowercase kebab-case <60 chars
3. status: draft (David marca ready_for_review)
4. audience_stage: awareness | consideration | trust | conversion | retention
5. cta_type: none | conversacion | validacion_problema | recurso | diagnostico | discovery | producto | educacion
6. cta_strength: none | soft | medium | strong
7. evidence_density: low | med | high
8. commercial_intent: none | low | med | high
9. funnel_stage: memory | enablement | validation | activation
10. primary_sources: URLs verificables (NO planbim.cl)
11. Si featured_image_url: agregar featured_image_alt <125 chars
12. tags: ≥1 tag

**Validaciones Pre-Escritura**:
- NO usar audience_stage: cold | warm | hot (DEPRECATED, usar awareness/trust/etc)
- NO usar planbim.cl como fuente
- Si claim numérico: fuente primaria verificable o marcar needs_fact_check: true
- Si cta_type ≠ none: cta_text y cta_destination obligatorios
- Si cta_type = none: no_cta_reason obligatorio

**Después de Generación**:
1. Leer cada artículo contra esta auditoría
2. Corregir audience_stage si es necesario
3. Validar primarias_sources
4. Rick marca status: ready_for_review
5. Copilot escribe a Notion
```

---

## 14. Riesgos si se Normaliza Demasiado

### 14.1 Riesgos de sobre-normalización

| Riesgo | Impacto | Mitigación |
|--------|--------|-----------|
| Forzar `audience_stage` a 4 valores cuando el contenido es "intermediate" | Pérdida granularidad editorial | Usar combinación con `funnel_stage` (4 valores) para 16 combinaciones |
| Eliminar flexibilidad de `tags` | Rigidez que requiere cambios de schema cada vez | Mantener tags como libre + multi-select creación dinámica |
| Eliminar `needs_fact_check` como gate | Sin visibilidad de content que requiere validación | Mantener como checkbox, no como bloqueo de publicación |

### 14.2 Beneficios de normalización correcta

- ✅ Validación previa a Notion API (costo y latencia reducidos)
- ✅ Evals reproducibles (gold-set cases)
- ✅ Auditoría de publicaciones por estadísticas
- ✅ Rate-limiting y reglas de negocio aplicables

---

## 15. Riesgos si NO se Normaliza

### 15.1 Riesgos de bajo control

| Riesgo | Impacto | Probabilidad |
|--------|--------|-------------|
| Artículos con `audience_stage: cold` (valor antiguo) | Validador código rechaza en eval → pieza no pasa gates | ALTA |
| `planbim.cl` usado como primary_source | Fact-check auditoría detecta fuente no vigente | ALTA (si no se valida manualmente) |
| `featured_image_alt` faltante cuando hay imagen | Worker rechaza publicación a blog | MEDIA |
| CTA sin `cta_text` y `cta_destination` | Publicación blog sin CTA legible | MEDIA |
| Tags vacíos | Deficiencia en búsqueda y clasificación | BAJA (metadata secundaria) |
| Gates humanos tocados por error | Publicación sin aprobación David | MUY BAJA (pero crítica si sucede) |

---

## 16. Conclusiones y Recomendaciones

### 16.1 Estado final: Schema Rick

- **Esrictez**: MEDIO-ALTO. Máquina de estado rígida pero campos de contenido flexibles.
- **Documentación**: INCONSISTENTE. Spec ≠ Código. **Código es autoridad**.
- **Implementación**: PARCIAL. Validadores en código, gates en Notion API.
- **Fronmatter YAML**: SIN VALIDADOR LOCAL. Validación ocurre en Notion.
- **Flexibilidad real**: MEDIA. Enums rígidos pero texto libre amplio para contenido.

### 16.2 Acciones inmediatas ANTES de generar 9 artículos

1. ✅ **Actualizar spec v1.md**: Reemplazar `audience_stage: cold/warm/hot` por `awareness|consideration|trust|conversion|retention`
2. ✅ **Actualizar schema YAML Notion**: Sincronizar enums con código
3. ✅ **Agregar validador de frontmatter YAML**: Script local que valide contra editorial_gold_set.py antes de Notion write
4. ✅ **Documentar mapping**: `cold→awareness`, `warm→consideration`, `hot→trust/conversion`
5. ✅ **Prohibir planbim.cl**: Checklist manual en auditoría de fuentes

### 16.3 Status de los 9 artículos

| Aspecto | Status | Acción |
|---------|--------|--------|
| ¿Pueden estar en `ready_for_review`? | ✅ SÍ (con checklist) | Usar checklist de §7.3 antes de marcar |
| ¿Necesitan `needs_fact_check: true`? | ⚠️ DEPENDE | Si claim sin verificable source |
| ¿Pueden permanecer `draft` hasta validar? | ✅ SÍ | RECOMENDADO para control de calidad |
| ¿Planbim.cl debe usarse? | ❌ NO | Buscar fuente verificable o marcar fact-check |

---

## 17. Artefactos Generados

Este documento es el archivo de auditoría solicitado:

```
14_Articulos/Copilot/00_auditoria_schema_rick_cursor.md
```

**Archivos NO modificados** (por regla de auditoría):
- Artículos originales (no existen aún)
- Código de validación
- Especificación v1 (mantener para referencia histórica; marcar inconsistencias)

---

## 18. Próximos Pasos

1. **Revisión por David**: Validar si mapping `cold→awareness` es correcto para su modelo mental
2. **Crear validador YAML local**: Script que valide frontmatter antes de write Notion
3. **Generar 9 artículos**: Usando prompt §13 como template
4. **Auditoría post-generación**: Re-ejecutar este análisis con artículos reales
5. **Cierre**: Marcar artículos `ready_for_review` si pasan todas validaciones

---

**Fin de auditoría.**

Auditor: Copilot  
Fecha: 2026-06-16  
Confianza: ALTA (código como fuente de verdad confirma incongruencias).
