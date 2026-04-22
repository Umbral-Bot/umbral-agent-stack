# Índice Maestro — Investigaciones Perplexity

> **Creado**: 2026-04-21
> **Estado**: vivo — actualizar cuando se agregue o retire investigación
> **Carpeta raíz**: `G:\Mi unidad\04_Recursos\Referencias e Investigacion\Investigacion\Perplexity\`

---

## Convenciones

| Estado | Significado |
|--------|-------------|
| **canónico** | Fuente de verdad activa. Usar como referencia para specs, ADRs y prompts |
| **histórico** | Versión anterior superada por un documento canónico más reciente. Conservar pero no referenciar |
| **redundante** | Cubierto por otro documento canónico. Ver columna "sustituido por" |
| **periférico** | Tangencialmente útil. No alimenta decisiones directas en v1 |
| **pendiente de integrar** | Canónico pero aún no capitalizado en specs ni implementación |
| **capitalizado** | Ya integrado en un spec, ADR o artefacto del repo |

---

## 1. Umbral Agent Stack

Ruta base: `G:\Mi unidad\04_Recursos\Referencias e Investigacion\Investigacion\Perplexity\Umbral Agent Stack\`

| ID | Carpeta | Archivo | Tema | Estado | Sustituido por | Alimenta decisión de… | No usar como fuente principal |
|----|---------|---------|------|--------|----------------|------------------------|-------------------------------|
| UA-01 | `01_Dolor de la audiencia aeco bim ia/` | (informe principal) | Dolor y audiencia AECO/BIM/IA | **canónico** | — | Perfil editorial David, system prompt Rick, audiencia objetivo | — |
| UA-02 | `02_Mapa de autoridad AECO - BIM - IA/` | (informe principal) | Mapa de autoridad y posicionamiento | **canónico** | — | Perfil editorial David, pilares temáticos, diferenciadores | — |
| UA-03 | `03_Benchmark Editorial Multicanal B2B/` | (informe principal) | Benchmark editorial multicanal | **canónico** | — | Contexto competitivo, frecuencia, formatos referencia | Solo como contexto; no contiene specs operativos |
| UA-04 | `04_Direccion Visual para Contenido Tecnico/` | (informe principal) | Dirección visual para contenido técnico | **canónico** | — | Guía de estilo visual, paleta, tipografía | — |
| UA-05 | `05_Radar de Noticias Reactivas para AECO y BIM/` | (informe principal) | Radar de noticias reactivas | **periférico** | — | Funcionalidad de radar reactivo (no priorizado v1) | No usar para v1; posible feature futura |
| UA-06 | `06_Marco Conceptual para Torneo de Prompts Editoriales/` | (informe principal) | Framework torneo de prompts | **canónico** | — | Evaluación y selección de prompts editoriales | — |
| UA-07 | `07_ Factibilidad de Publicación Automatizada Multicanal/` | `factibilidad_publicacion_automatizada.md` | Factibilidad publicación LinkedIn/X/Blog — v1 | **histórico** | **UA-10** | — | ⚠️ Superado por UA-10. No referenciar |
| UA-08 | `08_ Comparacion Visual Nano Banana Pro y Freepik/` | `capa_visual_editorial.md` | Comparativa visual Nano Banana Pro vs Freepik — v1 | **histórico** | **UA-11** | — | ⚠️ Superado por UA-11. No referenciar |
| UA-09 | `09_ CTAs para Contenido Técnico B2B/` | `cta-funnel-editorial.md` | CTAs para contenido técnico B2B — v1 | **histórico** | **UA-12** | — | ⚠️ Superado por UA-12. No referenciar |
| UA-10 | `10_ Investigación Sobre Publicación Automatizada/` | `informe-publicacion-editorial.md` | Publicación automatizada v2 — specs por canal | **canónico** | — | Spec sistema editorial (canales, endpoints, auth, rate limits, pricing), DB Publicaciones, adapters | — |
| UA-11 | `11_ Evaluación Visual Nano Banana vs Freepik/` | `capa-visual-rick-v1.md` | Capa visual Rick v2 — decisión arquitectural | **canónico** | — | ADR visual stack, asset_router, herramientas por caso de uso, licensing, riesgos preview | — |
| UA-12 | `12_ Diseno de CTA para Thought Leadership B2B/` | `cta-funnel-sistema-editorial.md` | CTA/funnel v2 — taxonomía + reglas de decisión | **canónico** | — | Tipos de CTA, reglas de decisión Rick, rate-limiting, metadata `cta_type`, funnel 4 capas, anti-patrones | — |
| UA-13 | `13_  Automatización Visual con Cuentas de Usuario/` | `UA-13_automatizacion_visual.md` | Automatización visual: API-first, prohibición UI automation, RPA limits | **canónico — capitalizado** | — | ADR-006 (API-first, Freepik API/MCP, prohibición UI automation), spec v1 §9, roadmap visual pipeline | Fuentes auxiliares: `ua13_freepik.md`, `ua13_google.md`, `ua13_rpa.md` |
| UA-14 | `14_ Orquestación Editorial con Make n8n y Cron/` | `UA-14-orquestacion-editorial.md` | Orquestación editorial: Agent Stack core + n8n bordes + Make lab | **canónico — capitalizado** | — | ADR-008 (orquestación editorial), roadmap arquitectura, backlog técnico n8n | Nota: informe menciona 4 bloques fuente (`ua14-bloque1-make.md` a `ua14-bloque4-patrones.md`) pero solo el integrado está en carpeta |

### Cadena de sustitución Agent Stack

```
UA-07 (factibilidad publicación v1)  →  sustituido por  →  UA-10 (publicación v2) ✅
UA-08 (visual v1)                    →  sustituido por  →  UA-11 (visual v2)      ✅
UA-09 (CTA v1)                       →  sustituido por  →  UA-12 (CTA v2)         ✅
```

> **Nota de trazabilidad UA-14**: el informe integrado referencia cuatro bloques fuente que no están presentes como archivos separados en la carpeta. El informe integrado es la fuente canónica; la ausencia de bloques no bloquea decisiones.

---

## 2. Umbral Bot

Ruta base: `G:\Mi unidad\04_Recursos\Referencias e Investigacion\Investigacion\Perplexity\Umbral Bot\`

### 2.1 Documentos raíz (primera pasada)

| ID | Archivo | Tema | Estado | Sustituido por | Alimenta decisión de… | No usar como fuente principal |
|----|---------|------|--------|----------------|------------------------|-------------------------------|
| UB-R1 | `2026-04-12-umbral-bot-expertises-perplexity-v1.md` | Expertises inicial | **histórico** | **UB-R2** | — | ⚠️ Superado por UB-R2 |
| UB-R2 | `2026-04-12-validacion-expertises…v2.md` | Validación expertises v2 | **canónico** | — | Catálogo de expertises del bot, priorización | — |
| UB-R3 | `corpus-bim-publico-chile.md` | Corpus BIM público Chile | **canónico** | — | KB package Chile, fuentes normativas | — |
| UB-R4 | `corpus-openbim-umbral-bot.md` | Corpus openBIM | **canónico** | — | KB package openBIM/IFC | — |
| UB-R5 | `corpus-revit-umbral-bot.md` | Corpus Revit | **canónico** | — | KB package Revit general | — |
| UB-R6 | `corpus-bep-peb-sdi-bim.md` | Corpus BEP/PEB/SDI | **canónico** | — | KB package BEP/PEB, intake conversacional | — |
| UB-R7 | `corpus-licitacion-bim-espana-chile.md` | Corpus licitación BIM | **canónico** | — | KB package licitación | — |
| UB-R8 | `corpus-bim-publico-espana.md` | Corpus BIM público España | **canónico** | — | KB package España, fuentes normativas | — |
| UB-R9 | `cde-bim-coordination-knowledge-base.md` | CDE / coordinación BIM | **canónico** | — | KB package CDE, flujos ISO 19650 | — |
| UB-R10 | `speckle-research.md` | Investigación Speckle | **periférico** | — | Migración Speckle (en curso) | Speckle en flujo de cambio; verificar antes de usar |
| UB-R11 | `umbral-bot-knowledge-base-plan.md` | Plan general de KB | **canónico** | — | Arquitectura de KB packages | — |
| UB-R12 | `aps-research.md` | APS research | **periférico** | — | Posible KB APS fase 2 | No priorizado para v1 |
| UB-R13 | `aec-tools-research (1).md` | AEC tools research | **periférico** | — | Contexto herramientas AEC | Solo como referencia |
| UB-R14 | `aps-knowledge-base-umbral.pplx.md` | APS KB | **periférico** | — | Posible KB APS fase 2 | No priorizado para v1 |
| UB-R15 | `aps-mcp-research.md` | APS MCP research | **periférico** | — | MCP tools APS (no priorizado) | No usar para v1 |
| UB-R16 | `aps-docs-deep-map.md` | APS docs deep map | **periférico** | — | Mapa de documentación APS | Solo como referencia |
| UB-R17 | `informe_bep_peb_agente_experto.md` | BEP/PEB agente experto | **canónico** | — | Diseño del agente BEP, system prompt | — |
| UB-R18 | `bim-espana-investigacion-detalle.tar.gz` | España detalle (comprimido) | **periférico** | — | — | Archivo comprimido sin extraer; bajo valor marginal |
| UB-R19 | `investigacion_5D_umbral_bot.md` | BIM 5D / cuantificación / Presto / BC3 | **canónico** | — | KB package 5D, software regional, fuentes técnicas | — |
| UB-R20 | `00-README.md` | Guía organizacional de la carpeta | **accesorio** | — | Convenciones de nombrado de research | — |

### 2.2 Documentos temáticos numerados (segunda pasada)

| ID | Carpeta | Archivo | Tema | Estado | Alimenta decisión de… | Capitalizado en repo |
|----|---------|---------|------|--------|------------------------|-----------------------|
| UB-01 | `01_Diseño de Agente Experto en Implementación BIM/` | `1_umbral_bot_implementacion_bim.md` | Implementación BIM — 4 planos de análisis | **canónico — pendiente de integrar** | System prompt del especialista, 4 planos (implementación/redacción/adopción/madurez) | No |
| UB-02 | `02_ Investigacion de Plantillas BEP y PEB/` | `bep_peb_estructura_informe.md` | Anatomía estructural BEP/PEB — comparativa Chile/ES/UK | **canónico — pendiente de integrar** | Generador de BEP, validación de secciones, comparativa regional | No |
| UB-03 | `03_Intake Conversacional para Agente BIM/` | `intake-conversacional-agente-bep.md` | Intake conversacional — 35 variables, suficiencia S0-S3 | **canónico — pendiente de integrar** | Spec intake, flujo de preguntas, batch design ≤5 | No |
| UB-04 | `04_Metodología de Benchmarking para Agentes BIM/` | `umbral_bot_evaluation_lab.md` | Evaluation lab — 15 dimensiones, RAGAS + humano | **canónico — parcialmente capitalizado** | Gold set, scoring pipeline, dimensiones de calidad | Parcial: `docs/agent-evaluation-lab.md` |
| UB-05 | `05_ Diseno de recomendaciones comerciales/` | `umbral_bot_recomendaciones_informe.md` | Recomendaciones comerciales — trust, sycophancy, guardrails | **canónico — fase 2** | Guardrails de recomendación, calibración de confianza | No |
| UB-06 | `06_ Diseño de Panel Admin y Gobernanza de Datos/` | `umbral_admin_governance_report.md` | Panel admin + gobernanza datos | **canónico — fase 2** | Modelo de datos admin, RBAC, catálogo de KB | No |
| UB-07 | `07_ Gobernanza de Sistema Multiagente Experto/` | 5 archivos (ver detalle) | Gobernanza multiagente completa | **canónico — parcialmente capitalizado** | Marco agente/modo/tool/KB, KB governance YAML, routing, antipatrones MAST | Parcial: `docs/agent-catalog-proposal.md`, `docs/kb-package-architecture.md` |
| UB-08 | `08_ Definir KB de Automatizacion BIM en Revit/` | `kb_dynamo_automatizacion_informe.md` | KB Dynamo/pyRevit — 9 subdominios, fuentes | **canónico — pendiente de integrar** | KB package `kb_dynamo_automatizacion`, fuentes a ingerir | No |
| UB-09 | `09_ Evaluación de Dominio Grasshopper y Rhino/` | `research_grasshopper_rhino_umbral_bot.md` | Grasshopper/Rhino — decisión de priorización | **canónico — fase 2** | KB package `rhino_gh_aec_bridge` (fase 2), 4 vectores productivos | No |
| UB-10 | `10_  Estrategias de Routing para Asistentes Técnicos/` | `routing-umbral-bot.md` | Routing — cascada regex→embeddings→LLM | **canónico — pendiente de integrar** | Spec routing v1, thresholds, métricas, abstain rate | No |

#### Detalle de UB-07 (5 archivos en la carpeta)

| Archivo | Contenido |
|---------|-----------|
| `umbral_bot_governance.md` | Informe integrado — documento de lectura principal |
| `research_p1_decision.md` | P1: Marco de decisión agente/modo/tool/KB |
| `research_p2_kb_governance.md` | P2: KB governance YAML contracts |
| `research_p3_routing.md` | P3: Routing y handoffs inter-agente |
| `research_p4_antipatterns.md` | P4: Antipatrones y MAST taxonomy |

### Cadena de sustitución Umbral Bot

```
UB-R1 (expertises v1)  →  sustituido por  →  UB-R2 (expertises v2) ✅
```

---

## 3. Documentos transversales

| ID | Ruta | Archivo | Tema | Proyecto | Estado |
|----|------|---------|------|----------|--------|
| TX-01 | `G:\Mi unidad\04_Recursos\…\Perplexity\` | `informe-pim-filesystem.md` | PIM / filesystem | Ambos | **periférico** |
| TX-02 | `G:\Mi unidad\04_Recursos\…\Perplexity\` | `informe-validacion-drive.md` | Validación estructura Drive | Ambos | **periférico** |
| TX-03 | `G:\Mi unidad\04_Recursos\…\Perplexity\Oferta y Comercializacion\` | `comercializacion-formacion-tecnica.md` | Comercialización formación técnica | Ambos | **periférico** |
| TX-04 | `G:\Mi unidad\04_Recursos\…\Perplexity\Oferta y Comercializacion\` | `evidencia-formacion-tecnica-aplicada.md` | Evidencia formación técnica aplicada | Ambos | **periférico** |

---

## 4. Resumen cuantitativo

| Categoría | Total | Canónicos | Históricos | Periféricos | Pendientes de integrar |
|-----------|-------|-----------|------------|-------------|----------------------|
| Agent Stack | 14 | 11 (01-06, 10-14) | 3 (07-09) | 0 | 3 (10, 11, 12) |
| Umbral Bot (raíz) | 20 | 10 | 1 (R1) | 7 (R10, R12-R16, R18) | 1 (R19) |
| Umbral Bot (numerados) | 10 (+5 sub-docs en UB-07) | 10 | 0 | 0 | 7 (01-03, 08, 10 nuevos; 04, 07 parciales) |
| Transversales | 4 | 0 | 0 | 4 | 0 |
| **Total** | **48** (+5 sub-docs) | **31** | **4** | **11** | **11** |

---

## 5. Reglas de uso

1. **Solo referenciar documentos canónicos** en specs, ADRs y prompts.
2. Los históricos (UA-07, UA-08, UA-09, UB-R1) **no se borran** pero se marcan con ⚠️ en cualquier referencia.
3. Cuando un documento pasa de "pendiente de integrar" a "capitalizado", actualizar esta tabla y agregar la ruta del artefacto en el repo.
4. Los periféricos pueden consultarse para contexto pero **no alimentan decisiones de diseño v1**.
5. Si se crea nueva investigación Perplexity, agregarla a este índice con estado inicial `pendiente de integrar`.
