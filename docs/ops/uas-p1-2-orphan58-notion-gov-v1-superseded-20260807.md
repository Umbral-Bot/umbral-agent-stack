# Notion governance V1 — descartado a favor de V2 (nota de archivo)

> Archivado junto con los 6 paths en
> [docs/archive/notion-governance-v1-2026-03/](archive/notion-governance-v1-2026-03/), rescatados
> desde `codex/notion-governance-v1-contract` @ `2221f5af` (2026-03-31, sin merge-base con `main`).
> Ver evaluación completa en [uas-p1-2-orphan58-cherry5-20260807.md](uas-p1-2-orphan58-cherry5-20260807.md) §2.5.

## Qué proponía V1

Un contrato de gobernanza Notion con **staging obligatorio**: `raw → sesión capitalizable →
capitalización` (ADR-005), un modelo operativo de 9 tipos de objeto canónico
(`02-operating-model-v1.md`), una matriz de permisos `comment/propose/edit` por superficie
(`02-permissions-by-surface.md`), reglas de anclas obligatorias antes de editar
(`03-capitalization-rules.md`), y bindings surface↔env_var↔handler con placeholders
(`runtime-bridge-contract.yaml`, `taxonomies-v1.yaml`).

## Por qué no es vigente

El slot `ADR-005` de `main` hoy es `publicacion-multicanal` — tema distinto por coincidencia de
número, **no** una renumeración de este ADR. No hubo re-emisión formal del pivote. La arquitectura
V2 real es `docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md`: flujo directo
`raw → classify_raw → capitalize_task_from_raw` (project-first, **sin** la capa de staging
`capitalizable_session` de V1), taxonomía Dominio/Tipo/Destino (no las 8 tablas de selects de
`taxonomies-v1.yaml`), permisos como guardrails G1–G7 (no la matriz `comment/propose/edit`), y
bindings reales verificados en VPS (no placeholders `<RAW_SESSIONS_DB_ID>`). La gobernanza viva hoy
día a día es la skill `.claude/skills/notion-governance-runtime/SKILL.md`.

## Por qué se archiva igual

Ningún doc V2 actual explica *que* el diseño con staging obligatorio se descartó a favor del flujo
directo — ese pivote arquitectónico quedaba huérfano de traza. Este archivo + los 6 paths
(encabezado `SUPERSEDED` en cada uno) dejan constancia histórica sin reintroducir V1 como vigente:
no se creó ningún `docs/policies/`, `registry/`, ni `docs/adr/ADR-005-*` en superficies activas de
`main`.
