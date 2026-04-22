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
| DB `Publicaciones` | `e6817ec4698a4f0fbbc8fedcf4e52472` | [link](https://www.notion.so/e6817ec4698a4f0fbbc8fedcf4e52472) | Creada — auditoría WARN (0 blockers, 12 warnings, 21 info) | Nombre visible: `📰 Publicaciones`, data source: `Publicaciones`. 34 propiedades en Notion (26 en schema + 18 extras - 10 faltantes). Última auditoría: 2026-04-22. |
| DB `Referentes` | _(completar o N/A)_ | | | |
| DB/página `Fuentes confiables` | _(completar o N/A)_ | | | |

## Páginas internas

| Recurso | ID | Estado |
|---------|----|--------|
| Perfil editorial David | _(pendiente)_ | No creada |
| Flujo editorial Rick | _(pendiente)_ | No creada |

## Último resultado del auditor

**Fecha**: 2026-04-22
**Verdict**: WARN (0 blockers, 12 warnings, 21 info)
**Integration**: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM"

Resultado completo en [`docs/ops/notion-publicaciones-last-audit.md`](notion-publicaciones-last-audit.md).

### Resumen de divergencias

**Propiedades faltantes en Notion (10 warnings)**:
- `Creado por` (created_by), `Fecha publicación` (date), `Fuentes confiables` (relation), `Notas` (rich_text), `platform_post_id` (rich_text), `Proyecto` (relation), `Publicación padre` (relation), `publication_url` (url), `trace_id` (rich_text), `Última edición` (last_edited_time)

**Propiedades extra en Notion (18 info)**: Ángulo editorial, canal_publicado, Claim principal, Comentarios revisión, Copy Blog/LinkedIn/Newsletter/X, Creado por sistema, error_kind, Prioridad, publish_error, published_at, published_url, Repo reference, Responsable revisión, Resumen fuente, Última revisión humana

**Opciones faltantes**:
- `Estado`: falta `Revisión pendiente` (existe `Revisión` en su lugar) — WARNING
- `Tipo de contenido`: faltan 7 opciones del schema, Notion tiene 7 diferentes — WARNING

**Siguiente paso**: corregir divergencias en Notion (agregar propiedades faltantes, renombrar `Revisión` → `Revisión pendiente`, ajustar opciones de `Tipo de contenido`). Luego re-ejecutar auditoría.

## Diferencias conocidas

- Notion AI creó 34 propiedades; el schema local define 26. La auditoría encontró 18 extras y 10 faltantes.
- Nombre visible incluye icono `📰` pero el data source interno es `Publicaciones` (coincide con schema).
- Vista "Pendiente de aprobación" usa filtro AND avanzado por limitación de Notion.
- Estado `Revisión pendiente` aparece como `Revisión` en Notion.
- Opciones de `Tipo de contenido` son completamente diferentes entre schema y Notion.

## Notas

- Hub creado 2026-04-22.
- DB Publicaciones creada 2026-04-22 por Notion AI (manual, inline en hub).
- Auditoría read-only ejecutada 2026-04-22: WARN (0 blockers, 12 warnings, 21 info).
- Integration: bot "Rick" (`3145f443-fb5c-814d-bbd1-0027093cebce`), workspace "Umbral BIM".
- Rick no participa todavía.
