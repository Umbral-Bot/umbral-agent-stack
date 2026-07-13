# Editorial — Contrato del hito humano "Publicaciones" (revisión humana)

> **Status:** DRAFT — design-only. Este documento NO activa agentes runtime, NO edita Notion,
> NO publica, NO pausa el writer, NO reinicia el gateway y NO cambia gates humanos.
> Define el contrato del punto de revisión humana del flujo editorial Sistema 2 (LinkedIn, HITL).
>
> **Goal:** M2-WIN-01 · **Veredicto objetivo:** `M2_WIN01_SPEC_DRAFT_READY`
> **Owner del gate:** David (humano) · **Superficie:** repo / Coordinador
> **Fecha:** 2026-06-01

---

## 0. Propósito

Especificar, como contrato estable y verificable, qué es el hito humano **"Publicaciones"**:
el punto donde una pieza editorial generada por la cadena de agentes queda **detenida en
estado de revisión** hasta que David la apruebe y autorice explícitamente. Este contrato
fija los campos mínimos, los estados, los gates de David y la relación con el skill
`linkedin-david`, sin implementar n8n, Notion writes ni runtime.

Out of scope (explícito): implementación n8n, Notion write, reactivación del writer,
fix del `FailoverError`, cambios en `openclaw.json`, scheduling automático.

---

## 1. Evidencia vs inferencia (separación obligatoria)

### 1.1 Evidencia (verificada en repo)

| # | Hecho | Fuente en repo |
|---|---|---|
| E1 | La DB canónica del hito es `Publicaciones` (Notion id `e6817ec4698a4f0fbbc8fedcf4e52472`, nombre visible `📰 Publicaciones`). Auditoría PASS 2026-04-22. | `docs/ops/notion-publicaciones-ids-template.md` |
| E2 | El schema v1 define `Status` con la secuencia `draft → ready_for_review → content_approved → publish_authorized → scheduled → published → archived`. | `docs/specs/sistema-editorial-rick-v1.md` §5.1 |
| E3 | Existen dos gates humanos vía checkbox: `Aprobado contenido` y `Autorizar publicación`. **Solo David marca `true`; Rick nunca los toca.** | spec v1 §5.1 y §6 |
| E4 | Regla de invalidación: si David comenta tras aprobar, `Aprobado contenido` y `Autorizar publicación` vuelven a `false` y Status regresa a `ready_for_review`. | spec v1 §6 "Reglas de gate" |
| E5 | El flujo editorial (`editorial-agent-flow.md`) coloca la revisión y aprobación de David en los pasos 8–10, después del registro del borrador en Notion por un operador (paso 7). | `docs/ops/editorial-agent-flow.md` |
| E6 | El skill `linkedin-david` se usa **después de la selección/aprobación humana** para afinar POV, tono, audience-fit y CTA de David. No publica ni asume automatización. | `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`; `openclaw/workspace-templates/skills/linkedin-david/SKILL.md` |
| E7 | Estado runtime declarado: `EDITORIAL_02_DIAG_READY`. El writer `rick-linkedin-writer` falla con `FailoverError` (Azure Responses, `store=false`, `rs_*` not found, cross-agent). | `.agents/tasks/2026-06-01-001-...editorial-02-diag...md`; `.agents/tasks/2026-06-01-004-editorial-03-...md` |

### 1.2 Inferencia (diseño propuesto, NO verificado en runtime)

| # | Inferencia | Base |
|---|---|---|
| I1 | El writer dispara "@ HH:09 vía gateway interno" — tomado del contexto del goal. **No verificado en VPS** en esta sesión (aplica VPS Reality Check Rule). | enunciado del goal M2-WIN-01 |
| I2 | El `FailoverError` (Azure `store=false` cross-agent) **no afecta el contrato del gate humano**: el hito "Publicaciones" es un estado de datos en Notion, no depende de que el writer esté sano. La pieza puede quedar en `ready_for_review` aunque el writer falle. | inferencia de diseño sobre E2–E5 |
| I3 | El subconjunto "mínimo" de campos (sección 3) es suficiente para operar el gate humano aunque el schema completo tenga 45 propiedades en Notion. | inferencia sobre spec v1 §5.1 |
| I4 | `linkedin-david` actúa **antes** de `ready_for_review` (calibración de voz en el draft) y **nunca** después de un gate de David; si David comenta, su intervención reabre el draft (E4) y recién entonces puede re-invocarse. | inferencia sobre E4 + E6 |

---

## 2. Definición del hito

**"Publicaciones"** es el bus humano del flujo editorial: una fila en la DB `Publicaciones`
que representa una pieza candidata y su estado de revisión. El hito se considera **alcanzado**
cuando una pieza entra en `ready_for_review` con su metadata mínima completa, y se considera
**cerrado** cuando David la lleva a `publish_authorized` (o la archiva / reabre).

El hito es **agnóstico al runtime**: ni el `FailoverError` del writer ni una pausa del lane
cambian la semántica del gate. Si el writer está caído, simplemente no entran piezas nuevas a
`ready_for_review`; las existentes permanecen esperando decisión humana.

---

## 3. Campos mínimos del contrato

Subconjunto operativo mínimo (el schema completo vive en spec v1 §5.1). Un registro `Publicaciones`
solo puede entrar a `ready_for_review` si estos campos están presentes y válidos.

| Campo | Tipo Notion | Quién lo escribe | Regla mínima |
|---|---|---|---|
| `Title` | Title | Rick | ≤120 chars, no vacío |
| `Slug` | Rich text | Rick | kebab-case, único, <60 chars |
| `Status` | Status | Rick (hasta el gate) / David (en/desde gates) | uno de los 7 estados de §4 |
| `Canal primario` | Select | Rick | `linkedin` (Sistema 2) / `blog` / `x` |
| `Tipo pieza` | Select | Rick | valor del enum spec v1 §5.1 |
| `Content markdown` | Page body | Rick | contenido fuente no vacío |
| `Copy LinkedIn` | Rich text | Rick (calibrado con `linkedin-david`) | requerido si `Canal primario = linkedin` |
| `CTA type` / `CTA text` | Select / Rich text | Rick | si `CTA type ≠ none` → `CTA text` no vacío |
| `Aprobado contenido` | Checkbox | **David únicamente** | gate humano 1 |
| `Autorizar publicación` | Checkbox | **David únicamente** | gate humano 2; requiere `Aprobado contenido = true` |
| `Content approved at` | Date | auto | timestamp de gate 1 |
| `Publish authorized at` | Date | auto | timestamp de gate 2 |
| `Last publish error` | Rich text | auto/operador | registro del último error (p.ej. `FailoverError` redactado) |

> Campos auto/extendidos (hash, tracking, copies por canal X/blog, scheduling) se rigen por
> spec v1 §5.1–§5.3 y no se redefinen aquí.

---

## 4. Estados y transiciones

Hereda la máquina de estados de spec v1 §6 (no la modifica):

```
draft
  → ready_for_review      [Rick: metadata mínima completa, CTA válido]
  → content_approved      [GATE HUMANO 1 — David: Aprobado contenido = true]
  → publish_authorized    [GATE HUMANO 2 — David: Autorizar publicación = true]
  → scheduled / published  [Rick: solo si Autorizar publicación = true]
  → archived              [David: decisión manual de retiro]
```

**Regla de reapertura (E4):** un comentario de David posterior a `content_approved`
invalida ambos checkboxes (`Aprobado contenido = false`, `Autorizar publicación = false`)
y devuelve `Status` a `ready_for_review`.

---

## 5. Gate de aprobación de David

| Gate | Estado origen → destino | Señal humana | Invariante |
|---|---|---|---|
| Gate 1 — Aprobación de contenido | `ready_for_review → content_approved` | David marca `Aprobado contenido = true` | Rick **nunca** marca este checkbox |
| Gate 2 — Autorización de publicación | `content_approved → publish_authorized` | David marca `Autorizar publicación = true` | requiere Gate 1; ningún canal publica sin Gate 2 |

Invariantes duras (de spec v1 §6, recogidas como contrato):

- `Autorizar publicación = true` es imposible si `Aprobado contenido = false`.
- Ningún canal publica si `Autorizar publicación ≠ true`.
- Si `Canal primario = linkedin` y el auth token está expirado → bloquear en `publish_authorized` y alertar (no auto-publicar).

---

## 6. Relación con el skill `linkedin-david`

| Momento | Rol de `linkedin-david` | Permitido |
|---|---|---|
| Antes de `ready_for_review` | Calibrar POV, tono, audience-fit y CTA de David sobre el draft (`Copy LinkedIn`). | Sí |
| En `ready_for_review` (esperando Gate 1) | Inactivo. La pieza espera decisión humana. | No reescribir por defecto |
| Tras Gate 1 / Gate 2 | Inactivo. La voz ya fue aprobada por David. | No |
| Tras reapertura por comentario de David (E4) | Puede re-invocarse para ajustar voz según el feedback, devolviendo a `ready_for_review`. | Sí, solo si David reabrió |

`linkedin-david` **no publica, no marca checkboxes y no asume automatización** (E6). Su salida
alimenta `Copy LinkedIn` y campos de CTA; la decisión de avanzar es siempre humana.

---

## 7. Independencia del contrato respecto al runtime (EDITORIAL_02_DIAG_READY)

- El estado `EDITORIAL_02_DIAG_READY` y el `FailoverError` (Azure `store=false`, `rs_*` not found,
  cross-agent) son condiciones del **writer**, no del **gate humano** (I2).
- Una pieza ya en `ready_for_review` permanece válida y esperando a David aunque el writer esté caído.
- Pausar el lane del writer (decisión EDITORIAL-03, fuera de este spec) **no** altera este contrato;
  solo detiene la entrada de piezas nuevas.
- El claim "writer dispara @ HH:09 vía gateway interno" es **inferencia del enunciado** (I1) y debe
  verificarse en VPS antes de tratarse como hecho runtime (VPS Reality Check Rule).

---

## 8. Qué queda fuera y pendiente de decisión

- **No implementado aquí:** flujo n8n, Notion writes, provisioning de propiedades, scheduling.
- **Pendiente humano:** confirmar en VPS el trigger real del writer (I1) y decidir EDITORIAL-03
  (pausar lane vs fix schema vs redeploy skill) en su propia tarea.
- **Relación con spec v1:** este documento es una vista-contrato del hito humano; la fuente de
  verdad del schema completo sigue siendo `docs/specs/sistema-editorial-rick-v1.md` y
  `ADR-007-notion-como-hub-editorial.md`.

---

## 9. Referencias

- `docs/specs/sistema-editorial-rick-v1.md` §5 (schema) y §6 (estados y gates)
- `docs/adr/ADR-007-notion-como-hub-editorial.md`
- `docs/ops/editorial-agent-flow.md`
- `docs/ops/notion-publicaciones-ids-template.md`
- `openclaw/workspace-templates/skills/linkedin-david/SKILL.md`
- `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`
- `.agents/tasks/2026-06-01-001-copilot-vps-editorial-02-diag-linkedin-writer-granola.md` (EDITORIAL_02_DIAG_READY)
- `.agents/tasks/2026-06-01-004-editorial-03-pause-writer-azure-store-fix.md`

---

**VEREDICTO: M2_WIN01_SPEC_DRAFT_READY**
