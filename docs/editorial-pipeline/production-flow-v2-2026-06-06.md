# Flujo de Producción Editorial — v2 (confirmado por David, 2026-06-06)

> **Estado:** CANÓNICO — fuente de verdad de la experiencia de producción.
> **Reemplaza/actualiza:** la secuencia de gates de `docs/specs/sistema-editorial-rick-v1.md` §6, los gates de `docs/editorial-pipeline/master-plan.md` §2, el proveedor visual de `docs/adr/ADR-006-capa-visual-editorial.md`, y el alcance de canales de `docs/adr/ADR-008-orquestacion-editorial.md`.
> **Confirmado en sesión:** 2026-06-06 (respuestas estructuradas de David).
> **Owner experiencia:** David · **Implementación:** Rick (OpenClaw) + Agent Stack (Worker/Dispatcher) + n8n (bordes).
>
> **⚠️ Ajuste P0 (norte 2026-07-22):** este doc sigue canónico salvo el **§5
> "Automático vía API" para LinkedIn/X**, que queda **superseded → Fila I = B**
> (no autopublish RRSS; LinkedIn ToS §3.1.26 + `ADR-010` §Contexto). La regla de gates y
> "la edición en Notion es la verdad final" (§3.2) permanece vigente. Ver
> `docs/ops/editorial-norte-hitl-contract-2026-07-22.md` §5.I y §7.

---

## 1. Resumen de la experiencia

El producto lleva una idea desde **señales del sector** hasta **publicación multicanal**, de forma casi totalmente automática, con **solo dos decisiones humanas en Notion** más una **confirmación final por Telegram**.

David no pega prompts en ninguna herramienta. Su único panel de control de contenido es **Notion**. Telegram es solo el botón final de seguridad.

**Modelo editorial (v2.1):** redacción y voice pass vía OpenClaw `azure-openai-responses/gpt-5.5`. Contrato: `docs/editorial-pipeline/editorial-model-contract.md`. Sin fallback silencioso.

---

## 2. Flujo confirmado (end-to-end)

```
[AUTOMÁTICO]
  1. Descubrir señales (referentes + fuentes)
  2. Curar + rankear + dedup
  3. Redactar borrador (framing AEC + voz David)
  4. Benchmark + QA interno (anti-slop, atribución, gates en false)
  5. Escribir el TEXTO en Notion (Decision Brief + copy por canal)

[GATE 1 — humano, en Notion]
  6. David revisa el texto
  7. David puede EDITAR el texto directamente en Notion
  8. David marca la casilla "Texto aprobado"

[AUTOMÁTICO, disparado por Gate 1]
  9. Generar N variantes de imagen (Magnific*)
  10. Subir las imágenes a la página de Notion

[GATE 2 — humano, en Notion]
  11. David elige 1 imagen
  12. David marca la casilla "Autorizar publicación"

[CONFIRMACIÓN FINAL — Telegram]
  13. Rick avisa: "voy a publicar <título> + <imagen> en <canales>, ¿confirmás?"
  14. David responde "ok publica"

[AUTOMÁTICO]
  15. El sistema toma la versión EDITADA en Notion + la imagen elegida (verdad final)
  16. Publica en: LinkedIn (empresa, API), Blog (Ghost), X (API), Newsletter
  17. Devuelve URL, post ID, estado y hash anti-duplicado a Notion
```

\* Sub-flujo de imagen pendiente de cerrar según capacidad real de Magnific (ver §6).

---

## 3. Reglas duras (lo que define el producto)

1. **Dos gates humanos, en Notion, separados:**
   - **Gate 1 = "Texto aprobado"** → dispara la generación de imágenes.
   - **Gate 2 = "Autorizar publicación"** → habilita la confirmación final.
2. **La versión editada por David en Notion es la verdad final.** Si David edita el texto, se publica **exactamente eso, sin re-validación automática**. Editar NO revierte la aprobación (cambia la regla previa de "editar invalida el gate").
3. **Las imágenes aparecen recién después del Gate 1** (no antes), generadas con Magnific y subidas a Notion para que David elija una.
4. **La publicación nunca ocurre sin la confirmación final por Telegram** ("ok publica"), aun con ambos gates marcados.
5. **Idempotencia:** un mismo copy no se publica dos veces (`publication_content_hash`).
6. **Honestidad runtime:** el sistema no afirma haber publicado hasta tener el post ID/URL de cada canal.

---

## 4. Gates y propiedades Notion (cambios respecto a v1)

| Propiedad Notion | v1 | v2 (confirmado) |
|------------------|----|-----------------|
| `Texto aprobado` (checkbox) | — (era `aprobado_contenido`, con regla de invalidación al editar) | **Gate 1.** Solo David. Dispara generación de imágenes. Editar el texto NO lo revierte. |
| `Selección imagen` (select) | — | **Nuevo.** David elige `Pendiente` → `Alt 1`…`Alt 5` / `Regenerar` / `Sin imagen`. Ver `docs/ops/notion-publicaciones-v2-visual-gates-schema.md`. |
| `Estado imagen` (select) | — | **Nuevo.** Máquina de estados Rick/Worker (`Listo para selección`, etc.). |
| `imagen_alt_*_url` (url ×5) | — | **Nuevo.** URLs por alternativa; verdad para publish (no el body). |
| `Autorizar publicación` (checkbox) | `autorizar_publicacion` | **Gate 2.** Solo David. Requiere Gate 1 + imagen elegida. Habilita confirmación Telegram. |
| `Imágenes candidatas` (files/embeds) | — | **Nuevo.** N imágenes generadas con Magnific. |
| Estado | draft → ready_for_review → content_approved → publish_authorized → published | draft → revisión texto → **texto aprobado** → imágenes → **autorizado** → confirmación Telegram → publicado |

> Rick **nunca** marca `Texto aprobado` ni `Autorizar publicación`. Solo David.

---

## 5. Canales en v1 producción

| Canal | Modo | Estado / Requisito |
|-------|------|--------------------|
| **LinkedIn (cuenta empresa)** | ~~Automático vía API~~ → **manual (Fila I = B)** | ⚠️ **Superseded → Fila I = B** (no autopublish; el post es humano — ver Nota P0 arriba + [contrato §5.I](../ops/editorial-norte-hitl-contract-2026-07-22.md)). Community Management / Marketing API, scope `w_organization_social`, David admin de la página, **access review de LinkedIn** pendiente (sólo revive con Fila I = A). Ver `ADR-009`. |
| **Blog (Ghost)** | Automático | Integración Ghost (JWT admin). Ya diseñado en spec v1 §8.1. |
| **X** | ~~Automático vía API~~ → **manual (Fila I = B)** | ⚠️ **Superseded → Fila I = B** (no autopublish; sin publisher X hoy — ver Nota P0 arriba + [contrato §5.I](../ops/editorial-norte-hitl-contract-2026-07-22.md)). API v2 de pago (David confirma que la paga). Adapter pendiente. |
| **Newsletter** | Automático | **Herramienta TBD** (Ghost members vs Substack vs otra). Bloqueante menor: definir plataforma. |

> La cuenta **personal** de LinkedIn queda **diferida** (se decide más adelante). v1 = empresa.

---

## 6. Pendientes abiertos (no bloquean el diseño, sí la implementación)

| # | Pendiente | Dueño | Notas |
|---|-----------|-------|-------|
| 1 | **Capacidad Magnific** | — | **Resuelto:** `images_generate` desde texto (MCP). Setup: `docs/ops/magnific-editorial-setup-2026-06-06.md`. |
| 2 | **OAuth Magnific** | David | MCP en Cursor + OpenClaw VPS; completar OAuth en browser (primera conexión). |
| 3 | **Plataforma de Newsletter** | David | TBD. Si el blog es Ghost, el camino simple es el mismo post enviado por email a members. |
| 4 | **LinkedIn access review** | David (admin) + Copilot | App en LinkedIn Developer, scopes de organización, aprobación. Ver `ADR-009`. |
| 5 | **X API** | — | **Resuelto (2026-06-06):** POST `/2/tweets` OK en VPS. Falta adapter Worker. |
| 6 | **Mecanismo de "elegir imagen" en Notion** | David + Notion AI | **Diseño listo:** `Selección imagen` + `imagen_alt_*_url`. Implementar con Prompt A en `docs/ops/notion-publicaciones-v2-visual-gates-schema.md`. Limpieza de columnas **después** del soak (Fase C). |

---

## 7. Qué cambia respecto a los docs previos

- **`ADR-006` (capa visual):** proveedor visual primario pasa de Vertex AI / Freepik / Nano Banana a **Magnific** (sujeto a §6.1). Se mantiene la regla API-first y anti-AI-slop.
- **`spec sistema-editorial-rick-v1` §3:** LinkedIn **Company Page** sale de "fuera de alcance v1" y pasa a **in-scope** (vía API, ver `ADR-009`).
- **`spec ... v1` §6:** gates redefinidos (Gate 1 texto dispara imágenes; Gate 2 publica); la regla "editar invalida la aprobación" se reemplaza por "**la edición en Notion es la verdad final**".
- **`master-plan.md` §2:** secuencia de gates actualizada + imagen entre Gate 1 y Gate 2 + confirmación Telegram como disparo final.
- **`ADR-008` (orquestación):** canales auto v1 = LinkedIn empresa, Blog, X, Newsletter. X deja de ser "manual v1".

---

## 8. Arquitectura de ejecución (sin cambios de capas)

- **Agent Stack (Dispatcher + Worker + Notion Poller + OpsLogger):** estado, trazabilidad, gates, idempotencia, escritura de borradores en Notion.
- **Rick (OpenClaw, Telegram):** orquestación editorial, QA entre subagentes, confirmación final con David.
- **n8n (VPS):** cron de descubrimiento, webhooks (Ghost, LinkedIn), Wait/HITL, scheduling, alertas de expiración de tokens.
- **Notion:** único panel humano de contenido; los dos gates viven acá.

Esta separación core/bordes/lab sigue la decisión de `ADR-008`.
