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
| DB `Publicaciones` | `e6817ec4698a4f0fbbc8fedcf4e52472` | [link](https://www.notion.so/e6817ec4698a4f0fbbc8fedcf4e52472) | Creada — auditoría **PASS** (0 blockers, 0 warnings, 19 info) | Nombre visible: `📰 Publicaciones`, data source: `Publicaciones`. 45 propiedades en Notion (26 del schema + 19 extras). Última auditoría: 2026-04-22. |
| DB `Referentes` | _(completar o N/A)_ | | | |
| DB/página `Fuentes confiables` | _(completar o N/A)_ | | | |

## Páginas internas

| Recurso | ID | Estado |
|---------|----|--------|
| Perfil editorial David | _(pendiente)_ | No creada |
| Flujo editorial Rick | _(pendiente)_ | No creada |

## Último resultado del auditor

**Fecha**: 2026-04-22 (tercera ejecución, post-alineación schema v1)
**Verdict**: **PASS** (0 blockers, 0 warnings, 19 info)
**Integration**: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM"

Resultado completo en [`docs/ops/notion-publicaciones-last-audit.md`](notion-publicaciones-last-audit.md).

### Decisiones v1 aplicadas al schema

1. **`Proyecto`**: cambiado de `relation` a `rich_text` en schema local. No hay DB canónica de proyectos clara; se mantiene como texto hasta decidir. Relación diferida a v1.1/v2.
2. **`Tipo de contenido`**: opciones del schema alineadas con las reales de Notion v1: `blog_post`, `linkedin_post`, `x_post`, `newsletter`, `carousel`, `visual_asset`, `thread`.

### Info restantes (19)

18 propiedades extra en Notion (no bloqueantes): Ángulo editorial, canal_publicado, Claim principal, Comentarios revisión, Copy Blog/LinkedIn/Newsletter/X, Creado por sistema, error_kind, Prioridad, publish_error, published_at, published_url, Repo reference, Responsable revisión, Resumen fuente, Última revisión humana.
1 extra option: `Etapa audiencia` tiene `retention` en Notion (no en schema).

**Siguiente paso**: crear primer registro manual de prueba en Notion, sin Rick.

## Diferencias conocidas

- Notion tiene 45 propiedades; el schema local define 26. Las 19 extras son intencionales (agregadas por Notion AI).
- Nombre visible incluye icono `📰` pero el data source interno es `Publicaciones` (coincide con schema).
- Vista "Pendiente de aprobación" usa filtro AND avanzado por limitación de Notion.
- `Proyecto` es `rich_text` tanto en schema como en Notion (decisión v1; relación diferida a v1.1/v2).
- `Tipo de contenido` alineado: schema y Notion usan las mismas 7 opciones v1.
- `Etapa audiencia` tiene opción extra `retention` en Notion (INFO, no bloqueante).

## Notas

- Hub creado 2026-04-22.
- DB Publicaciones creada 2026-04-22 por Notion AI (manual, inline en hub).
- Auditoría read-only #1 (2026-04-22): WARN (0 blockers, 12 warnings, 21 info).
- Auditoría read-only #2 (2026-04-22, post-correcciones Notion): WARN (0 blockers, 2 warnings, 20 info).
- Auditoría read-only #3 (2026-04-22, post-alineación schema v1): **PASS** (0 blockers, 0 warnings, 19 info).
- Integration: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM".
- Rick no participa todavía.
