# O18 — LinkedIn Auth Gap Report

> **Tipo**: spike de validación documental (read-only).
> **Owner**: Copilot VPS.
> **Branch**: `copilot-vps/o18-linkedin-auth-spike`.
> **Spec**: [`.agents/tasks/2026-05-08-O18-linkedin-auth-spike.md`](../../.agents/tasks/2026-05-08-O18-linkedin-auth-spike.md).
> **Plan ref**: O18 del plan Q2-2026.
> **Reglas**: 0 implementación, 0 escrituras al yaml, 0 llamadas a LinkedIn API.

## Summary

`config/auth_lifecycle.example.yaml` declara hoy el bloque LinkedIn asumiendo el modelo **non-MDP**: access_token de 60 días sin refresh_token, re-auth manual cada ~55 días. La doc oficial de Microsoft Learn (Authorization Code Flow + Programmatic Refresh Tokens) **confirma esa realidad**: access_token efectivamente vive 60 días (`expires_in: 5184000`), refresh_token requiere aprobación Marketing Developer Platform y dura ~365 días sin rotar. **Veredicto: el yaml sirve as-is con ajustes menores de naming y trazabilidad**, no requiere rework. Antes de implementar el handler `linkedin.post_share` el bloqueo NO está en el yaml — está en (1) decidir si pedir MDP approval (riesgo: rechazo + setup largo) o aceptar re-auth manual de 60d, y (2) crear la app en LinkedIn Developer Portal con `w_member_social` y redirect_uri productivo. El handler en sí es **S (small)** asumiendo HITL con token ya emitido.

## 1. Hechos extraídos doc oficial

Fuentes:

- [Authorization Code Flow (3-legged OAuth)](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow) — fetched 2026-05-07.
- [Refresh Tokens with OAuth 2.0](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens) — fetched 2026-05-07.

### Hechos duros

| # | Hecho | Valor exacto | Fuente |
|---|-------|--------------|--------|
| 1 | **access_token lifetime** | **60 días** (`expires_in: 5184000` segundos) | Authorization Code Flow §Step 3 / Response. Cita: *"Currently, all access tokens are issued with a 60-day lifespan."* |
| 2 | **refresh_token lifetime** | **365 días** (~31,536,000 segundos) | Programmatic Refresh Tokens §Introduction. Cita: *"By default, access tokens are valid for 60 days and programmatic refresh tokens are valid for a year."* |
| 3a | **Scope publishing en perfil personal** | **`w_member_social`** | Authorization Code Flow §Step 2 (sample request usa `liteprofile emailaddress w_member_social`). |
| 3b | **Scope publishing en company page** | **`w_organization_social`** (no usado por Rick — sin entidad legal) | Conocimiento estándar LinkedIn API; no requerido para v1 según [ADR-005](../adr/ADR-005-publicacion-multicanal.md). |
| 3c | **Scopes lectura básica** | `r_liteprofile`, `r_emailaddress` (legacy) o `openid profile email` (Sign In with LinkedIn v2 / OIDC). | Authorization Code Flow §Step 2. |
| 4 | **Endpoints OAuth** | authorize: `GET https://www.linkedin.com/oauth/v2/authorization`<br>token: `POST https://www.linkedin.com/oauth/v2/accessToken`<br>refresh: mismo endpoint que token, con `grant_type=refresh_token` | Authorization Code Flow §Step 2 + §Step 3 + Programmatic Refresh Tokens §Step 2. |
| 5 | **¿Refresh token rota en cada uso?** | **NO.** TTL del refresh_token se preserva desde la emisión inicial (no se renueva con cada refresh). Día 1 = 365 días; día 59 después de refrescar = **306 días** (365−59), no 365. El refresh_token devuelto en el body es el mismo string. | Programmatic Refresh Tokens §Introduction. Cita: *"the lifespan or Time To Live (TTL) of the refresh token remains the same as specified in the initial OAuth flow (365 days)"*. |
| 6 | **¿Refresh token requiere aprobación MDP?** | **SÍ.** Programmatic refresh tokens están reservados para **Marketing Developer Platform (MDP) approved partners**. Sin MDP: solo access_token de 60 días, sin refresh, re-auth manual obligatorio. | Programmatic Refresh Tokens página 1, primera línea: *"LinkedIn supports programmatic refresh tokens for all approved Marketing Developer Platform (MDP) partners."* |

### Hechos contextuales (no críticos pero relevantes)

- **Authorization code lifetime**: 30 minutos. Debe canjearse inmediatamente o reiniciar el flow.
- **Tamaño tokens**: ~500 caracteres hoy; LinkedIn pide soportar **≥1000** para futuras expansiones. Importante para schema de SQLite/Notion si se persisten.
- **Cambio de scopes invalida tokens previos**: *"If you request a different scope than the previously granted scope, all the previous access tokens are invalidated."* Implicación: cualquier rediseño futuro de scopes fuerza re-auth de todos los miembros.
- **Refresh transparente al usuario**: si el miembro está logueado en linkedin.com y el token aún no expiró, el authorize bypass-ea la pantalla de consentimiento — útil para flujos no-MDP que reauten programáticamente.
- **Revocación discrecional**: *"LinkedIn reserves the right to revoke Refresh Tokens or Access Tokens at any time due to technical or policy reasons."* El handler debe siempre tener fallback a re-auth manual.
- **Nota sobre publishing API**: La doc oficial de OAuth no cubre la API de publicación en sí. La realidad conocida (no extraída en este spike) es que `/rest/posts` (Posts API moderna) está reemplazando `/v2/ugcPosts` (UGC API legacy); ambas requieren `w_member_social` para perfil personal y `LinkedIn-Version` header. Validar en spike posterior antes de implementar.

### Discrepancia menor en la doc

El sample response de Programmatic Refresh Tokens §Step 1 muestra `"refresh_token_expires_in": 525600`, que en segundos da **~6 días** y contradice el texto "valid for a year". Probablemente el sample mezcla unidades (525600 minutos = 365 días) o es un valor sintético. **Autoritativo: el texto de la prosa (365 días)**, no el sample.

## 2. YAML diff table

Bloque actual relevante en [`config/auth_lifecycle.example.yaml`](../../config/auth_lifecycle.example.yaml) (líneas 14–37):

```yaml
- provider: linkedin
  credential_ref: linkedin_company_access_token
  warning_days: 14
  critical_days: 5
  notes: "OAuth 2.0 access token, 60-day TTL, no refresh (non-MDP). Re-auth required."
  owner: david
  reauth_playbook: >
    1. Open LinkedIn Developer App > Auth tab.
    2. Complete OAuth 2.0 Authorization Code flow.
    3. Update expires_at in config/auth_lifecycle.yaml.
    4. Update token in ~/.config/openclaw/env (LINKEDIN_ACCESS_TOKEN).

- provider: linkedin
  credential_ref: linkedin_refresh_authorization
  warning_days: 30
  critical_days: 14
  notes: "LinkedIn app authorization itself. Typically long-lived but can be revoked."
  owner: david
  reauth_playbook: >
    1. Verify app status at https://www.linkedin.com/developers/apps.
    2. Re-authorize if revoked.
```

### Diff campo por campo

| Campo | Doc oficial | YAML actual | Gap |
|-------|-------------|-------------|-----|
| `access_token` TTL | 60 días (5,184,000 s) | "60-day TTL" en `notes` | ✅ Sin gap. Coincide. |
| `refresh_token` TTL | 365 días si MDP, no existe si non-MDP | "no refresh (non-MDP)" en `notes` | ✅ Sin gap. Coincide con la realidad asumida. |
| `refresh_token` rota | NO (TTL se preserva desde emisión inicial) | No mencionado | ⚠️ Gap menor: si en el futuro David obtiene MDP, el `notes` debería aclarar que el cron de refresh debe contar contra emisión, no contra último uso. |
| Scope publishing | `w_member_social` | No declarado | ⚠️ Gap: el yaml es de lifecycle, no de scopes, pero conviene listar scopes esperados como `expected_scopes:` para detectar drift si LinkedIn cambia el granted set. |
| Endpoints OAuth | `oauth/v2/authorization` + `oauth/v2/accessToken` | No declarados | ⚠️ Gap: lifecycle tracker no necesita endpoints, pero el reauth_playbook podría linkear directo. |
| Aprobación MDP requerida | SÍ para refresh_token | Implícito en "non-MDP" | ⚠️ Gap menor: explicitar `mdp_approved: false` como flag separado en lugar de mezclarlo en notes. Permite alertar si el handler intenta usar refresh sin flag activo. |
| `credential_ref` naming | "company" vs perfil personal | `linkedin_company_access_token` | ❌ Gap real: contradice [ADR-005](../adr/ADR-005-publicacion-multicanal.md) §LinkedIn (Rick publica en **perfil personal**, sin Company Page por falta de entidad legal). Renombrar a `linkedin_personal_access_token`. |
| `credential_ref` naming refresh | Refresh token vs re-authorization | `linkedin_refresh_authorization` | ❌ Gap real: "refresh" en OAuth significa refresh_token. El campo describe en realidad "re-autorización del app" (consentimiento del usuario), no un refresh_token. Renombrar a `linkedin_app_authorization` o `linkedin_user_consent`. |
| Authorization code lifetime | 30 min | No declarado | ✅ No-gap. No es un credential a trackear; es transitorio en el flow. |
| Token size soporte | ≥1000 chars | No declarado | ⚠️ Gap si en futuro se persiste el token en SQLite/Notion: schema debe permitir VARCHAR(1024+). Out-of-scope del yaml de lifecycle. |
| Reauth playbook step 2 | OAuth Authorization Code flow | "Complete OAuth 2.0 Authorization Code flow" | ⚠️ Gap menor: muy genérico. Podría agregar redirect_uri esperado y URL de testing del Developer Portal Token Generator (https://www.linkedin.com/developers/tools/oauth/token-generator) como atajo manual. |
| Env vars referenciadas | `LINKEDIN_ACCESS_TOKEN` | Solo `LINKEDIN_ACCESS_TOKEN` | ⚠️ Gap: faltarán `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI` cuando se implemente el OAuth flow. Y eventualmente `LINKEDIN_REFRESH_TOKEN` si MDP. Documentar en `.env.example`. |

**Total de gaps**: **9** (2 ❌ reales con impacto en correctness/naming + 7 ⚠️ menores de completitud/trazabilidad). 0 gaps críticos que invaliden el approach actual.

## 3. Runtime state

### Handlers existentes

`grep -ril "linkedin" worker/ dispatcher/ identity/`:

| Archivo | Línea | Mención |
|---------|-------|---------|
| `worker/linear_team_router.py` | 32 | Keyword `"linkedin"` en lista de tags para routing de issues a team Marketing/Comms (no es un handler de publishing). |
| `worker/tasks/notion.py` | 541, 553 | Mapping `"linkedin": "LinkedIn"` y `("linkedin", "🎯")` — display name y emoji para canales en Notion (UI only). |
| `dispatcher/smart_reply.py` | 444 | `"linkedin.com"` en lista de domains conocidos (probablemente para inferir canal desde URL). |
| `dispatcher/intent_classifier.py` | 75 | Keyword `"linkedin"` en clasificador de intents (similar al routing). |

**Veredicto handlers**: **0 handlers de publishing existen hoy**. Solo referencias decorativas (display name, routing por keyword, dominio reconocido). No hay `linkedin.post_share`, `linkedin.oauth_refresh`, ni similar.

### SDK / cliente LinkedIn

`grep -rn "import.*linkedin\|from linkedin\|linkedin_api\|python-linkedin" worker/ dispatcher/ identity/ scripts/`:

- **0 imports**. No hay SDK de LinkedIn instalado, no hay cliente HTTP wrapper, no hay módulo `linkedin_client.py` (a diferencia de `worker/n8n_client.py` que sí existe).
- `pyproject.toml` no declara dependencia `linkedin-api`, `python-linkedin-v2`, `requests-oauthlib`, ni equivalentes.

### Env vars

`grep -rn "LINKEDIN_" worker/ dispatcher/ identity/ scripts/ config/`:

- Única referencia: `config/auth_lifecycle.example.yaml:26` mencionando `LINKEDIN_ACCESS_TOKEN` en el reauth_playbook.
- `.env.example` (verificar): no audited en este spike, asumir 0 entries productivas.
- Ninguna en runtime hoy. Ninguna integración usa nada de LinkedIn auth en producción.

### Docs previos

`grep -ril "linkedin" docs/`:

| Doc | Tamaño | Relevancia |
|-----|--------|------------|
| [`docs/plans/linkedin-publication-pipeline.md`](../plans/linkedin-publication-pipeline.md) | 459 líneas | Plan de diseño (sin código) del pipeline editorial completo. Hereda decisiones de [ADR-005](../adr/ADR-005-publicacion-multicanal.md). |
| [`docs/60-rrss-pipeline-n8n.md`](../60-rrss-pipeline-n8n.md) | 876 líneas | Plan/diseño para pipeline RRSS vía n8n (refleja arquitectura previa, anterior a [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) que clarifica "n8n bordes, no Notion writes"). |
| [`docs/adr/ADR-005-publicacion-multicanal.md`](../adr/ADR-005-publicacion-multicanal.md) | — | Decisión: LinkedIn perfil personal, HITL obligatorio (ToS §3.1.26), access token 60 días no-MDP, alerta día 55. **Coincide con la realidad de la doc oficial.** |
| [`docs/architecture/17-areas-gerencias-agentes-subagentes-model.md`](../architecture/17-areas-gerencias-agentes-subagentes-model.md) | — | Solo menciones decorativas a LinkedIn como uno de los canales. |

**Veredicto docs**: arquitectura editorial está **bien diseñada en papel** (ADR-005 + plan en `docs/plans/`). Falta el handler real, no el diseño.

## 4. Recommendations

### Prioridad 1 — Cambios mínimos al yaml (cuando se decida cerrar el spike)

| # | Acción | Archivo | Tipo |
|---|--------|---------|------|
| 1 | Renombrar `linkedin_company_access_token` → `linkedin_personal_access_token`. Coincide con ADR-005 (publicación en perfil personal). | `config/auth_lifecycle.example.yaml` | Naming |
| 2 | Renombrar `linkedin_refresh_authorization` → `linkedin_app_authorization` (clarifica que es re-consentimiento del usuario, no un refresh_token). | mismo | Naming |
| 3 | Agregar campo opcional `mdp_approved: false` (boolean) por entrada LinkedIn. Permite que el handler valide antes de intentar refresh programático. | mismo | Schema |
| 4 | Agregar campo opcional `expected_scopes: ["w_member_social"]`. Permite detectar drift cuando LinkedIn devuelva scopes distintos. | mismo | Schema |
| 5 | Actualizar `notes` para clarificar comportamiento de refresh_token cuando se obtenga MDP: TTL desde **emisión inicial**, no desde último uso. | mismo | Doc |
| 6 | Agregar al `reauth_playbook` el shortcut: `https://www.linkedin.com/developers/tools/oauth/token-generator` (Token Generator manual del Developer Portal). | mismo | Doc |
| 7 | Actualizar `.env.example` con stubs de `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`, `LINKEDIN_ACCESS_TOKEN`. | `.env.example` | Doc |

**Estimación**: <30 min. Una sola PR de yaml + .env.example. Cero impacto en runtime (es metadata).

### Prioridad 2 — Pre-requisitos antes del auto-poster

Antes de codear `linkedin.post_share`, deben resolverse en orden:

1. **Decisión MDP sí/no** (David):
   - **MDP yes**: setup largo (semanas-meses, application form, review por LinkedIn, no garantizado), pero habilita refresh tokens y publishing automático sin re-auth cada 60d.
   - **MDP no**: aceptar re-auth manual cada ~55d para siempre. Compatible con el HITL obligatorio que ya impone ToS §3.1.26 (David clickea "Publicar" en cada post, así que clickear "Re-auth" cada 60d no es fricción adicional dramática).
   - **Recomendación spike**: arrancar **non-MDP**, confirmar que el handler funciona, evaluar MDP solo si volumen lo justifica (>4 posts/mes con drift de re-auth incómodo).
2. **Crear LinkedIn Developer App** (David):
   - Portal: https://www.linkedin.com/developers/apps
   - Producto a solicitar: **"Share on LinkedIn"** (self-serve, no requiere MDP) → habilita scope `w_member_social`.
   - Configurar redirect_uri productivo: candidato `https://<vps-domain>/oauth/linkedin/callback` o `http://localhost:8088/oauth/linkedin/callback` para test inicial. Notar que LinkedIn requiere **HTTPS absoluto en producción**, sin parámetros, sin `#`.
   - Almacenar Client ID + Client Secret en `~/.config/openclaw/env` (no en repo).
3. **Primer flow OAuth manual** (David, una sola vez):
   - Usar el Token Generator del Developer Portal para emitir el primer access_token de 60 días.
   - Cargar `LINKEDIN_ACCESS_TOKEN` en env del worker.
   - Actualizar `expires_at` en `config/auth_lifecycle.yaml` (no example) con la fecha real.
   - Esto desbloquea el handler sin necesidad de implementar el OAuth callback completo en v0.
4. **Decisión scope publishing API** (técnica, en otro spike):
   - **UGC Posts** (`/v2/ugcPosts`): legacy, sigue funcionando, header `LinkedIn-Version` opcional.
   - **Posts API** (`/rest/posts`): moderna, requiere header `LinkedIn-Version: <YYYYMM>` versionado mensual, restWLI versioning.
   - Mientras LinkedIn no deprecate UGC, ambas son viables. Para v0, recomendación: **Posts API** (`/rest/posts`) por ser donde LinkedIn invierte; documentar el `LinkedIn-Version` esperado.
5. **NO usar nodo LinkedIn de n8n** mientras persista el bug conocido del header `LinkedIn-Version` (heredado de [ADR-008](../adr/ADR-008-orquestacion-editorial.md) §Restricciones operativas). Si se va por n8n, usar HTTP Request node con headers explícitos.
6. **Confirmar regla anti-Notion-write desde n8n** ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)): el handler `linkedin.post_share` vive en `worker/tasks/`, NO en n8n.

### Prioridad 3 — Estimación handler `linkedin.post_share`

**Tamaño: S (Small) — 1-2 días de trabajo asumiendo HITL y access_token ya emitido manualmente.**

Desglose:

| Subtarea | Estimación | Dependencias |
|----------|------------|--------------|
| Cliente HTTP wrapper (`worker/linkedin_client.py`) — POST a `/rest/posts` con auth Bearer + `LinkedIn-Version` | 2-3 h | `httpx` (ya en stack) |
| Handler `worker/tasks/linkedin.py` con función `post_share(post_id, content, media_urls)` | 2-3 h | Cliente arriba + parser de blocks Notion → texto LinkedIn (límite 3000 chars) |
| HITL gate: lectura de `aprobado_publicacion=true` desde Notion antes de postear | 1 h | Patrón ya existente en otros handlers |
| Idempotencia: validar `content_hash` previo al POST, persistir `linkedin_post_urn` en Notion post-éxito | 1-2 h | Pattern `worker/tasks/notion.py` existente |
| Handler `linkedin.refresh_token_check`: chequea `expires_at` y emite alerta a Notion si <warning_days. NO refresca automáticamente (non-MDP). | 1 h | Solo si MDP=no |
| Tests unitarios (mock LinkedIn API con `respx`) | 2-3 h | Pattern existente |
| Doc en `docs/handlers/linkedin.md` | 1 h | — |

**Total**: ~10-14 horas si MDP=no. Suma **+1-2 días** si MDP=yes (auto-refresh handler con persistencia del refresh_token cifrado).

**Tamaño M** si se incluye el OAuth callback completo (servidor HTTPS público para `/oauth/linkedin/callback` con state validation) — esto es necesario solo para auto-emisión de tokens, no para v0 con token manual.

**Tamaño L** si se incluye además: gestión multi-cuenta (Rick + futuros clientes), encryption-at-rest para refresh_token, retries con backoff diferenciado por error LinkedIn, metrics de rate limit. Solo si MDP+escala.

## 5. Open questions

Lo que la doc oficial no aclara y requiere prueba en sandbox o consulta a LinkedIn support:

1. **Comportamiento del `expires_in` post-refresh sin MDP**: ¿el authorize bypass cuando el miembro está logueado emite un access_token "fresco de 60 días" o respeta algún cap? La doc sugiere fresco, pero conviene medir en práctica antes de prometer SLA al usuario.
2. **Rate limits del endpoint `/rest/posts`**: la doc OAuth no los expone. Hay que consultar [Posts API docs](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/posts-api) en otro spike. Volumen objetivo Rick: ~20-40 posts/mes — muy debajo de cualquier umbral conocido, pero verificar.
3. **Versionado `LinkedIn-Version` requerido o recomendado**: Posts API moderna requiere el header. ¿Cuál es el valor mínimo soportado al 2026-05? Validar en sandbox antes de cablear constante en código.
4. **Behavior de revocación silenciosa**: la doc dice que LinkedIn puede revocar tokens "at any time". ¿Hay endpoint para validar si un token sigue vivo sin gastar una llamada de publishing? Probablemente `GET /v2/me` con el token, pero confirmar.
5. **Autorenovación cuando el miembro está deslogueado**: la doc dice "if member is no longer logged in to www.linkedin.com or their access token has expired, they are sent through the normal authorization process". Para Rick (single-user), David puede simplemente loguear y refrescar — pero ¿hay forma de saber proactivamente que el next refresh fallará? Probablemente no sin intentarlo.
6. **Aplicabilidad real del scope `w_member_social` para programmatic POST sin MDP**: la doc OAuth lo describe como disponible vía "Share on LinkedIn" product (self-serve). Confirmar en el Developer Portal en cuanto David cree la app — algunos reportes en el ecosistema sugieren que LinkedIn restringió self-serve a partir de 2024 y ahora pide justificación adicional. Riesgo bajo pero no cero.
7. **HITL formal requerido por ToS §3.1.26 — ¿"David clickea publicar" es suficiente o LinkedIn quiere otro tipo de evidencia?** ADR-005 lo asume zanjado, pero conviene re-verificar términos al 2026-05 antes del primer post real.
8. **Gestión del refresh_token si se obtiene MDP**: ¿dónde se persiste? Opciones: (a) Notion encrypted property (mala — Notion no es secrets store), (b) `~/.config/openclaw/env` (rotación manual al refresh — friccionante), (c) SQLite encriptada con key en env (mejor). Decidir antes de habilitar MDP, no después.

## Anexo — Referencias

- [Authorization Code Flow (3-legged OAuth) — Microsoft Learn](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [Refresh Tokens with OAuth 2.0 — Microsoft Learn](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens)
- [LinkedIn Developer Portal Tools (Token Generator)](https://learn.microsoft.com/en-us/linkedin/shared/authentication/developer-portal-tools)
- [Getting Access — Microsoft Learn](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access)
- [ADR-005 Publicación Multicanal](../adr/ADR-005-publicacion-multicanal.md)
- [ADR-008 Orquestación Editorial](../adr/ADR-008-orquestacion-editorial.md)
- [ADR-011 Orquestación Editorial — Criterios Duros](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)
- [Plan: pipeline publicaciones LinkedIn](../plans/linkedin-publication-pipeline.md)
- [Spec O18](../../.agents/tasks/2026-05-08-O18-linkedin-auth-spike.md)
