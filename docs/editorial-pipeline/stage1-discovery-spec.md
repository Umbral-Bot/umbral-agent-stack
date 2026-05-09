# Stage 1 — Discovery Spec (STUB)

> **status:** STUB — pendiente Hilo 2
> **handoff:** este archivo es un placeholder creado por Hilo 1 (`wave1-h1-master-plan-drift-audit`). Hilo 2 debe completarlo con el contrato real S0/S1 (descubrimiento de publicaciones por canal, por referente).
> **scope esperado:** definir el contrato de descubrimiento de publicaciones nuevas a partir del catálogo `👤 Referentes`, hoy colapsado dentro de `scripts/discovery/stage2_ingest.py`.

## Contexto (drift audit)

- El doc histórico (`docs/plans/linkedin-publication-pipeline.md` línea ~241) declara que existe un `scripts/discovery/stage1_load_referentes.py`. **Ese script NO existe** en `main`.
- El SKILL `openclaw/workspace-agent-overrides/rick-linkedin-writer/SKILL.md` línea ~31 también lo cita. Falsa atribución.
- En la práctica, S0 (lectura Referentes) + S1 (descubrimiento publicaciones) ocurren dentro de `stage2_ingest.py`.
- Cobertura actual de canales: 14/26 referentes = 53.8% (gap analysis: `docs/audits/2026-05-08-pipeline-editorial-gap-analysis.md`).

## Decisión bloqueante (D1 master-plan §7)

**¿Se rompe S1 en script propio (`stage1_discover_publications.py`) o se mantiene colapsado en S2?**

- **Pro break:** testabilidad por canal, cobertura aislada, retry independiente.
- **Pro mantener:** menos archivos, lectura+ingesta+persistencia atómicas.
- **Owner decisión:** David. Hilo 2 NO la resuelve unilateralmente; debe documentar trade-offs y esperar.

## Índice esperado

1. **Inputs**
   - DB `👤 Referentes` (data source `afc8d960-086c-4878-b562-7511dd02ff76`).
   - Filtros: referente activo, confianza canales ≥ MEDIA, sin flag `POSIBLE_INACTIVO` salvo override.
2. **Canales soportados (estado real)**
   - LinkedIn activity feed: 2/5 productivo.
   - RSS feed: parcial (`RSS_NO_CONFIRMADO` flag).
   - YouTube channel: parcial.
   - Web/Newsletter: parcial.
   - Otros canales: best-effort.
3. **Output canónico**
   - Items en SQLite `~/.cache/rick-discovery/state.sqlite`.
   - Schema: `referente_id`, `canal`, `url`, `publicado_en`, `extracto`, `titulo`, `contenido`, `estado_procesamiento`, etc.
4. **Dedup**
   - Reglas de deduplicación por URL canónica + por referente.
5. **Errores tolerados / fallbacks**
   - Canal inaccesible → marcar `sin_acceso`, no abortar pipeline.
6. **Tests obligatorios**
   - Mock por canal. Cero llamadas HTTP reales en CI.
7. **Telemetría**
   - ops_log events: `discovery.referente_loaded`, `discovery.channel_probed`, `discovery.publication_ingested`, `discovery.dedup_skip`, etc.

## TODO Hilo 2

- [ ] Decidir D1 (break vs mantener) — esperar input de David.
- [ ] Documentar contrato de salida exacto (schema SQLite columnas + tipos).
- [ ] Mapear las 10 columnas de canales `👤 Referentes` a la lógica de descubrimiento.
- [ ] Documentar política de retry por canal.
- [ ] Documentar timeout y rate-limit por plataforma.
- [ ] Tests goldenset por canal (sin llamadas reales).

## Restricciones (Ola 1)

- NO modificar `stage7_5_*.py` (FROZEN).
- NO publicar.
- NO crear superficies Notion nuevas.
- Tests obligatorios al tocar código.
- Cero llamadas HTTP reales a LinkedIn en tests.

## Referencias

- Master plan: [`./master-plan.md`](./master-plan.md) (§1 stages, §7 D1).
- Drift audit: [`../audits/2026-05-08-editorial-drift-audit.md`](../audits/2026-05-08-editorial-drift-audit.md).
- Doc canal LinkedIn: [`../plans/linkedin-publication-pipeline.md`](../plans/linkedin-publication-pipeline.md).
- SKILL writer: `openclaw/workspace-agent-overrides/rick-linkedin-writer/SKILL.md`.
- Gap analysis cobertura canales: `docs/audits/2026-05-08-pipeline-editorial-gap-analysis.md` (si existe).
