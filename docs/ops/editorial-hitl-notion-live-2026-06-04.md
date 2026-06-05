# Editorial HITL — Verificación live Notion (2026-06-04)

- **Veredicto:** `EDITORIAL_HITL_NOTION_LIVE_OK`
- **Método:** Notion MCP `notion-fetch` (sin escritura, sin publicación)
- **DB:** [Publicaciones](https://app.notion.com/p/e6817ec4698a4f0fbbc8fedcf4e52472) · data source `collection://dc833f1f-07d9-49d0-82ec-fdfad1c808c4`
- **Fila ejemplo:** [CAND-002](https://app.notion.com/p/34b5f443fb5c81daabe1e586033ceed8)

## Gates en vivo (nombres exactos)

| Propiedad Notion | Tipo | Descripción live | CAND-002 ahora |
|------------------|------|------------------|----------------|
| `aprobado_contenido` | Checkbox | Gate humano — solo David | **false** (`__NO__`) |
| `autorizar_publicacion` | Checkbox | Gate humano — solo David | **false** (`__NO__`) |
| `gate_invalidado` | Checkbox | Invalida aprobación si hay cambios posteriores | false |
| `Estado` | Status | Pipeline editorial | **Borrador** |
| `visual_hitl_required` | Checkbox | Asset visual requiere revisión humana | **true** |
| `published_url` / `publication_url` | URL | Post-publicación | vacío |
| `publish_error` | Text | Último error de publicación | vacío |
| `content_hash` | Text | Idempotencia post-aprobación | vacío (correcto pre-gate) |

## Drift vs spec v1 (`docs/specs/sistema-editorial-rick-v1.md`)

| Spec v1 | Live Notion | Impacto |
|---------|-------------|---------|
| `Status` select inglés | `Estado` status en español con grupos Idea→Publicado | OK — más rico que spec |
| `Aprobado contenido` (espacio) | `aprobado_contenido` (snake) | OK — mismo rol |
| Copies en propiedades | `Copy LinkedIn`, `Copy X`, `Copy Blog` | OK — alineado §5.2 |
| — | Vista **Pipeline editorial** (board) muestra ambos checkboxes en tarjeta | UX David: ver gates en kanban |
| — | Vista **Pendiente de aprobación** filtra `aprobado_contenido=false` | Cola revisión contenido |

## Qué ve David en Notion (flujo práctico)

1. Abrir DB **Publicaciones** → vista **Pipeline editorial** o **Pendiente de aprobación**.
2. Abrir **CAND-002** — callout en página: *No publicar. Gates desmarcados.*
3. Revisar `Copy LinkedIn` / checklist en cuerpo de página.
4. Para aprobar contenido (sin publicar aún): marcar **`aprobado_contenido`** → mover `Estado` a **Aprobado** (opcional, coherente con schema).
5. Para autorizar salida futura: marcar **`autorizar_publicacion`** solo después del gate 1 (regla en descripción de propiedad).
6. Publicación real: requiere además instrucción explícita en chat (`ok, publica`) — Rick no debe publicar solo con checkboxes.

## Evidencia CAND-002 (lectura 2026-06-04)

- `publication_id`: CAND-002
- `Canal`: linkedin · `Tipo de contenido`: linkedin_post
- Copy LinkedIn y X poblados; `visual_hitl_required`: sí (asset pendiente)
- Cuerpo incluye sección **No hacer todavía** con 🛑 no marcar gates

## Vistas recomendadas para HITL

| Vista | Uso |
|-------|-----|
| Pendiente de aprobación | Cola gate 1 |
| Pipeline editorial | Estado + checkboxes por tarjeta |
| Pendiente de assets visuales | CAND-002 aparece (visual_hitl_required, sin URL) |
| Gates invalidados | Tras comentarios que invaliden aprobación |

## Próximo paso editorial (sin publicar)

David revisa CAND-002 en Notion. Si aprueba contenido: solo `aprobado_contenido=true` — **no** `autorizar_publicacion` hasta decidir canal y momento.

Wave 2 implementación: `docs/ops/editorial-wave2-plan-2026-06-04.md`.
