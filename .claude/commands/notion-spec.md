# Notion Spec → Implementation — Umbral Agent Stack

Convierte un spec de Notion en issues de Linear + páginas de plan en Notion.
Usa los MCPs Notion y Linear que Claude Code tiene conectados.

## Flujo rápido

1. Buscar el spec: `notion-search` con el nombre o tema
2. Leerlo: `notion-fetch` sobre el page_id
3. Crear el plan en Notion (página de implementación)
4. Crear los issues en Linear bajo el team "Umbral"
5. Linkear spec ↔ plan ↔ issues

## Contexto del proyecto Umbral

**Workspace Notion:** workspace del usuario David
**Team Linear:** `Umbral` (team ID: `a586e97e-6ca8-45d7-8a38-bbd0c5cdb0cc`)
**Proyectos Linear activos:**
- `Mejora Continua Agent Stack` — mejoras al stack, routing, evals
- Buscar otros con `list_projects` filtrando por team Umbral

**Bases de Notion relevantes:**
- Control Room / Dashboard gerencial — `docs/22-notion-dashboard-gerencial.md`
- Bitácora / Log de operaciones
- Usar `notion-search` para localizar la DB de tareas del proyecto

## Paso a paso

### 1. Localizar el spec
```
notion-search: "<nombre del spec o feature>"
notion-fetch: <page_id del resultado>
```

Extraer de la página:
- Objetivo y alcance
- Requisitos funcionales
- Criterios de aceptación
- Dependencias y riesgos
- Fases propuestas

### 2. Crear plan en Notion
```
notion-create-pages en la misma sección del spec o en el proyecto
```
Incluir: resumen, fases, dependencias, criterios de éxito, link al spec.

### 3. Crear issues en Linear

Para cada fase o componente del spec:
```
save_issue:
  team: Umbral
  project: <proyecto correspondiente>
  title: [Slice N] <acción> — <componente>
  description: ## Contexto\n<extracto del spec>\n\n## Criterios\n- ...
  priority: 2 (High) para core, 3 (Normal) para mejoras
  labels: según área (System, Agent Stack, etc.)
```

Convención de título del repo: `[Slice N] Verbo — descripción`

### 4. Actualizar el spec
```
notion-update-page: agregar sección "Implementación" con links al plan y a los issues
```

## Sizing de issues
- 1 issue = máximo 2 días de trabajo
- Si es más grande, partir en slices numerados: `[Slice 1]`, `[Slice 2]`, etc.
- Cada slice debe ser deployable/verificable por separado

## Archivos de referencia
- `docs/14-codex-plan.md` — plan maestro del proyecto
- `docs/11-roadmap-next-steps.md` — roadmap S0-S7
- `docs/61-audit-traceability-governance.md` — gobernanza de entregables
- `AGENTS.md` — protocolo de coordinación inter-agentes
