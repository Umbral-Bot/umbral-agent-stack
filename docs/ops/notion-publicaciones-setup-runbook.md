# Setup Runbook — Notion Publicaciones

**Status**: pre-automation (manual/semi-manual)
**Schema**: `notion/schemas/publicaciones.schema.yaml`
**Provisioner**: `scripts/plan_notion_publicaciones.py`
**Auditor**: `scripts/audit_notion_publicaciones.py`
**Checklist CLI**: `scripts/notion_publicaciones_setup_checklist.py`

---

## Objetivo

Guiar la creación manual y controlada de la estructura Notion para el sistema editorial Rick v1, usando el schema aprobado y las herramientas offline ya mergeadas. **Rick no participa todavía.**

## Qué se crea manualmente

1. **Página parent**: `Sistema Editorial Rick` (o nombre que David elija).
2. **Base de datos**: `Publicaciones` — usando las 26 propiedades del schema aprobado.
3. **Página**: `Perfil editorial David` — dentro de la página parent.
4. **Página**: `Flujo editorial Rick` — dentro de la página parent.
5. **Referencia/relación** a DB `Referentes` (si existe).
6. **Referencia/relación** a DB/página `Fuentes confiables` (si existe).

## Qué NO se crea

- No se crea DB `Variantes` (decisión v1).
- No se crea DB `Assets Visuales Rick` (decisión v1).
- No se crea DB `PublicationLog` (decisión v1).
- No se activa Rick ni ninguna automatización.
- No se conecta a Ghost, LinkedIn, X, ni ninguna plataforma.
- No se crean webhooks, cron jobs, ni workers.

## Prerrequisitos

- [ ] Schema local aprobado: `notion/schemas/publicaciones.schema.yaml`
- [ ] Decidir parent page en Notion (recomendado: `Sistema Editorial Automatizado Umbral`)
- [ ] Confirmar si existe DB `Referentes` en el workspace
- [ ] Confirmar si existe DB/página `Fuentes confiables` en el workspace
- [ ] Tener acceso de edición al workspace Notion
- [ ] Generar plan con provisioner: `scripts/plan_notion_publicaciones.py --validate`

## Estructura recomendada

```
Notion workspace
└── Sistema Editorial Rick (o nombre elegido)
    ├── Publicaciones (DB — 26 propiedades)
    ├── Perfil editorial David (página)
    ├── Flujo editorial Rick (página)
    └── Referencias
        ├── → Referentes (relación si existe)
        └── → Fuentes confiables (relación si existe)
```

## Checklist de creación — Base de datos `Publicaciones`

### Paso 1: Generar plan

```bash
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --markdown
```

Revisar el plan completo antes de crear la DB.

### Paso 2: Crear página parent

- [ ] Crear página `Sistema Editorial Rick` en el workspace
- [ ] Anotar el page ID en `docs/ops/notion-publicaciones-ids-template.md`

### Paso 3: Crear DB `Publicaciones`

- [ ] Crear base de datos inline dentro de la página parent
- [ ] Nombrar: `Publicaciones`
- [ ] Agregar las 26 propiedades según el plan generado

### Paso 4: Propiedades críticas

Verificar que estas propiedades existen con el tipo correcto:

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

### Paso 5: Canales

- [ ] `blog` (blue)
- [ ] `linkedin` (green)
- [ ] `x` (gray)
- [ ] `newsletter` (purple) — preparado, no prioritario v1

### Paso 6: Estados

Verificar los 8 estados en 3 grupos:

**No iniciado**:
- [ ] Idea (default)

**En progreso**:
- [ ] Borrador (blue)
- [ ] Revisión pendiente (yellow)
- [ ] Aprobado (green)
- [ ] Autorizado (green)
- [ ] Publicando (orange)

**Completado**:
- [ ] Publicado (green)
- [ ] Descartado (red)

### Paso 7: Gates humanos

- [ ] `aprobado_contenido` = checkbox, default false
- [ ] `autorizar_publicacion` = checkbox, default false
- [ ] `gate_invalidado` = checkbox, default false

### Paso 8: Vistas recomendadas

- [ ] **Pipeline editorial** — board, group by Estado
- [ ] **Por canal** — table, group by Canal
- [ ] **Pendientes de aprobación** — table, filter Estado == Revisión pendiente
- [ ] **Gates invalidados** — table, filter gate_invalidado == true
- [ ] **Publicados** — table, filter Estado == Publicado

### Paso 9: Relaciones

- [ ] `Publicación padre` → self-relation a Publicaciones
- [ ] `Fuentes confiables` → relación a DB Fuentes confiables (si existe)
- [ ] `Proyecto` → relación a DB Proyectos (si existe)

### Paso 10: Post-creación

- [ ] Copiar database ID de `Publicaciones`
- [ ] Registrar en `docs/ops/notion-publicaciones-ids-template.md`
- [ ] Correr auditor read-only (solo cuando David lo autorice):

```bash
export NOTION_API_KEY="ntn_..."
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id <publicaciones-db-id> --validate-schema --fail-on-blocker
```

- [ ] Verificar que el auditor reporta 0 blockers
- [ ] **No activar Rick todavía**

## Rick todavía no participa

En esta fase:
- Rick **no** crea páginas ni DBs.
- Rick **no** escribe drafts.
- Rick **no** publica.
- Rick **no** interactúa con `Publicaciones`.

Rick solo participará después de:
1. DB `Publicaciones` creada y auditada con 0 blockers.
2. David aprueba explícitamente que Rick puede empezar a escribir drafts.
3. Se implementa la integración código → Notion con gates humanos activos.

## Definition of Done

- [ ] Página parent creada con nombre aprobado.
- [ ] DB `Publicaciones` creada con 26 propiedades.
- [ ] Auditor read-only ejecutado con 0 blockers.
- [ ] IDs registrados en template.
- [ ] Vistas recomendadas creadas.
- [ ] Relations configuradas (donde aplique).
- [ ] David confirma estructura correcta.
- [ ] Rick NO activado.

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Propiedad con tipo incorrecto | Selección manual equivocada | Corregir tipo en Notion, re-correr auditor |
| Falta propiedad crítica | Olvidada durante creación manual | Agregar propiedad, re-correr auditor |
| Estado/opción faltante | No se agregaron todas las opciones | Agregar opciones, re-correr auditor |
| Auditor reporta blocker | Discrepancia entre schema y DB real | Corregir DB según plan, no modificar schema |
| DB creada en parent incorrecto | Parent page equivocada | Mover DB a parent correcto en Notion |
| Token no funciona | Integration no tiene acceso a la página | Compartir página con la integration en Notion |

## Rollback manual

Si la DB o página fue creada incorrectamente:

1. **Mover a papelera** la DB/página en Notion.
2. **Vaciar papelera** si se desea eliminación permanente.
3. **Limpiar IDs** en `docs/ops/notion-publicaciones-ids-template.md`.
4. **Re-ejecutar** el proceso desde el paso 2.

Este rollback es completamente manual. No hay automatización de rollback.

## Orden recomendado de operaciones

1. **Setup runbook/checklist** (este documento)
2. **Dry-run provisioner**: `scripts/plan_notion_publicaciones.py --validate --markdown`
3. **Creación manual controlada** siguiendo esta checklist
4. **Read-only audit**: `scripts/audit_notion_publicaciones.py --database-id <id> --fail-on-blocker`
5. Solo después: Rick puede escribir drafts (requiere aprobación explícita de David)
