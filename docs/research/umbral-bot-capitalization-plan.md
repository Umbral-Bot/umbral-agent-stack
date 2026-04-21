# Umbral Bot — Plan de Capitalización

> **Estado**: PROPUESTO — pendiente de revisión humana
> **Creado**: 2026-04-21
> **Autor**: Copilot (sesión de capitalización)
> **Repo destino**: `umbral-bot-copilot` (TypeScript/React, Lovable Cloud, Supabase)
> **Repo origen docs**: `umbral-agent-stack-codex-coordinador` (este repo)

---

## Objetivo

Proponer los artefactos que se deben crear o actualizar en el repositorio `umbral-bot-copilot` para capitalizar la investigación Perplexity sobre Umbral Bot. Este documento **no implementa nada** — es un bridge document que lista qué hay que crear, dónde, con qué fuentes, en qué prioridad y con qué dependencias.

> **Regla**: este repo (`umbral-agent-stack-codex-coordinador`) NO edita archivos de `umbral-bot-copilot`. Solo propone.

---

## Inventario de fuentes Perplexity para Umbral Bot

IDs y temas según [perplexity-master-index.md](perplexity-master-index.md). Solo se listan documentos canónicos o pendientes de integrar.

### Documentos temáticos numerados

| ID | Tema real | Estado en índice | Capitalización |
|----|-----------|------------------|----------------|
| UB-01 | Implementación BIM — 4 planos de análisis | canónico — pendiente de integrar | **No capitalizado** |
| UB-02 | Anatomía estructural BEP/PEB — comparativa Chile/ES/UK | canónico — pendiente de integrar | **No capitalizado** |
| UB-03 | Intake conversacional — 35 variables, suficiencia S0-S3 | canónico — pendiente de integrar | **No capitalizado** |
| UB-04 | Evaluation lab — 15 dimensiones, RAGAS + humano | canónico — parcialmente capitalizado | Parcial: `docs/agent-evaluation-lab.md` |
| UB-05 | Recomendaciones comerciales — trust, sycophancy, guardrails | canónico — fase 2 | **No capitalizado — diferido** |
| UB-06 | Panel admin + gobernanza datos | canónico — fase 2 | **No capitalizado — diferido** |
| UB-07 | Gobernanza multiagente completa (5 archivos: marco, KB governance YAML, routing, antipatrones MAST) | canónico — parcialmente capitalizado | Parcial: `docs/agent-catalog-proposal.md`, `docs/kb-package-architecture.md` |
| UB-08 | KB Dynamo/pyRevit — 9 subdominios, fuentes | canónico — pendiente de integrar | **No capitalizado** |
| UB-09 | Grasshopper/Rhino — decisión de priorización, 4 vectores | canónico — fase 2 | **No capitalizado — diferido** |
| UB-10 | Routing — cascada regex→embeddings→LLM | canónico — pendiente de integrar | **No capitalizado** |

### Documentos raíz canónicos relevantes

| ID | Tema real | Uso para capitalización |
|----|-----------|------------------------|
| UB-R2 | Validación expertises v2 | Catálogo de expertises del bot, priorización de dominios |
| UB-R3 | Corpus BIM público Chile | Input para KB package Chile |
| UB-R4 | Corpus openBIM / IFC | Input para KB package openBIM |
| UB-R5 | Corpus Revit | Input para KB package Revit general |
| UB-R6 | Corpus BEP/PEB/SDI | Input para KB package BEP/PEB e intake conversacional |
| UB-R7 | Corpus licitación BIM | Input para KB package licitación |
| UB-R8 | Corpus BIM público España | Input para KB package España |
| UB-R9 | CDE / coordinación BIM | Input para KB package CDE, flujos ISO 19650 |
| UB-R11 | Plan general de KB | Arquitectura de KB packages |
| UB-R17 | BEP/PEB agente experto | Diseño del agente BEP, system prompt |
| UB-R19 | BIM 5D / cuantificación / Presto / BC3 | KB package 5D, software regional |

### Documentos no usados en este plan

| ID | Tema | Razón de exclusión |
|----|------|--------------------|
| UB-R1 | Expertises v1 | **Histórico** — sustituido por UB-R2 |
| UB-R10 | Investigación Speckle | Periférico — Speckle en flujo de cambio |
| UB-R12, R14, R15, R16 | APS (research, KB, MCP, docs map) | Periféricos — no priorizados para v1 |
| UB-R13 | AEC tools research | Periférico — solo contexto |
| UB-R18 | España detalle (tar.gz) | Periférico — archivo comprimido sin extraer |
| UB-R20 | README organizacional de carpeta | Accesorio |

---

## Artefactos propuestos

### 1. KB Package YAML Contracts

| Campo | Detalle |
|-------|---------|
| **Qué crear** | Schema YAML para KB packages + 1-2 packages de ejemplo (BEP/PEB como primer candidato) |
| **Ruta sugerida** | `agents/schemas/kb-package-schema.yaml`, `agents/packages/bep-peb.yaml` |
| **Fuentes Perplexity** | UB-07 P2 `research_p2_kb_governance.md` (lifecycle, formatos, ownership, versioning). Corpus para packages de ejemplo: UB-R6 (BEP/PEB/SDI), UB-R11 (plan general KB) |
| **Prioridad** | **P1** — fundacional para routing y evaluación |
| **Dependencias** | Ninguna (schema standalone) |
| **Tipo** | Diseño + schema |
| **Docs existentes** | `docs/kb-package-architecture.md` (propuesta previa, verificar alineación) |
| **Entregable** | Schema YAML validable, 2 packages ejemplo, README de convenciones |

### 2. Spec Intake BEP (Conversational)

| Campo | Detalle |
|-------|---------|
| **Qué crear** | Spec del flujo conversacional de intake para BEP consulting |
| **Ruta sugerida** | `docs/specs/intake-bep-v1.md` |
| **Fuentes Perplexity** | UB-03 (35 variables de intake, stages S0-S3, branching conversacional). Soporte: UB-02 (anatomía BEP/PEB), UB-R6 (corpus BEP/PEB/SDI), UB-R17 (agente experto BEP) |
| **Prioridad** | **P1** — define el producto conversacional core |
| **Dependencias** | KB packages (para saber qué knowledge necesita el intake) |
| **Tipo** | Diseño |
| **Docs existentes** | Ninguno específico para intake BEP |
| **Entregable** | Spec con variables, stages, decision tree, validation rules, fallback paths |

### 3. Spec Routing v1 (Cascading)

| Campo | Detalle |
|-------|---------|
| **Qué crear** | Spec del sistema de routing multi-KB con cascading |
| **Ruta sugerida** | `docs/specs/routing-v1.md` |
| **Fuentes Perplexity** | UB-10 (cascada regex→embeddings→LLM, thresholds, abstain rate). Soporte: UB-07 P3 `research_p3_routing.md` (routing y handoffs inter-agente) |
| **Prioridad** | **P1** — define cómo el bot selecciona knowledge |
| **Dependencias** | KB package schema (para saber qué se rutea) |
| **Tipo** | Diseño |
| **Docs existentes** | Parcialmente en `docs/ARCHITECTURE.md` (verificar) |
| **Entregable** | Spec con pipeline stages, fallback logic, confidence thresholds, metrics |

### 4. Gold Set Evaluation Framework

| Campo | Detalle |
|-------|---------|
| **Qué crear** | Framework de evaluación con gold set + 15 dimensiones |
| **Ruta sugerida** | `agents/evals/gold-set-framework.md`, `agents/evals/dimensions.yaml`, `agents/evals/gold-set-bep.yaml` |
| **Fuentes Perplexity** | UB-04 (laboratorio evaluación: 15 dimensiones, scoring rubrics, gold set design). Soporte: UB-07 P4 `research_p4_antipatterns.md` (antipatrones a evaluar) |
| **Prioridad** | **P1.5** — necesario antes de evaluar routing y calidad de respuestas. Routing no puede iterarse sin un gold set que mida calidad, latencia y UX de las respuestas ruteadas |
| **Dependencias** | KB packages (para gold set content). Nota: routing depende de gold set para su evaluación, no al revés |
| **Tipo** | Diseño + datos |
| **Docs existentes** | `docs/agent-evaluation-lab.md` (propuesta previa — **parcialmente capitalizado**, reconciliar), `agents/evals/` (directorio existente) |
| **Entregable** | Framework doc, schema de dimensiones, 1 gold set de ejemplo para BEP |

### 5. Gobernanza Multiagente (5 archivos)

| Campo | Detalle |
|-------|---------|
| **Qué crear** | Framework de gobernanza para los agentes del bot |
| **Ruta sugerida** | `agents/policies/governance-framework.md`, `agents/policies/escalation-rules.yaml`, `agents/policies/capability-boundaries.yaml`, `agents/policies/audit-log-spec.md`, `agents/policies/release-process.md` |
| **Fuentes Perplexity** | UB-07 completo (5 archivos: P1 marco de decisión, P2 KB governance, P3 routing/handoffs, P4 antipatrones MAST) |
| **Prioridad** | **P2** — importante para multi-agent coordination pero no bloquea primer agent |
| **Dependencias** | KB packages, routing (para definir qué gobierna cada policy) |
| **Tipo** | Diseño + config |
| **Docs existentes** | `agents/CAPABILITY-MATRIX.md`, `agents/RELEASE-GATES.md` (parcialmente cubren esto — **parcialmente capitalizado**, reconciliar) |
| **Entregable** | 5 documentos/configs alineados con UB-07, reconciliados con archivos existentes |

### 6. KB Packages de dominio (corpus)

| Campo | Detalle |
|-------|---------|
| **Qué crear** | KB packages concretos para los dominios priorizados |
| **Ruta sugerida** | `agents/packages/bep-peb.yaml`, `agents/packages/implementacion-bim.yaml`, `agents/packages/dynamo-pyrevit.yaml` |
| **Fuentes Perplexity** | UB-01 (implementación BIM), UB-02 (anatomía BEP/PEB), UB-08 (Dynamo/pyRevit). Corpus: UB-R3 (Chile), UB-R4 (openBIM), UB-R5 (Revit), UB-R6 (BEP/PEB/SDI), UB-R7 (licitación), UB-R8 (España), UB-R9 (CDE), UB-R19 (5D) |
| **Prioridad** | **P2** — depende del schema P1 estar definido |
| **Dependencias** | KB Package YAML Contracts (artefacto 1) |
| **Tipo** | Datos + config |
| **Docs existentes** | Ninguno — los corpus Perplexity son la fuente |
| **Entregable** | 3-5 packages YAML conformes al schema, con fuentes trazables |

---

## Matriz de prioridad y secuencia

```
P1 (bloquea todo lo demás)
  ├── KB Package YAML Contracts  ← fundacional (UB-07 P2, UB-R11)
  ├── Spec Intake BEP            ← producto core (UB-03, UB-02, UB-R6, UB-R17)
  └── Spec Routing v1            ← cómo el bot decide (UB-10, UB-07 P3)

P1.5 (necesario antes de iterar routing)
  └── Gold Set Evaluation         ← calidad (UB-04)
      Routing no puede iterarse sin gold set: necesita mediciones de
      calidad, latencia y UX para validar thresholds y cascading.

P2 (necesario pre-producción)
  ├── Gobernanza Multiagente      ← coordinación (UB-07 completo)
  └── KB Packages de dominio      ← contenido (UB-01, UB-02, UB-08, corpus UB-R*)

Diferido (no tocar todavía)
  ├── Routing implementation       ← requiere gold set evaluado
  ├── Specialist activation        ← requiere routing + gobernanza
  ├── UB-05: Recomendaciones comerciales      ← fase 2
  ├── UB-06: Panel admin / data governance    ← fase 2
  └── UB-09: Grasshopper/Rhino               ← fase 2

Secuencia sugerida:
  KB Package Schema → Gold Set Evaluation → Intake BEP → Routing Spec →
  Gobernanza → KB Packages dominio
  (Schema primero porque gold set, routing, intake y packages dependen
  de la estructura. Gold set antes de routing porque routing necesita
  métricas de evaluación para calibrar thresholds.)

Primer PR en umbral-bot-copilot:
  Schema YAML real (kb-package-schema.yaml) + 1 package ejemplo (bep-peb.yaml).
  Scope mínimo, no incluye routing ni gobernanza.
```

---

## Estado de capitalización parcial

Algunos artefactos ya existen parcialmente en `umbral-bot-copilot`:

| Archivo existente | Fuente Perplexity | Estado | Acción |
|-------------------|-------------------|--------|--------|
| `docs/kb-package-architecture.md` | UB-07 P2, UB-R11 | Parcial | Reconciliar con KB YAML contracts. Puede ser la base |
| `docs/agent-evaluation-lab.md` | UB-04 | Parcial | Reconciliar con gold set framework. Expandir con 15 dimensiones |
| `docs/agent-catalog-proposal.md` | UB-07 P1 | Parcial | Reconciliar con gobernanza multiagente |
| `agents/CAPABILITY-MATRIX.md` | UB-07 | Parcial | Reconciliar con capability-boundaries |
| `agents/RELEASE-GATES.md` | UB-07 | Parcial | Reconciliar con release-process |

### Verificar antes de crear (no hay certeza de contenido)

| Archivo existente | Acción |
|-------------------|--------|
| `docs/ARCHITECTURE.md` | Verificar que routing spec no contradiga |
| `docs/ROADMAP.md` | Alinear prioridades propuestas con roadmap actual |
| `agents/schemas/` | Verificar si ya existe schema YAML para KB |
| `agents/evals/` | Verificar estado actual del directorio de evaluaciones |

---

## Fuentes Perplexity no capitalizadas en este plan (lower priority)

| ID | Tema real | Uso futuro |
|----|-----------|------------|
| UB-05 | Recomendaciones comerciales | Guardrails, trust calibration — fase 2 |
| UB-06 | Panel admin / data governance | Modelo de datos admin, RBAC, catálogo KB — fase 2 |
| UB-09 | Grasshopper/Rhino | KB package `rhino_gh_aec_bridge` — fase 2 |
| UB-R2 | Validación expertises v2 | Priorización de dominios al planificar KB packages |
| UB-R19 | BIM 5D | KB package 5D — puede entrar en P2 junto con KB packages de dominio |

---

## Reglas de ejecución

1. **NO implementar desde este repo**. Solo proponer artefactos para `umbral-bot-copilot`.
2. Cada artefacto debe crearse en una sesión dedicada con el Perplexity source abierto.
3. Antes de crear, hacer `git status` en `umbral-bot-copilot` para verificar estado limpio.
4. Cada artefacto es un PR independiente con referencia al ID de fuente Perplexity.
5. Reconciliar con archivos existentes ANTES de crear — no duplicar.
6. Toda spec debe incluir: alcance v1, fuera de alcance, decisiones pendientes, criterios de aceptación.
7. **No arrastrar IDs inventados**. Solo usar IDs del [perplexity-master-index.md](perplexity-master-index.md).
