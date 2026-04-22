# Notion Publicaciones — IDs & Location Registry

> **ADVERTENCIA**: No pegar `NOTION_API_KEY`, tokens, credenciales, ni secretos en este archivo. Este archivo es solo para IDs de recursos Notion (pages y databases), que no son secretos.

---

## Hub principal — Sistema Editorial Rick

| Recurso | ID | URL | Notas |
|---------|----|-----|-------|
| Sistemas y Automatizaciones (parent) | `d9f44c45f20848d1a7eb330a9884afb3` | | Página raíz del workspace |
| **Sistema Editorial Rick** (hub) | `5894ba351e2749729077ca971fd9f52a` | [link](https://www.notion.so/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a) | Hub operativo/documental principal |
| Sistema Editorial Rick (OpenClaw) | `31e5f443fb5c8180bec7cbcda641b3b7` | [link](https://www.notion.so/Sistema-Editorial-Rick-31e5f443fb5c8180bec7cbcda641b3b7) | Registro/proyecto técnico bajo OpenClaw |

## Ubicación en Notion

```
Sistemas y Automatizaciones
├── Sistema Editorial Rick          ← hub principal (5894ba35...)
│   ├── DB Publicaciones            ← creada 2026-04-22 (e6817ec4...)
│   ├── (futuro) Perfil editorial David
│   └── (futuro) Flujo editorial Rick
└── OpenClaw
    └── Proyectos técnicos - Rick
        └── Sistema Editorial Rick  ← proyecto técnico (31e5f443...)
```

## Decisión de gobernanza

- El hub operativo/documental principal vive como hija directa de "Sistemas y Automatizaciones".
- La página bajo OpenClaw se conserva como registro/proyecto técnico relacionado.
- No se mueve ni borra la página de OpenClaw.

## Bases de datos

| Recurso | ID | URL | Estado | Notas |
|---------|----|-----|--------|-------|
| DB `Publicaciones` | `e6817ec4698a4f0fbbc8fedcf4e52472` | [link](https://www.notion.so/e6817ec4698a4f0fbbc8fedcf4e52472) | Creada — auditoría WARN (0 blockers, 2 warnings, 20 info) | Nombre visible: `📰 Publicaciones`, data source: `Publicaciones`. 44 propiedades en Notion (26 del schema + 18 extras). Última auditoría: 2026-04-22. |
| DB `Referentes` | _(completar o N/A)_ | | | |
| DB/página `Fuentes confiables` | _(completar o N/A)_ | | | |

## Páginas internas

| Recurso | ID | Estado |
|---------|----|--------|
| Perfil editorial David | _(pendiente)_ | No creada |
| Flujo editorial Rick | _(pendiente)_ | No creada |

## Último resultado del auditor

**Fecha**: 2026-04-22 (segunda ejecución, post-correcciones)
**Verdict**: WARN (0 blockers, 2 warnings, 20 info)
**Integration**: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM"
**Mejora**: de 12 warnings → 2 warnings (10 propiedades faltantes corregidas, Estado corregido)

Resultado completo en [`docs/ops/notion-publicaciones-last-audit.md`](notion-publicaciones-last-audit.md).

### Resumen de divergencias

**Warnings restantes (2)**:
1. `Proyecto`: type mismatch — schema define `relation`, Notion tiene `rich_text` (fallback intencional porque hay varias DBs candidatas)
2. `Tipo de contenido`: faltan 7 opciones del schema (`cta_variant`, `news_reactive`, `raw_idea`, `reference_post`, `source_signal`, `technical_explainer`, `thought_leadership`). Notion tiene opciones diferentes: `blog_post`, `carousel`, `linkedin_post`, `newsletter`, `thread`, `visual_asset`, `x_post`

**Propiedades extra en Notion (18 info)**: Ángulo editorial, canal_publicado, Claim principal, Comentarios revisión, Copy Blog/LinkedIn/Newsletter/X, Creado por sistema, error_kind, Prioridad, publish_error, published_at, published_url, Repo reference, Responsable revisión, Resumen fuente, Última revisión humana

**Extra options (2 info)**:
- `Etapa audiencia`: extra option `retention`
- `Tipo de contenido`: 7 extra options (ver arriba)

**Siguiente paso**: decidir si actualizar schema local para reflejar opciones reales de `Tipo de contenido`, o corregir Notion. `Proyecto` como `rich_text` es aceptable como fallback v1.

## Diferencias conocidas

- Notion tiene 44 propiedades; el schema local define 26. Las 18 extras son intencionales (agregadas por Notion AI).
- Nombre visible incluye icono `📰` pero el data source interno es `Publicaciones` (coincide con schema).
- Vista "Pendiente de aprobación" usa filtro AND avanzado por limitación de Notion.
- `Proyecto` es `rich_text` en Notion (fallback v1) vs `relation` en schema.
- Opciones de `Tipo de contenido` difieren entre schema y Notion (schema usa snake_case técnico, Notion usa nombres en español/descriptivos).

## Notas

- Hub creado 2026-04-22.
- DB Publicaciones creada 2026-04-22 por Notion AI (manual, inline en hub).
- Auditoría read-only #1 (2026-04-22): WARN (0 blockers, 12 warnings, 21 info).
- Auditoría read-only #2 (2026-04-22, post-correcciones): WARN (0 blockers, 2 warnings, 20 info).
- Integration: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM".
- Rick no participa todavía.
