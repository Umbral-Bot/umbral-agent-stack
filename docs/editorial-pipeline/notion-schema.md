# Notion Schema — Editorial Pipeline (STUB)

> **status:** STUB — pendiente Hilo 4
> **handoff:** este archivo es un placeholder creado por Hilo 1 (`wave1-h1-master-plan-drift-audit`). Hilo 4 debe completarlo con el audit real del schema de las superficies Notion del pipeline editorial.
> **scope esperado:** documentar el schema canónico de las superficies Notion en uso, sin crear DBs ni páginas nuevas.

## Índice esperado

1. **Hub principal `Sistema Editorial Rick`** (`5894ba351e2749729077ca971fd9f52a`)
   - Estructura, navegación, owners.
2. **Página técnica OpenClaw `Sistema Editorial Rick`** (`31e5f443fb5c8180bec7cbcda641b3b7`)
   - Rol vs hub, qué vive donde.
3. **DB `📰 Publicaciones`** (`e6817ec4698a4f0fbbc8fedcf4e52472`)
   - 45 propiedades reales = 26 canon + 19 extras (audit 2026-04-22).
   - Para cada propiedad: `nombre`, `tipo Notion`, `owner stage`, `escritor autorizado`, `semántica`, `valores válidos`.
   - Estados (`Estado`): `Borrador`, `Revisión pendiente`, `Aprobado` (¿existe? ver D3 master-plan §7), `Publicado`, etc.
4. **DB `👤 Referentes`** (data source `afc8d960-086c-4878-b562-7511dd02ff76`)
   - 10 columnas de canales agregadas 2026-05-05 (LinkedIn activity feed, YouTube channel, Web/Newsletter, RSS, Otros canales, Última actividad, Confianza canales, Flags canales, Notas canales, Última auditoría canales).
   - Cobertura actual: 14/26 referentes (53.8%).
   - Reglas de uso por stage (S2 lee canales explícitos; no inferir desde slug).
5. **Subpage `📊 Pipeline Editorial — Métricas`** (escrita por `stageX_pipeline_dashboard.py`)
   - Estructura del markdown / blocks generados.
6. **Permisos por integración**
   - Qué token escribe en qué superficie. Cruzar con audit `2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md`.

## TODO Hilo 4

- [ ] Auditar schema real vía Notion API + comparar con `docs/ops/notion-publicaciones-setup-runbook.md`.
- [ ] Documentar las 19 propiedades extras (no canónicas) y decidir si se prunan.
- [ ] Mapear qué stage escribe qué propiedad (matriz stage × propiedad).
- [ ] Resolver ambigüedades de naming (`copy_*` columns vs `Copy LinkedIn` rich_text).
- [ ] Verificar permisos integración Rick vs Copilot-VPS por superficie.
- [ ] Producir tabla de equivalencia "Estado en Notion" vs "estado en SQLite".

## Restricciones (Ola 1)

- NO crear DBs ni páginas Notion nuevas.
- NO modificar schema en producción.
- NO duplicar `📰 Publicaciones`.
- Solo lectura + documentación.

## Referencias

- Master plan: [`./master-plan.md`](./master-plan.md).
- Drift audit: [`../audits/2026-05-08-editorial-drift-audit.md`](../audits/2026-05-08-editorial-drift-audit.md).
- Runbooks Notion: `docs/ops/notion-publicaciones-*.md`.
- Audit Notion MCP: `docs/audits/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md` (si existe).
