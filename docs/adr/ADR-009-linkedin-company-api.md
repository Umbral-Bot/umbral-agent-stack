# ADR-009: Publicación en LinkedIn Cuenta Empresa vía API

## Estado

Proposed — 2026-06-06

> Deriva del flujo confirmado en `docs/editorial-pipeline/production-flow-v2-2026-06-06.md`.
> Modifica `docs/specs/sistema-editorial-rick-v1.md` §3 (LinkedIn Company Page sale de "fuera de alcance") y §8.2 (canal LinkedIn pasa de perfil personal HITL a cuenta empresa vía API).

> **⚠️ Nota P0 (norte 2026-07-22 — Fila I = B):** el POST automático a la Company
> Page que propone este ADR queda **diferido**. Bajo el norte editorial 2026-07-22,
> las RRSS no se autopublican (LinkedIn ToS §3.1.26; `ADR-010` §29): el sistema
> inyecta el link del blog + copy y deja estado `listo_rrss` para post **humano**.
> Este ADR revive (Fila I = A) solo si David lo decide **y** LinkedIn aprueba el
> access review de Community Management API. Ver
> `docs/ops/editorial-norte-hitl-contract-2026-07-22.md` §5.I y §7.

## Contexto

El diseño previo (spec v1 §3, §8.2) publicaba en LinkedIn **perfil personal** con HITL manual, y dejaba la **Company Page fuera de alcance** ("requiere CMA + entidad legal").

David confirmó (2026-06-06) que quiere publicar en la **cuenta de empresa vía API**, de forma automática tras sus gates en Notion + confirmación final por Telegram. David es **admin de la página** y puede crear/gestionar una app en LinkedIn Developer.

## Decisión

**Publicar en la LinkedIn Company Page de Umbral usando la API oficial de LinkedIn (Posts API con contexto de organización), con HITL conservado como confirmación final por Telegram.**

### Requisitos de acceso

- **App en LinkedIn Developer Portal** asociada a la organización.
- **Producto Community Management API** (organización) habilitado en la app — requiere **access review** de LinkedIn (no es inmediato).
- **Scope** `w_organization_social` (publicar como organización) + lectura de organización para resolver el URN.
- **Rol**: David como administrador de la Company Page; la app autorizada por un admin.
- **OAuth 2.0** (Authorization Code). El `author` del post es el **URN de la organización** (`urn:li:organization:{id}`), no el del miembro.

### Contrato de publicación

- **Endpoint**: `POST https://api.linkedin.com/rest/posts`.
- **Header obligatorio**: `LinkedIn-Version: YYYYMM` (revisar trimestralmente; 426 si caduca).
- **author**: `urn:li:organization:{org_id}`.
- **Media (imagen elegida en Notion)**: flujo async `POST /rest/images?action=initializeUpload` → PUT binario → polling hasta `AVAILABLE` → URN.
- **Idempotencia**: respetar `publication_content_hash`; no reintentar POST si ya hay post ID.

### HITL conservado

- El POST a LinkedIn **solo** ocurre tras: Gate 2 en Notion (`Autorizar publicación`) + imagen elegida + **confirmación final por Telegram** ("ok publica").
- Esto preserva el espíritu del gatekeeper: nada sale sin orden humana explícita sobre el texto final, la imagen final y el canal.

## Alternativas consideradas

### A. Mantener perfil personal con HITL manual (diseño previo)

Rechazada por decisión de producto: David quiere cuenta empresa y automatización post-gate.

### B. Nodo LinkedIn directo de n8n

Rechazada para el POST productivo mientras exista el bug del header `LinkedIn-Version` (ver `ADR-008`). Si se usa n8n para el borde, debe ser **HTTP Request** con versión explícita.

### C. Publicar empresa + personal en paralelo desde v1

Diferida. David eligió "empezar con empresa, definir personal después".

## Consecuencias

### Positivas

- Publicación automática real en el canal objetivo (empresa) tras gates.
- Atribución institucional (marca Umbral) en lugar de perfil personal.

### Negativas / Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Access review de LinkedIn demora o rechaza | Alto (bloquea canal) | Iniciar el trámite temprano; mantener blog/X operativos mientras tanto |
| `LinkedIn-Version` header caduca (426) | Medio | Revisión trimestral del header; alerta automatizada |
| Token de organización expira / re-auth | Medio | Tracking de auth lifecycle en Agent Stack; alerta día 55 |
| Cambios de política de la Community Management API | Medio | Aislar en adapter; version-lock |

## Pendientes

1. Crear/identificar la app de LinkedIn Developer y solicitar Community Management API (David admin + Copilot).
2. Resolver `org_id` de la Company Page de Umbral.
3. Construir el adapter de publicación (Worker `editorial.publish.linkedin_org`).
4. Definir almacenamiento seguro del token de organización (no en repo; env VPS / Key Vault).

## Contención B4 (2026-07-20)

Mientras el handler `editorial.publish.linkedin_org` (Pendiente 3) no exista,
`scripts/discovery/stage9c_linkedin_publish.py` queda **contenido fail-closed**
por `scripts/discovery/lib/linkedin_org_guard.py`. Un POST real solo procede si
se cumplen las **tres** condiciones:

1. `endpoint == "/rest/posts"` (Company Posts API, no el personal `/v2/ugcPosts`);
2. `author` es `urn:li:organization:*` resuelto (no placeholder, no `urn:li:person:*`);
3. `RICK_LINKEDIN_ORG_PUBLISH_ENABLED` truthy (default **off**).

Como stage9c aún apunta a `/v2/ugcPosts`, la condición (1) nunca se cumple hoy,
así que el guard **siempre bloquea el POST real** y deja `--dry-run` como único
camino. Esto contiene una invocación manual/accidental bajo identidad personal
legacy sin publicar. Cablear el handler org (endpoint + payload `/rest/posts` +
resolución del URN de organización) sigue siendo trabajo aparte de esta
contención. Ver `docs/plans/tanda-b-security-execution-plan-2026-07-19.md` §5.

## Referencias

- `docs/editorial-pipeline/production-flow-v2-2026-06-06.md` — flujo confirmado.
- `docs/specs/sistema-editorial-rick-v1.md` §8.2 — contrato LinkedIn previo (perfil personal).
- `docs/adr/ADR-008-orquestacion-editorial.md` — restricción del nodo LinkedIn de n8n.
- Skill `linkedin-marketing-api-embudo` — productos, permisos y access tiers de LinkedIn.
