# Clasificación de los 4 FAIL repetidos del e2e (2026-08-13)

> **Status:** acta docs-only del PKG-MACRO-P5-L2-T1. **Clasifica, no arregla.**
> **Superficie:** VPS `srv1431451`, clone canónico `~/umbral-agent-stack` @ `98d9a954`.
> Cero mutación de runtime: no se cargó ninguna credencial ni se tocó
> `openclaw.json`, el crontab, el gateway, el worker ni n8n, y cero escrituras a
> Notion. Sí hubo mutación de git en el clone: esta rama y su commit.
> **Origen:** reconteo E6 fila 34 / E-p4 — "mismos 4 FAIL en las 2 últimas
> corridas completas", hipótesis Fable *(no verificada)*: login de modelo del
> gateway.

## 0. Veredicto

Los 4 FAIL **no son cuatro fallos**: son **uno solo**, con **dos capas
superpuestas**, y la hipótesis de partida apuntaba al lado equivocado.

El worker no tiene credencial de **ningún** provider LLM: `/providers/status`
devuelve `"configured": []` con los 9 providers declarados en `unconfigured`.
Encima, `UMBRAL_DISABLE_CLAUDE=true` deshabilita por flag a `claude_pro`,
`claude_opus`, `claude_haiku` y `openclaw_proxy` — o sea que cargar credenciales
**no alcanza** para esos cuatro.

Capa única para las 4 filas: **preflight del modelo** — variante *credencial
ausente + provider deshabilitado por flag*, no *login vencido*.

## 1. Tabla de clasificación

| # | Test | Último resultado (2026-08-13 06:00 -04) | Capa | Causa raíz |
|---|---|---|---|---|
| 4 | `llm.generate` | `HTTPStatusError: Server error '500' for url 'http://127.0.0.1:8088/run'` | preflight del modelo | `RuntimeError: GOOGLE_API_KEY not configured` en el worker |
| 5 | `composite.research` | `ValueError: composite.research_report terminó en status=blocked: None` | preflight del modelo | **Derivado de #4**: `composite.py` importa y llama `handle_llm_generate` (líneas 13, 105, 130) |
| 14 | `R8: Routing coding` | `ValueError: No effective configured route for coding` | preflight del modelo | `has_configured_route: false`; los 4 providers de la cadena (`azure_foundry`, `claude_pro`, `gemini_pro`, `gemini_flash`) están `unconfigured` |
| 15 | `R8: Routing research` | `ValueError: No effective configured route for research` | preflight del modelo | Idéntico a #14 sobre la cadena de `research` |

## 2. Las dos capas, con su fuente

### 2.1 Credenciales ausentes

El mapa canónico es `_PROVIDER_ENV_REQUIREMENTS` en
`dispatcher/model_router.py:25-35` — no el env del worker. Exige:

| Provider | Env vars requeridas | ¿Presentes? |
|---|---|---|
| `azure_foundry` | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` | no / no |
| `openclaw_proxy` | `OPENCLAW_GATEWAY_TOKEN` | no |
| `claude_pro` / `claude_opus` / `claude_haiku` | `ANTHROPIC_API_KEY` | no |
| `gemini_pro` / `gemini_flash` / `gemini_flash_lite` | `GOOGLE_API_KEY` | no |
| `gemini_vertex` | `GOOGLE_API_KEY_RICK_UMBRAL` + `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` | no / no |

Verificado sobre **las tres** fuentes de env que declara el unit
(`systemctl --user cat umbral-worker`): `~/.config/openclaw/env` y los dos
opcionales `copilot-cli.env` / `copilot-cli-secrets.env`. Ninguna de las seis
variables aparece en ninguna de las tres. El primer archivo sí tiene otras 16
claves (Notion, Linear, X, YouTube, Tavily, GitHub, …): no es que el env esté
vacío, es que las de LLM nunca estuvieron.

### 2.2 Deshabilitados por flag

`UMBRAL_DISABLE_CLAUDE=true` está declarado en el env. Según
`_get_disabled_providers` (`model_router.py:43-47`), eso saca de juego a
`claude_pro`, `claude_opus`, `claude_haiku` **y `openclaw_proxy`**.

Consecuencia para quien haga el fix: `openclaw_proxy` es el candidato natural
para puentear al gateway, pero **cargar `OPENCLAW_GATEWAY_TOKEN` no lo va a
habilitar** mientras el flag siga en `true`. Son dos cosas, no una.

## 3. Repo dice vs VPS verifica

| | Repo dice | VPS verifica |
|---|---|---|
| Providers | `openclaw.json` declara 9 providers y cadenas de fallback por tarea (`coding`, `research`, `critical`, …) | `/providers/status` → `"configured": []`, los 9 en `unconfigured`, `has_configured_route: false` en toda ruta |
| Credenciales | `_PROVIDER_ENV_REQUIREMENTS` exige las 6 vars de §2.1 | ninguna presente en las 3 fuentes de env del unit |
| Gateway | — | `openclaw-gateway` reporta `active`; `openclaw models status` lista 5 modelos y default `openai/gpt-5.5` |

**Límite explícito de esta acta:** el estado del gateway se leyó con
`systemctl is-active` y `openclaw models status`. La regla dura 2 de
`openclaw-vps-operator` dice que ese comando **informa lo que registró, no lo
que pasa** — el 2026-08-06 reportó `ok` con el refresh token ya invalidado. Así
que "el gateway tiene modelos" queda **declarado, no probado**: no se corrió
ninguna sonda real contra él, porque este pack clasifica y no muta. Si el pack
de fix apuesta a la ruta `openclaw_proxy`, lo primero es esa sonda.

## 4. Hallazgo lateral (no es uno de los 4)

El cron `e2e-validation-cron.sh` corre con `--notion` y su post final falla
aparte, por longitud:

```
[ERROR] Notion add_comment failed (400): ... body.rich_text[0].text.content.length
should be ≤ 2000, instead was 2001
```

Un carácter por encima del límite. Es una quinta rotura del mismo cron, con
causa propia (truncado del cuerpo), independiente de los 4 FAIL.

## 5. Método

La corrida analizada es la del cron (2026-08-13 06:00 -04 = 10:00 UTC),
**posterior** al merge de T1 (`f278f875`, ~08:45 UTC), así que no hizo falta
re-ejecutar el e2e a mano: los 4 FAIL persisten con el checkout ya devuelto a
`main` y `ensure-main-for-run` pasando. Descarta que fueran un artefacto del
gate.

---

## 6. Resultado de la sonda al gateway (PKG-MACRO-P5-L2-T2, 2026-08-13)

§3 dejaba el estado del gateway como **declarado, no probado**, y nombraba la
sonda real como primer paso de cualquier fix por la vía `openclaw_proxy`. Se
corrió. **Falla.**

**El login de OpenAI del gateway está invalidado de forma permanente.** El
journal del propio `openclaw-gateway` (no `models status`) registra:

```
(auth_permanent). Re-authenticate with:
    openclaw models auth login --provider openai --force
OAuth token refresh failed for openai:
    OpenAI Codex token refresh failed (401): "code": "refresh_token_invalidated"
"message": "Your session has ended. Please log in again."
```

La entrada es de las **16:23:08 -04** y la sonda corrió a las **16:24:38**: es
una señal viva de un pedido real fallado, no un rastro histórico. Un `POST
/v1/chat/completions` contra `127.0.0.1:18789` devuelve `401 unauthorized`
(rechazo del gateway al cliente); el oráculo concluyente es el journal.

### Consecuencia para el plan de fix

La opción **A** (cablear `openclaw_proxy`: cargar `OPENCLAW_GATEWAY_TOKEN` en el
worker y apagar `UMBRAL_DISABLE_CLAUDE`) **no habría funcionado**, y el modo de
fallo habría sido peor que el actual: el worker habría alcanzado el gateway y el
gateway no alcanza a OpenAI, así que los mismos 4 tests fallarían un nivel más
adentro, ahora con una config mutada de por medio.

Quedan **tres capas** apiladas, no dos:

| # | Capa | Estado |
|---|---|---|
| 1 | Credenciales de provider ausentes en el worker (§2.1) | abierta |
| 2 | `UMBRAL_DISABLE_CLAUDE=true` apaga `claude_*` + `openclaw_proxy` (§2.2) | abierta |
| 3 | **Login OpenAI del gateway invalidado** (`refresh_token_invalidated`) | abierta — **bloquea la vía A** |

El orden correcto es 3 → 2 → 1: re-autenticar el provider `openai` en el gateway
(`reference-auth.md` de `openclaw-vps-operator`; ojo con `--force` después de un
login limpio) y recién entonces cablear el worker. La vía B (`gemini` / `azure`
con API key propia) no depende de la capa 3 y sigue disponible.

**Este pack no mutó nada:** la sonda es el gate del paquete y falló, así que no
se tocó el env del worker, ni el unit, ni el gateway. Verificado al cierre:
`UMBRAL_DISABLE_CLAUDE` sigue en `true`, `OPENCLAW_GATEWAY_TOKEN` sigue ausente
y el worker sigue con el mismo `ActiveEnterTimestamp` del 2026-07-25 (no hubo
restart). Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t2/`.

---

## 7. Re-auth del gateway OpenAI (PKG-MACRO-P5-L2-T3, 2026-08-13)

**Autorización citada de David:** "A — re-auth del gateway openai. Elegida
2026-08-13 post-T2. Este pack es SOLO capa 3." Prohibido explícito: cablear
`openclaw_proxy`, tocar `UMBRAL_DISABLE_CLAUDE`, cargar `OPENCLAW_GATEWAY_TOKEN`
en el worker, restart de `umbral-worker`. Nada de eso se tocó.

### 7.1 Diagnóstico pre-reauth

`journalctl --user -u openclaw-gateway --since "30 min ago"` mostró la misma
firma que §6, sin remediar: `auth_permanent` + `refresh_token_invalidated` a
las 16:23:07-08 -04, repetida para `openai/gpt-5.6-sol`, `openai/gpt-5.5` y
`openai/gpt-5.4` (los tres candidatos de fallback agotados).

Identidades `openai` antes del re-auth (agent `main`, cero tokens):

| # | Perfil | Expira (declarado) | Estado |
|---|---|---|---|
| 1 | `openai:david.a.moreira.m@gmail.com` | 2026-08-23T04:06:31.919Z | "vivo" según estado local — **falso**, ver regla dura 2 |
| 2 | `openai:umbral-rick` | 2026-08-12T18:23:38.683Z | expirado + disabled — zombi |

### 7.2 Re-auth headless (device-code, sin `--force`)

`script -qfc "openclaw models auth login --provider openai --device-code" /dev/null`.
Primer código expiró antes de que David pudiera completarlo en el browser (el
poller se cerró solo, sin quedar huérfano); segundo intento confirmado por
David. El login **refrescó el perfil existente** `openai:david.a.moreira.m@gmail.com`
en vez de crear un tercero — mismo nombre de cuenta OAuth, así que no hizo
falta `--force`. CLI: `Updated config: ~/.openclaw/openclaw.json` con backup
automático propio (`.bak`), no una edición manual del archivo.

Identidades después del re-auth:

| # | Perfil | Expira (declarado) | Rol |
|---|---|---|---|
| 1 | `openai:david.a.moreira.m@gmail.com` | 2026-08-23T21:09:06.062Z (refrescado) | activa |
| 2 | `openai:umbral-rick` | 2026-08-12T18:23:38.683Z | zombi — **no borrada**, según instrucción |

`openclaw models auth order set --provider openai --agent main
openai:david.a.moreira.m@gmail.com openai:umbral-rick` — override confirmado:
nueva primero, zombi segunda.

### 7.3 Sonda real post-login (oráculo = journal, no `models status`)

Nota de método: la misión pedía el token del gateway "leído del env vivo". No
existe ninguna variable `OPENCLAW_GATEWAY_TOKEN` — ni en `~/.config/openclaw/env`,
ni en `~/.openclaw/gateway.systemd.env`, ni en el `environ` real del proceso
gateway. El único campo que gobierna el Bearer de `/v1/chat/completions` es
`gateway.auth.token` en `~/.openclaw/openclaw.json` (config live). Se leyó en
runtime a una variable de shell, se usó una vez, se hizo `unset` de inmediato;
nunca se imprimió ni se logueó.

- Intento 1, `model=openai/gpt-5.6-sol` → `HTTP 400` (`Invalid model. Use
  openclaw or openclaw/<agentId>`) — el Bearer **sí fue aceptado** (no 401):
  el gateway hace su propio ruteo de modelo internamente.
- Intento 2, `model=openclaw/main` → `HTTP 200`, completion real
  (`finish_reason=stop`, respuesta "pong", `usage.total_tokens=27557`).
- Journal, ventana exacta 17:13:35–17:14:20 -04: **0 coincidencias** de
  `auth_permanent`, `refresh_token_invalidated` o `401`. Sanity extendida desde
  17:07 (momento del re-auth): igual, 0 coincidencias, contra las múltiples de
  16:23:07-08 pre-reauth.

**PASS.** La completion no cayó por `refresh_token_invalidated` y el journal de
esa ventana no registra `auth_permanent`.

### 7.4 Estado de las tres capas (actualiza §6)

| # | Capa | Estado |
|---|---|---|
| 1 | Credenciales de provider ausentes en el worker (§2.1) | abierta — fuera de alcance de este pack |
| 2 | `UMBRAL_DISABLE_CLAUDE=true` apaga `claude_*` + `openclaw_proxy` (§2.2) | abierta — fuera de alcance de este pack |
| 3 | Login OpenAI del gateway invalidado | **cerrada** — re-auth confirmado con sonda real |

**`P5_L2_GATEWAY_AUTH = Y`**. Capas 1 y 2 siguen bloqueando la vía A del
worker; recién con las tres cerradas tiene sentido cablear `openclaw_proxy`.

### 7.5 Gap detectado (Repo dice / VPS muestra)

`CLAUDE.md` y este mismo pack citan
`.claude/skills/openclaw-vps-operator/SKILL.md` y su
`references/reference-auth.md` como fuente de la regla dura 2 y del
procedimiento de re-auth (incl. el fallback fifo §3 para cuando el prompt no
drena por `script -qfc`). Ninguno de los dos existe hoy en el repo ni en
`~/.claude/skills` — quedaron fuera en la higiene del 2026-08-11
(`docs/operations/_archive-hygiene-vps-2026-08-11/`). Este pack se ejecutó con
las instrucciones explícitas del PKG y la regla dura 2 ya confirmada por la
evidencia de T2; no bloqueó, pero el gap queda pendiente de reparar.

**Cero mutación fuera de capa 3:** `UMBRAL_DISABLE_CLAUDE` sigue en `true`,
`OPENCLAW_GATEWAY_TOKEN` sigue sin cargarse en el worker, no hubo restart de
`umbral-worker`/`openclaw-dispatcher`/n8n, la identidad zombi `umbral-rick`
sigue presente. Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t3/`.
