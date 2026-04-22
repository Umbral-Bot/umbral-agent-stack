# Setup Runbook — Notion Publicaciones

**Status**: pre-automation (manual/semi-manual)
**Schema**: `notion/schemas/publicaciones.schema.yaml`
**Provisioner**: `scripts/plan_notion_publicaciones.py`
**Auditor**: `scripts/audit_notion_publicaciones.py`
**Checklist CLI**: `scripts/notion_publicaciones_setup_checklist.py` (PR #260)

---

## Ubicación Notion confirmada

El hub principal ya fue creado en Notion:

| Recurso | URL |
|---------|-----|
| **Hub principal** | [Sistema Editorial Rick](https://www.notion.so/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a) |
| Página técnica (OpenClaw) | [Sistema Editorial Rick](https://www.notion.so/Sistema-Editorial-Rick-31e5f443fb5c8180bec7cbcda641b3b7) |

**Ubicación exacta**:
- Hub principal: `Sistemas y Automatizaciones → Sistema Editorial Rick`
- Página técnica: `Sistemas y Automatizaciones → OpenClaw → Proyectos técnicos - Rick → Sistema Editorial Rick`

**Decisión de gobernanza**:
- El hub operativo/documental principal vive como hija directa de "Sistemas y Automatizaciones".
- La página bajo OpenClaw se conserva como registro/proyecto técnico relacionado. No se mueve ni se borra.

**Estado actual**:
- Hub principal: creado.
- DB `Publicaciones`: **creada** (2026-04-22, inline por Notion AI).
  - ID: `e6817ec4698a4f0fbbc8fedcf4e52472`
  - URL: [link](https://www.notion.so/e6817ec4698a4f0fbbc8fedcf4e52472)
  - Nombre visible: `📰 Publicaciones` (data source interno: `Publicaciones`)
  - 34 propiedades creadas, 7 vistas creadas
  - No se crearon automatizaciones ni registros de ejemplo
- Siguiente paso: ejecutar auditoría read-only para verificar alineación con schema local y corregir divergencias si aparecen.

**Limitaciones reportadas por Notion AI**:
- Vista "Pendiente de aprobación" usa filtro avanzado AND (limitación de Notion, no soporta filtro simple con múltiples condiciones).
- Notion AI agregó sección "Diferencias pendientes de auditoría" encima de la DB en la página.

---

## Objetivo

Guiar la creación manual y controlada de la DB Notion `Publicaciones` dentro del hub ya existente, usando el schema aprobado y las herramientas offline ya mergeadas. **Rick no participa todavía.**

## Qué se crea manualmente

1. **DB `Publicaciones`** — dentro de `Sistema Editorial Rick`, usando las 26 propiedades del schema aprobado.
2. **Página `Perfil editorial David`** — dentro del hub.
3. **Página `Flujo editorial Rick`** — dentro del hub.
4. **Referencia/relación** a DB `Referentes` (si existe).
5. **Referencia/relación** a DB/página `Fuentes confiables` (si existe).

## Qué NO se crea

- No se crea DB `Variantes` (decisión v1).
- No se crea DB `Assets Visuales Rick` (decisión v1).
- No se crea DB `PublicationLog` (decisión v1).
- No se activa Rick ni ninguna automatización.
- No se conecta a Ghost, LinkedIn, X, ni ninguna plataforma.
- No se crean webhooks, cron jobs, ni workers.

## Prerrequisitos

- [x] Schema local aprobado: `notion/schemas/publicaciones.schema.yaml`
- [x] Hub principal creado en Notion: `Sistema Editorial Rick`
- [x] DB `Publicaciones` creada inline en el hub (2026-04-22)
- [x] Ejecutar auditoría read-only contra DB real — **PASS** (0 blockers, 0 warnings, 19 info) post-alineación schema v1
- [x] Corregir divergencias principales (10 propiedades faltantes agregadas, Estado corregido)
- [x] Alinear schema v1: `Proyecto` como rich_text, `Tipo de contenido` con opciones reales de Notion
- [ ] Crear primer registro manual de prueba en Notion, sin Rick
- [ ] Confirmar si existe DB `Referentes` en el workspace
- [ ] Confirmar si existe DB/página `Fuentes confiables` en el workspace

## Checklist de creación — DB `Publicaciones`

### Paso 1: Generar plan

```bash
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --markdown
```

### Paso 2: Crear DB `Publicaciones`

- [x] Crear base de datos inline dentro de `Sistema Editorial Rick`
- [x] Nombrar: `Publicaciones`
- [x] Agregar las 26 propiedades según el plan generado
- Nota: Notion AI creó 34 propiedades (8 extras pendientes de auditoría)

### Paso 3: Propiedades críticas

| Propiedad | Tipo | Crítica |
|-----------|------|---------|
| `Título` | title | si |
| `Canal` | select (blog, linkedin, x, newsletter) | si |
| `Estado` | status (8 estados, 3 grupos) | si |
| `aprobado_contenido` | checkbox | si |
| `autorizar_publicacion` | checkbox | si |
| `gate_invalidado` | checkbox | si |
| `content_hash` | rich_text | si |
| `idempotency_key` | rich_text | si |

### Paso 4: Canales

- [ ] `blog` (blue)
- [ ] `linkedin` (green)
- [ ] `x` (gray)
- [ ] `newsletter` (purple) — preparado, no prioritario v1

### Paso 5: Estados (8 en 3 grupos)

**No iniciado**: Idea
**En progreso**: Borrador, Revisión pendiente, Aprobado, Autorizado, Publicando
**Completado**: Publicado, Descartado

### Paso 6: Vistas recomendadas

- [ ] **Pipeline editorial** — board, group by Estado
- [ ] **Por canal** — table, group by Canal
- [ ] **Pendientes de aprobación** — table, filter Estado == Revisión pendiente
- [ ] **Gates invalidados** — table, filter gate_invalidado == true
- [ ] **Publicados** — table, filter Estado == Publicado

### Paso 7: Post-creación

- [x] Copiar database ID de `Publicaciones` → `e6817ec4698a4f0fbbc8fedcf4e52472`
- [x] Registrar en `docs/ops/notion-publicaciones-ids-template.md`
- [ ] Correr auditor read-only (solo cuando David lo autorice):

```bash
export NOTION_API_KEY="ntn_..."
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id e6817ec4698a4f0fbbc8fedcf4e52472 --validate-schema --fail-on-blocker
```

- [ ] Verificar 0 blockers
- [ ] **No activar Rick todavía**

## Rick todavía no participa

Rick solo participará después de:
1. DB `Publicaciones` creada y auditada con 0 blockers.
2. David aprueba explícitamente que Rick puede empezar a escribir drafts.
3. Se implementa la integración código → Notion con gates humanos activos.

## Orden recomendado de operaciones

1. **Setup runbook** (este documento)
2. **Dry-run provisioner**: `scripts/plan_notion_publicaciones.py --validate --markdown`
3. ~~**Creación manual controlada** siguiendo esta checklist~~ **Completado 2026-04-22**
4. **Read-only audit**: `scripts/audit_notion_publicaciones.py --database-id e6817ec4698a4f0fbbc8fedcf4e52472 --fail-on-blocker`
5. **Corregir divergencias** si la auditoría reporta blockers o warnings
6. Solo después: Rick puede escribir drafts (requiere aprobación explícita de David)

## Errores comunes

| Error | Solución |
|-------|----------|
| Propiedad con tipo incorrecto | Corregir tipo en Notion, re-correr auditor |
| Falta propiedad crítica | Agregar propiedad, re-correr auditor |
| Auditor reporta blocker | Corregir DB según plan, no modificar schema |
| Token no funciona | Compartir página con la integration en Notion |

## Rollback manual

1. Mover a papelera la DB/página en Notion.
2. Vaciar papelera si se desea eliminación permanente.
3. Limpiar IDs en `docs/ops/notion-publicaciones-ids-template.md`.
4. Re-ejecutar desde paso 2.
