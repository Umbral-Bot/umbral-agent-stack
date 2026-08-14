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

---

## 8. Cableado de `openclaw_proxy` — capas 1 y 2 (PKG-MACRO-P5-L2-T4, 2026-08-13)

**Autorización citada de David:** "A — las dos capas en el mismo pack, orden
2→1 (flag, después token, restart worker, 4 tests). Elegida 2026-08-13
post-T3." Prohibido explícito: `quota_policy.yaml`, `UMBRAL_DEFAULT_MODEL`,
`DEFAULT_MODEL`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, Azure/Foundry, editar
`openclaw.json`, restart de gateway/n8n, `--force`, borrar la zombi
`umbral-rick`.

### 8.1 Preflight

Journal de `openclaw-gateway` (15 min previos): 0 coincidencias de
`auth_permanent`/`refresh_token_invalidated` — capa 3 seguía cerrada, no hubo
regresión. `EnvironmentFile` de `umbral-worker`: `~/.config/openclaw/env`
(primario), `copilot-cli.env`, `copilot-cli-secrets.env`. `EnvironmentFile` de
`openclaw-dispatcher`: el **mismo** archivo primario que el worker — un solo
archivo cubre ambos units, sin duplicar. Backup de los tres archivos del
worker antes de tocar nada (permisos 600, en la evidencia del pack).

### 8.2 Capa 2 — `UMBRAL_DISABLE_CLAUDE`

`true` → `false`, explícito, en la única línea donde vivía (`~/.config/openclaw/env`).
No se dejó comentado ni ambiguo.

### 8.3 Capa 1 — `OPENCLAW_GATEWAY_TOKEN`

Copiado desde `gateway.auth.token` de `~/.openclaw/openclaw.json` (leído, no
editado) hacia una línea nueva en `~/.config/openclaw/env`. Lectura a
variable de shell → escritura → `unset` inmediato; cero `echo`/`cat`/log del
valor en ningún paso. Verificado post-hoc: `copilot-cli.env` y
`copilot-cli-secrets.env` quedaron byte-idénticos al backup (`diff -q`).

### 8.4 Restart y verificación

`systemctl --user restart umbral-worker` y `openclaw-dispatcher` (comparten el
archivo parchado). `openclaw-gateway` **no tocado** —
`ActiveEnterTimestamp` idéntico antes/después (`2026-08-12 12:34:19 -04`).
`ActiveEnterTimestamp` de `umbral-worker`: `2026-07-25 21:30:38` →
`2026-08-13 17:26:23` (cambió, confirma restart real, no cache). Mismo salto
en `openclaw-dispatcher`. Los tres units `active` post-restart.

`GET /providers/status` (sin secretos):

```
configured:   ["openclaw_proxy"]
unconfigured: [azure_foundry, claude_haiku, claude_opus, claude_pro,
               gemini_flash, gemini_flash_lite, gemini_pro, gemini_vertex]
```

`openclaw_proxy` pasó a `configured: true`. **El cableado cumplió.**

### 8.5 Los 4 tests (`scripts/e2e_validation.py`, sin `--notion`)

Los 4 siguen en **FAIL**, pero ya no por credencial/flag ausente — por una
capa distinta y explícitamente fuera de alcance de este pack:

| Test | Resultado | Causa |
|---|---|---|
| `llm.generate` | FAIL | `RuntimeError: GOOGLE_API_KEY not configured` — sin modelo explícito usa `DEFAULT_MODEL=gemini-2.5-pro`, no pasa por `openclaw_proxy` |
| `composite.research` | FAIL | `ValueError: ... status=blocked: None` — derivado de `llm.generate` (§2, ya documentado en T1) |
| `R8: Routing coding` | FAIL | `ValueError: No effective configured route for coding` — `quota_policy.yaml` no incluye `openclaw_proxy` en ninguna cadena |
| `R8: Routing research` | FAIL | ídem, sobre la cadena `research` |

Resto de la suite (contexto, no gate): 11/17 PASS, 3 SKIP (sin API keys de
OpenAI/Google/Vertex — esperado), 6 FAIL total (incluye dos tests de
Anthropic/Claude, también fuera de alcance).

### 8.6 Veredicto y rollback

Por instrucción explícita del pack: si `configured=sí` pero los 4 fallan por
ruteo/Gemini, **no hay rollback automático** — el cableado cumplió su objetivo
y se documenta el bloqueo de la capa siguiente. Se dejó el env como quedó
(`UMBRAL_DISABLE_CLAUDE=false`, `OPENCLAW_GATEWAY_TOKEN` presente).

**`P5_L2_PROXY_WIRED = Y`.** Gate de los 4 tests: **BLOCKED, capa ruteo**
(`quota_policy.yaml` no tiene `openclaw_proxy` en ninguna cadena de fallback)
+ **capa default-model** (`llm.generate` sin modelo explícito depende de
`GOOGLE_API_KEY`, ausente). Ninguna de las dos se tocó — ambas están en la
lista de prohibidos de este pack. Evidencia completa en
`~/.coord-ag-evidence/pkg-macro-p5-l2-t4/`.

---

## 9. Ruteo + default al proxy — código, y un incidente real (PKG-MACRO-P5-L2-T5, 2026-08-13)

**Autorización citada de David:** "C — yaml + default al proxy en el mismo
pack, para los 4 tests por la vía openclaw_proxy." Constraint duro: generación
de imagen = Magnific vía MCP (no tocado en este pack).

### 9.1 Cambios de código (probados, correctos)

- `config/quota_policy.yaml`: `openclaw_proxy` agregado al **final** de
  `fallback_chain` en las 7 `task_types`, sin tocar ningún `preferred`. Bloque
  `providers.openclaw_proxy` nuevo (mismo orden de magnitud que `claude_pro`).
- `worker/tasks/llm.py`: `handle_llm_generate` ahora usa `_default_model()`
  cuando el input no trae `model` ni `selected_model` — con
  `OPENCLAW_GATEWAY_TOKEN` presente y Claude no deshabilitado, cae en
  `claude-sonnet-4-6` (→ `openclaw_proxy` vía `_detect_provider`); sin token,
  el default histórico (Gemini) sigue igual.
- **Bug encontrado y corregido** (no estaba en el alcance original, pero
  bloqueaba todo lo demás): `_call_openclaw_proxy` reenviaba el `model`
  solicitado (p.ej. `claude-sonnet-4-6`) tal cual al gateway. El endpoint
  `/v1/chat/completions` del gateway hace su **propio** ruteo interno de
  modelo y devuelve `400 Invalid model. Use openclaw or openclaw/<agentId>`
  para cualquier otro valor — verificado en vivo contra `127.0.0.1:18789`
  (mismo patrón que T3 §7.3). Corregido: el payload saliente ahora usa
  `openclaw/<agent>` (`OPENCLAW_GATEWAY_AGENT`, default `main`); el `model`
  solicitado se sigue preservando en el valor de retorno.
- `worker/app.py`: `_PROVIDER_MODELS` no tenía entrada para `openclaw_proxy`,
  así que `/providers/status` reportaba `effective_model="unknown"` para
  `coding`/`research` aunque `has_configured_route` ya fuera `true` —
  inconsistente con `dispatcher/service.py:PROVIDER_MODEL_MAP`, que sí lo
  tiene (`anthropic/claude-sonnet-4-6`). Agregado, ambos mapas ahora coinciden
  — necesario para que `R8: Routing coding/research` puedan comparar
  `expected_model` contra el `model` real que devuelve la tarea.
- Efecto colateral encontrado y corregido: `~/.config/openclaw/env` ya trae un
  `OPENCLAW_GATEWAY_TOKEN` real desde T4, y varios archivos de test importan
  `worker.config` (que lo carga) sin aislarlo — 17 tests en 5 archivos
  (`test_model_router.py`, `test_llm_handler.py`,
  `test_model_routing_integration.py`, `test_dispatcher_model_routing.py`,
  `test_provider_detection.py`) empezaban a resolver `openclaw_proxy` en vez
  de `anthropic`/`quota_exceeded` por la fuga. Mismo patrón que el leak de
  `UMBRAL_DISABLE_CLAUDE` ya documentado ahí como "Task 042" — extendido para
  cubrir también `OPENCLAW_GATEWAY_TOKEN`.
- `pytest tests/test_model_router.py tests/test_llm_handler.py -v`: **72
  passed**. Suite completa (`pytest tests/`, excluyendo 3 fallos
  pre-existentes y no relacionados en `test_pit_*` por `ModuleNotFoundError:
  pydantic` en un subproceso — confirmado que fallan igual sin este pack
  aplicado): **4788 passed, 6 skipped, 2 xfailed**.

### 9.2 Live: ruteo confirmado, pero incidente real del gateway

Restart de `umbral-worker` + `openclaw-dispatcher` (gateway intacto, timestamp
sin cambios en ese momento). `GET /providers/status` post-restart:

```
configured: ["openclaw_proxy"]
coding:    has_configured_route=true, effective_preferred=openclaw_proxy, effective_model=anthropic/claude-sonnet-4-6
research:  has_configured_route=true, effective_preferred=openclaw_proxy, effective_model=anthropic/claude-sonnet-4-6
```

El ruteo (paso 1) y el default (paso 2) funcionan exactamente como se pidió.
Pero al correr `scripts/e2e_validation.py` real (sin `--notion`), el tráfico
concurrente hacia `openclaw_proxy` — que invoca `openclaw/main`, el agente
**completo** de producción (spawnea sub-procesos `codex app-server` por
invocación, ~30–160s y ~27K prompt tokens por llamada, visto ya en T3 §7.3
para un simple "ping") — **tumbó el gateway compartido**, que systemd
reinició solo (`NRestarts=4`, PID nuevo, `ActiveEnterTimestamp` saltó de
2026-08-12 12:34:19 —estable >24h— a 2026-08-13 18:05:38). No se corrió
`systemctl restart openclaw-gateway` en ningún momento.

Causa: el lane `main` del gateway tiene concurrencia limitada
(`activeAhead=4 activeNow=3 queueBehind=1`, visto en journal). Este pack
disparó ~6-7 llamadas casi simultáneas vía `openclaw_proxy`
(`llm.generate`, `composite.research` ×2 subllamadas, `R8: Claude provider`,
`R8: Routing coding`, `R8: Routing research`), que compitieron por esos slots
contra tráfico real de producción — incluido al menos un cron interrumpido
(`lane=cron-nested ... codex app-server client closed before turn completed`).
27 líneas de `ClientDisconnectError`/`codex app-server client closed`/`lane
wait exceeded` en la ventana 18:00–18:06 (evidencia, sin secretos).

Resultado del e2e run: los 4 tests siguen en FAIL, pero ya no por
config/ruteo/Gemini — por timeouts y `500 OpenClaw gateway unreachable`
durante la ventana de crash+respawn.

Post-incidente (verificado read-only): `umbral-worker`, `openclaw-dispatcher`
y `openclaw-gateway` los tres `active`, `curl /health` del worker con
`ok=true`. **No se repitió el e2e run** — repetirlo arriesga otro crash del
gateway compartido que usa David en producción.

### 9.3 Veredicto

**`P5_L2_ROUTE_AND_DEFAULT = BLOCKED`** — pero **capa capacidad/confiabilidad
del gateway**, no la capa ruteo/Gemini que preveía la misión original. El
código (ruteo + default + fix del payload + consistencia de mapas) es
correcto y está probado con 149+ tests unitarios nuevos/actualizados. El
riesgo no está en el cableado — está en usar `openclaw_proxy` (hoy: único
modelo disponible es el agente completo `openclaw/main`) como backend de
`llm.generate` a la escala de tráfico concurrente real.

**Sin rollback automático** del env (`UMBRAL_DISABLE_CLAUDE=false`,
`OPENCLAW_GATEWAY_TOKEN` presente) ni del código: ambos son correctos y están
probados: el peligro es de *uso a escala*, no de *cableado incorrecto*. Queda
para decisión de David:

- (a) agregar al gateway un agente liviano dedicado a completions (fuera de
  alcance/prohibido en este pack — requiere editar `openclaw.json`), o
- (b) no usar `openclaw_proxy` como default de `llm.generate` sin modelo
  explícito hasta que exista esa vía liviana (revertir solo `_default_model()`
  en `worker/tasks/llm.py`, dejando el ruteo de `quota_policy.yaml` y el fix
  de `_call_openclaw_proxy` — ambos correctos independientemente de esta
  decisión).

Evidencia completa (incl. journal del crash, sin secretos) en
`~/.coord-ag-evidence/pkg-macro-p5-l2-t5/`.

### 9.4 `/code-review` (xhigh, 10 ángulos + verify + sweep) — hallazgo de seguridad más grave que el incidente

Corrido sobre el diff de código de este pack (no sobre la acta). 22 candidatos
generados, **0 refutados** — 20 CONFIRMED/PLAUSIBLE + 2 del sweep, reportados
como 15 findings priorizados vía `ReportFindings`. Se aplicaron los fixes
seguros y de bajo riesgo antes de abrir el PR; el resto queda documentado
para decisión de David.

**El hallazgo más importante no es de código — es de alcance.** `_default_model()`
no solo afecta a `llm.generate`/`composite.research` (lo que este pack
probó): también gobierna, sin cambio de código propio, dos rutas que
**nunca pasan por el Dispatcher/ModelRouter** porque llaman `/run` directo:

- `dispatcher/smart_reply.py::_do_llm_generate` — **respuestas y planes de
  smart-reply de Notion Control Room que ve David.**
- `scripts/daily_digest.py::generate_llm_summary` — el resumen del digest
  diario.
- `worker/tasks/composite.py` (`_generate_queries`,
  `_generate_report_with_retry`) — ya cubierto en §9.1-9.3.

Las tres rutas omiten `model`/`selected_model` (son las únicas en todo el
repo que lo hacen, junto a un puñado de llamadas de test), así que con
`OPENCLAW_GATEWAY_TOKEN` presente (ya está, desde T4) las tres **cambian de
Gemini a Claude-vía-`openclaw_proxy` en producción, ahora mismo, sin que
nadie lo haya pedido para ellas específicamente** — y heredan el mismo
camino pesado y frágil (`openclaw/main`, turno de agente completo) que
**ya tumbó el gateway compartido** en §9.2. Cero tracking de cuota en las
tres (`QuotaTracker.record_usage` nunca se llama en este camino). Cero
cobertura de test.

Además: en `~/.openclaw/openclaw.json`, el agente `main` (el que
`OPENCLAW_GATEWAY_AGENT` usa por default) tiene `model.primary =
"openai/gpt-5.6-sol"` — **cero proveedores Anthropic configurados**. O sea
que hoy, literalmente, `provider: "openclaw_proxy"` en la respuesta **no
significa que Claude generó el texto** — lo generó GPT-5.6-sol, y
`trace_llm_call`/`ops_log.llm_usage`/`/providers/status` lo registran como
si fuera Claude, sin ningún chequeo.

**Fixes aplicados (seguros, no cambian el alcance de `_default_model()`):**

| Archivo | Fix |
|---|---|
| `worker/tasks/llm.py` | `MODEL_ALIASES["openclaw_proxy"]` agregado — sin esto, `selected_model="openclaw_proxy"` literal (mismo patrón de alias que `claude_pro`/`gemini_flash`) caía silenciosamente a Gemini vía el catch-all de `_detect_provider` y tiraba `GOOGLE_API_KEY not configured` |
| `worker/tasks/llm.py` | `_default_model()` ahora lee `MODEL_ALIASES["claude_pro"]` en vez de un literal hardcodeado duplicado |
| `tests/conftest.py` + 5 archivos | Fuga de `OPENCLAW_GATEWAY_TOKEN`/`UMBRAL_DISABLE_CLAUDE` (mismo patrón que "Task 042") centralizada en un fixture `autouse` compartido, en vez de duplicada 6 veces (2 sitios ya habían divergido dentro de este mismo diff) |
| `tests/test_openclaw_proxy.py` | 2 tests nuevos cubriendo el fix de `MODEL_ALIASES` end-to-end |

`pytest tests/` tras los fixes: **4790 passed** (2 más que en §9.1, por los
tests nuevos), mismos 3 fallos pre-existentes de `test_pit_*` deseleccionados.

**No corregidos en este pack (documentados, `ReportFindings` con
`outcome=skipped`):** el alcance de `_default_model()` sobre
`smart_reply.py`/`daily_digest.py`/`composite.py` (requiere una decisión de
producto, no un fix mecánico); el mismatch `provider/model` cuando el
agente del gateway corre un modelo distinto al pedido; el hijack silencioso
de `claude_pro`/`opus`/`haiku` cuando `ANTHROPIC_API_KEY` también esté
configurado (late, no activo hoy); duplicación de `PROVIDER_MODEL_MAP` en
3 lugares; `DEFAULT_ROUTING` en Python sin `openclaw_proxy`; ineficiencias
preexistentes de `QuotaTracker` (fuera de los archivos de este pack).

**Recomendación urgente para David:** el riesgo de crash del gateway
compartido (§9.2) ya no es solo "mi e2e run lo tumbó" — es un riesgo
**activo y continuo** cada vez que alguien dispara un smart-reply, el
digest diario, o `composite.research_report`, sin que este pack lo haya
pedido para esos tres casos. Antes del próximo uso real de cualquiera de
esas tres rutas, decidir entre: (a) revertir el alcance de
`_default_model()` a solo los casos explícitamente autorizados (acotarlo
por `task_type`/caller en vez de global), (b) agregar al gateway un agente
liviano dedicado a completions (fuera de alcance de este pack, requiere
`openclaw.json`), o (c) aceptar el riesgo conscientemente. Esta prohibido
tocar `UMBRAL_DISABLE_CLAUDE`/`OPENCLAW_GATEWAY_TOKEN` en este pack, así
que no se revirtió nada del env — la decisión queda pendiente.

> **Actualización (T6, §10): la opción (b) fue probada y NO funciona.**
> Ver §10. Quedan (a) y (c).

---

## 10. Agente liviano en el gateway — probado y descartado (PKG-MACRO-P5-L2-T6, 2026-08-13)

**Autorización citada de David:** "B — agregar en el gateway un agente
liviano solo para completions (toca `openclaw.json`; el default global de
`_default_model` puede quedar, pero ya no usa el turno completo de Rick).
Elegida 2026-08-13 post-T5." Restart de `openclaw-gateway` autorizado en
este pack (el único de L2 que lo autoriza), con backup + rollback.

**Resultado: `P5_L2_COMPLETIONS_AGENT = BLOCKED`.** El agente se creó y
funcionó — pero *no es liviano*, y no puede serlo: el costo no está en cómo
se configure el agente, está en el endpoint del gateway.

### 10.1 Qué se construyó

Alta vía el CLI documentado (`openclaw agents add completions
--non-interactive --workspace … --model openai/gpt-5.4-mini --json`), que
reportó `bindings.added: []` — **cero bindings de canal**. Workspace nuevo y
vacío (`~/.openclaw/workspaces/completions`), verificado antes del alta; no
se copió el de `main`. Endurecimiento posterior por patch JSON sobre el
mismo schema (`agents.list`):

| Requisito del pack | Cómo se cumplió |
|---|---|
| Sin bindings de canal | `Routing rules: 0` confirmado por `openclaw agents list` |
| Sin heartbeat autónomo | Sin clave `heartbeat`. **Verificado leyendo el runtime** (`isHeartbeatEnabledForAgent` + `hasExplicitHeartbeatAgents`): como ya hay agentes con heartbeat explícito, el heartbeat aplica *sólo* a esos — un agente sin la clave queda fuera. No es una suposición |
| `skipBootstrap` | El schema **no** lo permite per-agent (`additionalProperties: false`, lo rechazó el validador). `agents.defaults.skipBootstrap` ya es `true` → se hereda |
| Tools de exec/edit/write DENY | `profile: minimal` + `deny` de 13 grupos. El journal confirma **26 tools removidas**: `exec`, `edit`, `write`, `read`, `apply_patch`, `web_fetch`, `web_search`, `subagents`, `cron`, `message`, `nodes`, `image`, `tts`, … |
| Provider ya autenticado | `openai/gpt-5.4-mini` (el más liviano del provider `openai` que ya autentica el gateway). No se inventó ningún Anthropic |

Dos errores de schema los atrapó el **validador del propio runtime**
(`openclaw config validate`), no se adivinó nada: `subagents.maxSpawnDepth`
es sólo válido en `defaults` (reemplazado por `subagents.allowAgents: []`),
y `skipBootstrap` no es válido per-agent (removido).

### 10.2 Las sondas — 4 mediciones secuenciales, nunca concurrentes

| # | Config | Timeout | Resultado |
|---|---|---|---|
| S1 | runtime `codex` | 20s | HTTP 000 (timeout) — inconcluso, ¿cold start? |
| S2 | runtime `codex` | 60s | **HTTP 200 en 33.3s**, respuesta correcta. `prompt_tokens=12825` para un prompt de 5 palabras |
| S3 | runtime `openclaw` | 30s | HTTP 000. El journal revela la causa oculta: `[bundle-mcp] failed to start server "magnific" … timed out after 30000ms` |
| S4 | runtime `openclaw` + `deny: bundle-mcp` | 20s | HTTP 000, pero magnific ya no aparece en el journal (el deny per-agent funcionó). Server-side: `durationMs=32593` |

S2 ya cumple por sí sola el criterio BLOCKED que fijó el pack (30s+ **y**
10k+ tokens). S3 y S4 sirvieron para descartar la hipótesis de que la culpa
fuera del MCP.

**Magnific no se tocó** (prohibido): el fix de S4 fue denegar `bundle-mcp`
*a nivel del agente*, no deshabilitar el servidor MCP.

### 10.3 Diagnóstico: no es configurable

El costo no viene del modelo, ni del runtime, ni de las tools, ni de MCP:

- Modelo más liviano disponible (`gpt-5.4-mini`): no alcanza.
- Runtime `codex` (subproceso) **y** runtime interno `openclaw`: ambos ~32-33s.
- `profile: minimal` con 26 tools removidas: no alcanza.
- `bundle-mcp` denegado: elimina 30s de arranque de MCP y **aun así son ~32s**.

Es la maquinaria de **turno de agente** del gateway en sí (system prompt de
~12.8k tokens + orquestación) la que cuesta ~32s por llamada, se configure
como se configure el agente. El endpoint `/v1/chat/completions` del gateway
**no expone completions puras**: todo pasa por un turno de agente.

Comparación con T3 §7.3 (sonda a `openclaw/main`): 36s / 27.5k tokens →
ahora 33s / 12.8k tokens. Mejora del ~53% en tokens, pero **sigue siendo un
turno de agente**, no un completion.

### 10.4 Rollback y estado final

Por la regla del pack ("si 1-3 fallan, STOP y rollback json"):
`openclaw.json` restaurado desde el backup y gateway reiniciado.
Verificado: el archivo quedó **idéntico byte a byte** al backup pre-pack
(`diff` vacío), los 8 agentes originales intactos, `completions` ya no
existe, `openclaw config validate` → `Config valid`, y
gateway/worker/dispatcher los tres `active` con `NRestarts=0` (los restarts
fueron explícitos y limpios, no crash loops).

**Los pasos 4 y 5 no se ejecutaron** — la misión lo prohíbe explícitamente
cuando la sonda da BLOCKED ("no sigas al env"). En consecuencia:
`OPENCLAW_GATEWAY_AGENT` **sigue sin definirse** en el env del worker, el
default en `worker/tasks/llm.py` **sigue siendo `main`**, y
`umbral-worker`/`openclaw-dispatcher` no se reiniciaron en este pack
(conservan el `ActiveEnterTimestamp` de T5).

**Residuo conocido, no limpiado a propósito:**
`~/.openclaw/agents/completions/` (109 MB, incluye los transcripts de sesión
de las 4 sondas) y `~/.openclaw/workspaces/completions/` (vacío). Quedan
**inertes** — `openclaw.json` ya no los referencia. No se borraron porque
implicaría podar transcripts (prohibido en este pack) y es irreversible.
Comando documentado si David quiere limpiarlos:
`openclaw agents delete completions`.

### 10.5 Qué queda para decidir

La opción (b) de §9.4 está **empíricamente descartada**. Quedan:

- **(a)** Acotar el alcance de `_default_model()` a los casos explícitamente
  autorizados (por `task_type`/caller en vez de global), sacando del camino
  del gateway a `smart_reply` (Notion, David-facing), `daily_digest` y
  `composite.research_report`. Es un cambio de código acotado, testeable, y
  ataca directamente el riesgo de §9.4.
- **(c)** Aceptar conscientemente que esas tres rutas paguen el costo del
  turno de agente, con el riesgo de saturación del gateway compartido ya
  demostrado en §9.2. Ojo con el número: como el agente `completions` se
  revirtió (§10.4), esas rutas usarían `openclaw/main`, que se midió en
  **~36s y ~27.5k tokens** (§7.3) — no los ~33s/12.8k de la tabla de arriba,
  que son del agente que ya no existe.

Una tercera vía que este pack no exploró (fuera de su autorización): darle
al worker una API key propia de algún provider (`gemini`/`azure`) para
`llm.generate`, que no depende del gateway en absoluto — es la "vía B" que
§6 ya mencionaba como disponible e independiente de la capa 3.

Evidencia completa (4 sondas, journal, diff de keys sin secretos) en
`~/.coord-ag-evidence/pkg-macro-p5-l2-t6/`.

---

## 11. Recorte del default — cierre del riesgo de §9.4 (PKG-MACRO-P5-L2-T7, 2026-08-13)

**Autorización citada de David:** "A — acotar `_default_model()` por caller:
smart-reply, digest y composite NO van al gateway. El ruteo yaml del PR
puede quedar. Pack de recorte en #645 antes de mergear. Elegida 2026-08-13
post-T6 (B empíricamente descartada)."

**`P5_L2_DEFAULT_SCOPED = Y`.** El riesgo concreto que §9.4 marcó como
*urgente* — que `smart_reply` (Notion, David-facing), `daily_digest` y
`composite` se reenrutaran solos al gateway sin que nadie lo pidiera —
queda cerrado en código, con guards que se verificaron no-vacíos. El PR
#645 pasa a ser seguro de mergear. Lo que **no** cierra este pack (y no
pretendía): el camino encolado por el dispatcher, que sigue resolviendo a
`openclaw_proxy` para toda tarea LLM — ver §11.2, punto 2.

### 11.1 Seguridad live primero

Antes de tocar nada, el `umbral-worker` seguía corriendo en memoria el
código de T5 — es decir, con el default global todavía activo. Se
reiniciaron `umbral-worker` y `openclaw-dispatcher` **desde el checkout
`main`** (que no tiene `_default_model()`), para descargarlo del proceso
vivo antes de empezar. `ActiveEnterTimestamp` 18:00:32 → **22:07:31**;
`openclaw-gateway` **no se tocó** (sigue en 20:43:17, el restart de T6).

### 11.2 El recorte

`_default_model()` **eliminada**. `handle_llm_generate` vuelve al default
histórico:

```python
requested_model = str(
    input_data.get("model")
    or input_data.get("selected_model")
    or DEFAULT_MODEL          # Gemini — nunca el gateway
).strip()
```

`openclaw_proxy` se usa ahora sólo cuando alguien lo pide explícitamente
(un `model`/alias Claude u `openclaw_proxy`) o cuando el dispatcher inyecta
`selected_model` vía ModelRouter. Los tres callers que llegaban sin modelo
— `dispatcher/smart_reply.py::_do_llm_generate` (Notion, David-facing),
`scripts/daily_digest.py::generate_llm_summary` y
`worker/tasks/composite.py` (`_generate_queries` y
`_generate_report_with_retry`) — vuelven al camino Gemini-sin-modelo, que
es donde estaban antes de T5.

**Dos precisiones que el `/code-review` de este pack corrigió sobre el
borrador de esta misma sección** — ambas importan para decidir qué sigue:

1. **`composite` sí pasa por el ModelRouter.** `LLM_TASK_PREFIXES =
   ("llm.", "composite.")` (`dispatcher/service.py:61`), así que el
   dispatcher **sí** le inyecta `model` a `composite.research_report`. Lo
   que pasa es que `handle_composite_research_report` nunca lo lee y sus
   dos sub-llamadas arman payloads nuevos sin modelo: **pasa por el router
   y descarta la decisión**. Eso es pre-existente (está igual en `main`,
   T5 sólo lo enmascaraba) y el recorte lo restaura tal cual — pero no es
   cierto, como decía el borrador, que "no pase por el router".
2. **El recorte cierra las rutas directas, no la encolada.** Con
   `openclaw_proxy` como **único** provider configurado y presente en las
   7 `fallback_chain` (cambio del PR que se conserva), **toda** tarea
   `llm.*`/`composite.*` encolada sigue resolviendo a `openclaw_proxy` —
   no sólo R8 `coding`/`research`. Verificado en el env vivo:

   ```
   configured: ['openclaw_proxy']
   coding/critical/general/light/ms_stack/research/writing -> ['openclaw_proxy']
   ```

   O sea: el riesgo de §9.4 (los tres callers directos, incluido el
   David-facing) **queda cerrado**; el camino encolado por el dispatcher
   **no**, y sigue apuntando al mismo gateway de §9.2. No es una regresión
   de este pack (es el estado de `main` + el ruteo yaml que David pidió
   conservar), pero conviene tenerlo explícito antes de mergear.

**Se conservó todo lo demás del PR** (nada de esto dependía del default
global): los `fallback_chain` de `quota_policy.yaml`, el fix del payload
`openclaw/<agent>`, `MODEL_ALIASES["openclaw_proxy"]`, los mapas
sincronizados de `worker/app.py`, y el fixture de fuga de env en
`conftest.py`. `_claude_disabled()` sigue en uso desde `_detect_provider`
(no quedó código muerto).

### 11.3 Tests

- `test_handle_llm_generate_defaults_to_openclaw_proxy_with_token` (que
  afirmaba el comportamiento ahora recortado) → reescrito como
  **`test_handle_llm_generate_without_model_never_uses_gateway`**: con el
  token presente y sin `model`, no sólo espera el error de Gemini —
  además exige `mock_urlopen.assert_not_called()`, o sea que **no se abrió
  ninguna conexión** al gateway.
- Nuevo **`test_handle_llm_generate_selected_model_openclaw_proxy_uses_gateway`**:
  la contrapartida, `selected_model="openclaw_proxy"` sí llega al gateway.
- Nueva clase **`TestDefaultScopedAwayFromGateway`** (5 tests) que se ata a
  los callers **reales**, no a literales copiados a mano — esto también salió
  del `/code-review`, que detectó que el borrador afirmaba "callers reales"
  cuando dos de los tres eran un dict escrito en el test:
  - `composite`: usa el propio `_build_report_generation_payload()` y, aparte,
    ejercita `_generate_queries()` (que arma su payload inline y no tenía
    guardia), ambos con `urlopen.assert_not_called()`.
  - `smart_reply` y `daily_digest`: invocan las funciones de producción
    (`_do_llm_generate`, `generate_llm_summary`) con un `WorkerClient`
    mockeado y afirman sobre el payload **que ellas realmente construyen**.
    Si alguien le agrega un `model` a cualquiera de las dos, el test falla.
  - La guardia estructural sobre el payload de composite se acotó: no
    prohíbe `selected_model` en general (composite sí está ruteado y algún
    día podría legítimamente reenviarlo), sino hardcodear un modelo de
    gateway/Claude.

**Verificación de que los guards no son vacíos:** se revirtió el recorte a
mano y se corrió la suite — 3 de los tests nuevos **fallan** con el recorte
revertido y pasan con él aplicado. Además `UMBRAL_DISABLE_CLAUDE` se fija
explícito en los tests de `test_llm_handler.py` (si llegara truthy, el guard
pasaría por el motivo equivocado).

`pytest tests/`: **4796 passed**, 6 skipped, 2 xfailed. Mismos 3 fallos
pre-existentes de `test_pit_*` deseleccionados (`pydantic` faltante en un
subproceso, ajenos a este pack).

**Cero sondas al gateway y cero e2e en este pack**, por instrucción
explícita — el e2e completo fue justamente lo que lo tumbó en §9.2.

### 11.4 Estado de las capas

| # | Capa | Estado |
|---|---|---|
| 1 | Credenciales de provider ausentes en el worker (§2.1) | **abierta** |
| 2 | `UMBRAL_DISABLE_CLAUDE` (§2.2) | cerrada en T4 (`false`) |
| 3 | Login OpenAI del gateway (§6) | cerrada en T3 |
| — | Reruteo silencioso al gateway, **rutas directas** (§9.4) | **cerrada acá** |
| — | Camino **encolado** por el dispatcher → gateway | **abierta** (ver §11.2, punto 2) |

Los 4 tests del e2e **siguen fallando**. Este pack no los arregla — saca a
los tres callers directos del camino peligroso. Matiz sobre la causa, que
el `/code-review` precisó: no es sólo "capa 1". Para `llm.generate` suelto
sí (no hay credencial propia). Para `composite.research_report` hay algo
más: el router **sí** elige un provider configurado (`openclaw_proxy`) y
composite **descarta** esa decisión, así que cae en Gemini y muere por
`GOOGLE_API_KEY not configured`. Cargar una key de Gemini lo taparía sin
arreglar el descarte.

La vía que arreglaría los 4 sin depender del gateway sigue siendo la "vía
B" de §6/§10.5: una API key propia (`gemini`/`azure`) para el worker.

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t7/`.

> **Actualización (T8, §12): David eligió lo contrario a la "vía B".** El
> texto va por OAuth de ChatGPT vía gateway, **sin Gemini**. §11 se revierte
> en su parte de default; lo demás (timeouts, guards de callers) se conserva
> y se amplía. Ver §12.

---

## 12. El texto va por OAuth de ChatGPT — default al proxy + timeouts (PKG-MACRO-P5-L2-T8, 2026-08-14)

**Autorización citada de David:** "ChatGPT OAuth vía gateway por ahora. Subir
timeouts. Sin Gemini. Azure Foundry más adelante SOLO si hay mucha
concurrencia; preferencia = quedarse en OAuth. Imagen = Magnific MCP."
(2026-08-14)

**`P5_L2_CHATGPT_OAUTH = Y`** para el texto en general — **`llm.generate` y
las dos rutas R8 andan por OAuth vía gateway**, que es exactamente lo pedido.
`composite.research_report` queda **BLOCKED por capacidad**.

> ⚠️ **Con una advertencia que no se puede leer por encima:** durante la
> verificación live el gateway compartido **murió por OOM** (3.5 GB, restart
> automático de systemd) por el loop de redespacho de `composite`, no por las
> tres pruebas que pasan. Se recuperó solo y quedó `active`. Ver §12.4 y
> §12.5 antes de habilitar `composite.research_report` en cron o en cualquier
> ruta automática.

### 12.1 Qué cambió

| Cambio | Detalle |
|---|---|
| Default al proxy | `_default_model()` vuelve, pero ahora devuelve el alias `openclaw_proxy`. Sin `model` ni `selected_model` → gateway. |
| **Sin fallback mudo a Gemini** | Si falta `OPENCLAW_GATEWAY_TOKEN` (o `UMBRAL_DISABLE_CLAUDE` está activo), **no** se cae a Gemini: se lanza un error que nombra lo que falta. Un fallback silencioso mandaría tráfico a un provider que David descartó y el síntoma aparecería como `GOOGLE_API_KEY not configured`, que apunta al lugar equivocado. |
| Timeouts ≥ 90s | e2e `llm.generate` 25s → **120s**; poll de `_enqueue_and_wait` 15×1s → **60×2s**; poll de composite 20×1.5s → **90×2s**; `smart_reply._LLM_TIMEOUT` 20s → **120s**; `daily_digest` 30s (default) → **120s**; R8 Claude/anthropic 30s → **120s**; `urlopen` del proxy 90s → **105s** (subido, nunca bajado — y a propósito *por debajo* de los 120s de los callers, ver §12.6). |
| `_LLM_TIMEOUT` **no se usaba** | Hallazgo lateral: la constante existía en `smart_reply.py` pero no se pasaba a `wc.run()`, así que el timeout real era el default de `WorkerClient` (30s). Ahora se pasa de verdad. |
| Retries acotados | Los dos tests e2e que pegan al gateway pasan `retries=0`. Con el default (2), un timeout disparaba 3 turnos de agente de 120s sobre el mismo gateway (363s, hasta 3 vivos a la vez) — la ráfaga de §9.2. |
| composite honra el ruteo | `handle_composite_research_report` propaga `model`/`selected_model` (vía `_ACTIVE_CONTEXT`, igual que la metadata de tracing) a sus dos sub-llamadas. Cierra el descarte que §11.2 documentó. |

`DEFAULT_MODEL` (Gemini) queda como constante para quien pida Gemini
explícitamente; ya no es el default de nadie.

### 12.2 Etiqueta vs realidad — importante

El worker reporta `provider="openclaw_proxy"` y `model="claude-sonnet-4-6"`,
pero **el modelo real lo elige el gateway**, no este código. Hoy el agente
`main` del gateway tiene `model.primary = openai/gpt-5.6-sol` y **cero
proveedores Anthropic** (§9.4). O sea: la respuesta la genera GPT vía la
sesión OAuth de ChatGPT — que es justamente lo que David pidió — pero la
etiqueta dice Claude. No es un bug introducido acá; es la consecuencia de
usar `openclaw_proxy` como puente y ya estaba señalado en §9.4. Vale
tenerlo presente al leer `ops_log`/`trace_llm_call`.

### 12.3 Tests

`pytest tests/`: **4799 passed**, 6 skipped, 2 xfailed (mismos 3 fallos
pre-existentes de `test_pit_*` deseleccionados). Los guards de T7 se
invirtieron a propósito, porque la orden cambió:

- `test_handle_llm_generate_without_model_uses_the_proxy` — con token y sin
  modelo, **sí** va al proxy (invierte el guard de T7).
- `test_handle_llm_generate_without_token_fails_asking_for_the_proxy` y
  `..._claude_disabled_fails_without_falling_back` — sin token / con el flag
  activo, falla nombrando lo que falta y **no** abre conexión a Gemini.
- `test_no_gemini_call_when_token_present` — guard explícito de "sin
  Gemini": aun con `GOOGLE_API_KEY` presente, la URL de salida es el gateway
  y nunca `googleapis.com`.
- `test_composite_honours_dispatcher_routed_model` — el passthrough nuevo.

### 12.4 Las 4 pruebas live (de a una, pausa ≥10s, nunca el e2e completo)

| # | Prueba | Resultado | Latencia |
|---|---|---|---|
| 1 | `llm.generate` | **PASS** — `provider=openclaw_proxy`, 169 chars, 27.330 prompt tokens | **35.2s** |
| 2 | `composite.research_report` | **FAIL** (capacidad) | no converge |
| 3 | R8 routing `coding` | **PASS** — `status=done` | **53.7s** |
| 4 | R8 routing `research` | **PASS** — `status=done` | **38.6s** |

Los tres que pasan confirman la medición de §7.3: ~35-54s por turno de
agente, ~27k tokens de prompt. Antes de este pack morían por timeout a los
20/25/30s.

**Corrección importante — el gateway SÍ se cayó, por OOM.** Un borrador de
esta sección decía "el gateway aguantó, `NRestarts=0` sin cambio de principio
a fin". **Eso era falso**, y el error fue mío: verifiqué `NRestarts` *antes*
del evento, no al final. Lo que pasó de verdad:

```
02:02:25  composite encolado; arranca el loop de redespacho (~cada 2 min)
02:02–02:18  8 redespachos, cada uno abriendo turnos de agente en el gateway
02:18:50  systemd: "A process of this unit has been killed by the OOM killer"
          "Failed with result 'oom-kill'" — 3.5G memory peak, 25min 44s CPU
02:18:58  systemd: "Scheduled restart job, restart counter is at 1"
02:19:0x  gateway arranca de nuevo solo y recupera (active, MainPID nuevo)
```

Estado final verificado: `openclaw-gateway` **active**, `NRestarts=1`,
`MainPID=3436104` — se recuperó solo, sin intervención. Las tres latencias
que pasan se midieron **antes** del OOM, así que esos resultados siguen
siendo válidos.

Lo que esto cambia en la conclusión: el pile-up de composite (§12.5) no es
sólo desperdicio de tiempo — **agotó la memoria del gateway compartido y lo
mató**. Es el mismo final que §9.2, por otro camino: allá fue una ráfaga
concurrente del e2e completo, acá fue un loop de redespacho sostenido de una
sola tarea. Las pausas y el "de a una" evitaron el crash *de las tres pruebas
que pasan*, pero no alcanzan si una tarea puede reencolarse sola para
siempre.

### 12.5 Por qué composite no pasa, y el agravante que apareció

No es auth, ni ruteo, ni config: **una sola llamada suya excede los 120s**.
El journal del gateway marca `durationMs=119867 / 119877 / 119881` — agota
exactamente el timeout que subí. El prompt de generación de reporte lleva
todo el `research_data` + `max_tokens=4096`, y ese turno de agente tarda más
que eso.

**Agravante encontrado (no lo causa este pack):** el dispatcher **redespacha
la misma tarea cada ~2 min** (02:02:25, 02:04:27, 02:06:28, 02:08:28…).
Cada redespacho arranca un composite nuevo que vuelve a pegarle al gateway:
la tarea nunca termina y el gateway recibe tráfico sin fin. Se cortó
reiniciando worker+dispatcher al cerrar el pack.

Por eso **subir más el timeout no es la respuesta obvia**: si el timeout
supera la ventana de redespacho (~2 min), se garantiza pile-up — varias
corridas de la misma tarea vivas a la vez contra el mismo gateway, que es
la receta de §9.2. Opciones reales para composite, en orden de menor a
mayor cambio:

1. **Achicar el turno**: bajar `max_tokens` del reporte y/o recortar el
   `research_data` que se le manda, para que la llamada entre en la ventana.
2. **Alinear redespacho y timeout**: subir la ventana de redespacho del
   dispatcher por encima del timeout, para que no haya dos corridas vivas.
3. **Streaming o partición**: generar el reporte por secciones (varias
   llamadas cortas) en vez de una sola larga.
4. Azure Foundry para esta tarea puntual — pero David dijo *sólo si hay
   mucha concurrencia*, y esto es latencia de una llamada, no concurrencia.

### 12.6 Lo que encontró el `/code-review` (y una advertencia sobre el review mismo)

**Aviso de honestidad sobre el review:** corrió *parcial*. 12 de 20 agentes
murieron con `529 Overloaded` (falla del lado del servidor, no del diff), así
que de 5 ángulos sólo 2 quedaron completamente verificados
(default-correctness y timeout-coherence). Los ángulos de tests, del
passthrough de composite y de exactitud del acta **no** llegaron a correr.
Lo que sí corrió encontró dos cosas reales, ya corregidas:

1. **`scripts/daily_digest.py` se me había quedado afuera.** Construye su
   `WorkerClient()` con el default de **30s** y llama `llm.generate` sin
   modelo — o sea que con el default nuevo (proxy, ~35s) el digest habría
   expirado **siempre**, y con `retries=2` habría dejado **3 turnos de agente
   huérfanos** corriendo en el gateway por cada corrida. Subí timeouts en
   `e2e_validation.py` y `smart_reply.py` y me salté este caller, que es
   justamente uno de los tres que §9.4 había señalado. Corregido: pasa
   `timeout=120s`.
2. **Multiplicación por retries.** `_request_json` en el e2e trae
   `retries=2` por default: 120s × 3 = 363s y hasta 3 turnos vivos en
   paralelo (el worker **no** cancela el hilo del handler cuando el cliente
   se desconecta — usa `run_in_executor`). Eso fabrica exactamente la ráfaga
   de §9.2. Corregido con `retries=0` en los dos tests que pegan al gateway.
3. **Margen interno/externo.** Había puesto el `urlopen` del proxy en 120s,
   *igual* que todos los callers — con lo cual el caller siempre gana la
   carrera, el worker nunca alcanza a devolver su propio error descriptivo, y
   el turno queda huérfano. Corregido a **105s**: sigue arriba de los 90s
   originales (nunca se bajó) pero ahora deja margen, así el error sale del
   worker con causa clara dentro de la ventana del caller.

El review también señaló, y vale registrarlo aunque no se toca acá: una sola
expiración del lado del caller puede costar hasta **9 turnos** de gateway,
porque se multiplican `WorkerClient.retries=2` × el re-enqueue del dispatcher
(`service.py`, `retry_count < 2`). Es la misma familia de problema que el
pile-up de §12.5 y conviene atacarlo junto con eso.

Evidencia (journal, latencias, sin secretos) en
`~/.coord-ag-evidence/pkg-macro-p5-l2-t8/`.

---

## 13. SHRINK de composite — el gateway sobrevive, la latencia no baja lo suficiente (PKG-MACRO-P5-L2-T9, 2026-08-14)

**Autorización citada de David:** "SHRINK — achicar el turno de composite:
bajar `max_tokens` (hoy 4096) y recortar `research_data`. Una sola llamada,
más barata. No partir en N llamadas. No Azure. Composite NO a cron hasta que
esto pase." (2026-08-14)

**`P5_L2_COMPOSITE_SHRUNK = BLOCKED`.** El modo de fallo mejoró mucho — el
gateway **sobrevivió** esta vez — pero el objetivo de latencia (<90s) **no se
alcanzó**: el turno sigue por encima de 105s. Composite queda **sin habilitar
en cron**, como pidió David.

### 13.1 Los números salieron de medir, no de estimar

Antes de tocar nada se midió el `research_data` real corriendo `_do_research`
+ `_format_research_data` con el mismo shape del e2e:

| depth | queries × resultados | fuentes | chars | ≈ tokens |
|---|---|---|---|---|
| `quick` | 3 × 5 | 15 | **9.945** | ~2.5k |
| `standard` | 5 × 5 | 25 | ~16.5k | ~4k |
| `deep` | 10 × 5 | 50 | ~33k | ~8k |

(Los snippets vienen capados a 500 chars por el buscador, así que el tamaño
escala casi lineal con la cantidad de fuentes.)

Y de §12.4: `llm.generate` con `max_tokens=100` generó 34 tokens en **35.2s**.
O sea que **~35s es overhead fijo** del turno de agente (setup + los ~27k
tokens de prompt que el propio agente arrastra), no generación. El que
empujaba el reporte por encima de 119s era el `max_tokens=4096`.

### 13.2 Qué se cambió

| Constante | Antes | Ahora | Por qué |
|---|---|---|---|
| `REPORT_MAX_TOKENS` | 4096 | **1000** | El lever principal: ~4000 tokens de salida eran el grueso del turno |
| `REPORT_RESEARCH_DATA_MAX_CHARS` | (no existía) | **12.000** | `quick` (9.945) entra completo; acota `standard` y `deep` — ver la advertencia de §13.5 |
| `REPORT_GENERATION_MAX_ATTEMPTS` | 3 | **1** | El reintento era el multiplicador que llevó al OOM: cada intento abría un turno nuevo de >119s |

El truncado corta en el salto de línea previo, para no partir una fuente por
la mitad y dejar una URL colgada.

### 13.3 Live: una sola corrida, con el gateway vigilado

`task_id=2e54f1a5…`, `topic` corto, `depth=quick`. Baseline del gateway:
`MainPID=3436104`, `NRestarts=1`, RSS 653 MB.

**Lo que mejoró — y es mucho:**

| | T8 (antes) | T9 (ahora) |
|---|---|---|
| Intentos de reporte | 3 (retry storm) | **1** — el journal muestra una sola línea de fallo |
| RSS pico del gateway | **3.5 GB** → OOM | **1.003 MB** (~3.5× menos) |
| Gateway | **murió** (OOM 02:18:50, `NRestarts` 0→1) | **sobrevivió**: `NRestarts=1` y `MainPID` **sin cambio** |

**Lo que no mejoró:**

- El turno de reporte **sigue excediendo los 105s**. Journal del gateway:
  `durationMs=104847`. Worker: `LLM report generation failed: OpenClaw proxy
  request failed: timed out`.
- **Cuidado con leer mal ese número**: 104.8s no es lo que tarda el turno —
  es donde lo **cortó** mi `urlopen` de 105s. La duración real es >105s,
  desconocida.
- **La truncación no se activó**: `quick` son 9.945 chars y el cap es 12.000.
  Para `quick`, el único lever activo fue `max_tokens`, y bajarlo de 4096 a
  1000 **no alcanzó**. El cap sólo protege a `standard`/`deep`.
- El **redespacho del dispatcher sigue**: composite se ejecutó 2 veces en 8
  min. No se tocó (no estaba autorizado) y sigue siendo un amplificador.

Por el criterio de STOP del propio pack (`durationMs ≥ 100s`) se cortó ahí:
no se reintentó y **no se corrieron las otras 3 pruebas**.

### 13.4 Qué haría falta para el próximo intento

Con overhead fijo ~35s y el turno todavía >105s con `max_tokens=1000`, la
generación de ≤1000 tokens está costando >70s → **<14 tokens/s**. Para entrar
en 90s haría falta del orden de **700 tokens** de salida.

**Pero eso es extrapolación de un turno que fue cortado, no medido hasta el
final.** Antes de volver a bajar el número a ojo conviene **medir una corrida
sin corte** (timeout alto, una sola, fuera de horario) para conocer la tasa
real de generación. Sin ese dato, bajar a 700-800 es otra apuesta — y ya
llevamos dos.

### 13.5 Lo que corrigió el `/code-review` (dos cosas mías)

**1. El cap recorta el depth por *defecto*, no sólo los grandes.** Justifiqué
el número 12.000 diciendo que `quick` entra completo "porque es la forma que
corre el e2e" — y me quedé ahí. Pero el default del task es
`standard` (`depth = input_data.get("depth", "standard")`), y **standard sí se
recorta**. Medido:

| depth | fuentes | chars | líneas que ve el modelo |
|---|---|---|---|
| `quick` | 15 | 8.699 | **15/15** (intacto) |
| `standard` (**default**) | 25 | 14.499 | **20/25** |
| `deep` | 50 | 28.999 | **20/50** |

Peor: `sources` y `stats.total_sources` se calculan sobre los datos **sin**
recortar, así que el sobre decía `total_sources: 25` al lado de un reporte
escrito con 20 fuentes — y el prompt le pide al modelo citar fuentes inline,
o sea que sólo puede citar las que vio. `scripts/sim_to_make.py` reenvía ese
`sources_count` a Make tal cual.

Corregido con lo más barato que es honesto: `stats.sources_sent_to_model`,
que dice cuántas fuentes llegaron **de verdad** al modelo. No se cambió el
cap ni el contrato — sólo se dejó de afirmar algo que no era cierto.

**2. Uno de mis tests nuevos no probaba nada.** El que decía verificar que el
recorte no parte una línea afirmaba
`body.endswith("\n") or body.endswith("s")` sobre datos hechos de líneas de
"s": pasaba **igual con la heurística de corte desactivada**. Lo verifiqué
mutando el código y confirmando que seguía en verde. Reescrito para afirmar
la propiedad real (toda línea que sobrevive está entera) y **re-verificado
por mutación**: ahora falla si se saca la heurística. Se agregó además el
caso sin saltos de línea, que antes no estaba cubierto.

`pytest tests/`: **4805 passed**, 6 skipped, 2 xfailed.

### 13.6 Qué haría falta para el próximo intento

Vale decirlo claro: **el problema de fondo no es el tamaño del pedido, es que
el endpoint del gateway no es un completion sino un turno de agente** con
~35s de piso y ~14 tok/s de techo. Un reporte de 4 secciones con citas no
entra cómodo en ese presupuesto. Las salidas reales, en orden de honestidad:

1. **Aceptar un reporte más corto** (~700 tokens ≈ 500 palabras) y verificar
   que el resultado le sirva a David. Es la continuación directa del SHRINK.
2. **Aceptar que composite tarde ~2 min** y arreglar la ventana de redespacho
   del dispatcher para que no apile — o sea, atacar el amplificador en vez de
   la latencia.
3. Revisar por qué el agente del gateway arrastra ~27k tokens de prompt en
   cada turno: si eso bajara, baja el piso de 35s para **todo** el stack, no
   sólo composite.

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t9/`.

---

## 14. WINDOW — se midió cuánto tarda de verdad y se ensanchó la ventana (PKG-MACRO-P5-L2-T10, 2026-08-14)

**GO citado de David (2026-08-14):** WINDOW. No bajar más `max_tokens`. No
partir el reporte en N llamadas. No Azure. No Gemini. Composite **NO** a cron.

Los packs T8 y T9 dimensionaron a ojo y erraron dos veces. Este empieza al
revés: **primero medir, después fijar constantes.**

### 14.1 FASE 0 — la corrida sin corte `[E]`

Método: `POST` directo al worker (**no** por la cola, para que el redespacho
no contaminara la medida), una sola llamada, sin retries, y el `urlopen` del
proxy subido **temporalmente** a 300s para que nada truncara el número.
Gateway **no** tocado.

| Métrica | Valor |
|---|---|
| HTTP | **200** — el reporte se generó **completo** |
| `generation_time_ms` (turno de reporte) | **158.171 s** |
| `research_time_ms` | 8.028 s |
| wall del task (curl) | **205.6 s** |
| reporte | **21.462 chars**, 4 secciones |
| `total_sources` / `sources_sent_to_model` | 15 / 15 (`quick` no se trunca: consistente) |
| `report_generation_attempts` | 1 |
| RSS pico del gateway | 1.467 MB (STOP estaba en 2 GB) |
| `MainPID` / `NRestarts` | 3436104 / 1 — **sin cambio** |

**Es término, no corte.** En T9 el `104847` era el timeout de 105s cortando;
este **158.2 s** es la duración de verdad. Ese es el dato que faltaba.

> Nota de método: el journal del gateway sólo emite `durationMs` en líneas de
> `lane task error`. Como este turno **terminó bien**, no dejó ninguna. Las
> entradas de esa ventana (`durationMs=63092/13155`, error "Bad Request") son
> de `lane=session:agent:rick-delivery:main` — **tráfico ajeno**, de otro
> agente. Por eso el oráculo acá es el del worker, no el journal.

### 14.2 FASE 1 — la aritmética, y dónde me aparté de la instrucción

La instrucción decía `T = durationMs_real/1000 + 30`. Con el turno de reporte
(158.2) eso da **188 s** — y el task completo tarda **205.6 s**, así que 188
lo **cortaría**. El dispatcher espera la **tarea entera**, no sólo el turno.
Así que dimensioné con el wall:

Primera versión (la que el `/code-review` tumbó, ver §14.5):

```
205.6 s + 30 s = 235.6  →  T_dispatcher = 240 s
240 − 15                →  T_proxy      = 225 s     ← MAL
```

**Versión final**, con la cuenta correcta: el urlopen del reporte **no arranca
en t=0**, arranca después del preámbulo. Lo que hay que acotar es la *suma*:

```
ventana del dispatcher                       = 300 s  (techo autorizado)
techo query-gen  (medido 39.4 s)             =  90 s
techo reporte    (medido 158.2 s)            = 190 s
peor caso encadenado: 90 + 190               = 280 s  <  300 ✓
```

Y para que la invariante valga **siempre** —no sólo en el caso típico— el
reporte no usa un techo fijo sino **lo que queda del presupuesto**: el
dispatcher inyecta su ventana en `_task_timeout_s` y composite reparte. Si ya
no queda tiempo, **no arranca el turno** y falla rápido al reporte degradado,
en vez de dejar un huérfano corriendo en el gateway.

| | valor | debe ser < | ✓ |
|---|---|---|---|
| turno real medido | 158.2 s | techo reporte 190 s | ✓ |
| query-gen medido | 39.4 s | techo query-gen 90 s | ✓ |
| **peor caso encadenado** | **280 s** | **dispatcher 300 s** | ✓ |
| wall real medido | 205.6 s | dispatcher 300 s | ✓ |
| proxy default | 105 s | caller normal 120 s | ✓ |

**El timeout del proxy quedó por llamada, no global** — y acá también me
aparté de la letra ("subirlo a `T_proxy`", en singular). Subir el global
habría dejado a `smart_reply`/`daily_digest` (120 s) **cortando antes que el
proxy**, que es exactamente el anti-patrón que §12 arregló. Entonces:
`PROXY_DEFAULT_TIMEOUT_S = 105` para todos, y composite manda su propio
`_proxy_timeout_s`. Mismo espíritu (que no corte), sin romper la invariante
para los demás.

### 14.3 Los dos multiplicadores, cerrados

| Multiplicador | Antes | Ahora |
|---|---|---|
| Retries HTTP del `WorkerClient` | 2 → hasta 3 intentos de ~3.5 min c/u | **`retries=0`** sólo para `composite.*` (`run()` ganó override por llamada; los defaults de ping/notion **no** se tocan) |
| Re-encolado del dispatcher por timeout | hasta 2 re-encolas, cada una abriendo turnos nuevos | **no se re-encola** en timeout de `composite.*`. `ConnectError` **sí** sigue reintentando: worker caído ≠ LLM lento |

También se corrigieron dos comentarios que habían quedado viejos: el de
`service.py` decía "composite tarda 30-60s" (son ~205 s) y el de `composite.py`
esperaba "~50-70s" tras el SHRINK (son ~158 s).

### 14.4 Tests `[E]`

`pytest tests/`: **4815 passed**, 6 skipped, 2 xfailed. Deselect de los 3
`test_pit_*` pre-existentes (`ModuleNotFoundError: pydantic` en un subproceso,
ajenos a este pack y rojos también en `main`).

Siete tests nuevos en `test_dispatcher_resilience.py` + tres en
`test_openclaw_proxy.py`. Los 24 tests de resiliencia previos siguen verdes
(el cambio no toca al resto de las tareas, y hay un test que lo fija).

**Verificados por mutación** (lección de §13.5, donde un test mío no probaba
nada):
- revertir el no-reenqueue → fallan `test_composite_timeout_does_not_reenqueue`
  y `test_composite_write_timeout_does_not_reenqueue`;
- sacar el override de ventana → falla
  `test_composite_uses_its_own_timeout_and_zero_retries`.

### 14.5 Lo que encontró el `/code-review` — y por qué importa

Dos hallazgos CONFIRMED, los dos míos, los dos corregidos en este mismo PR.

**1. Mi invariante estaba mal planteada.** Yo comparaba
`timeout_del_reporte < ventana_del_dispatcher` (225 < 240) y lo daba por bueno.
Pero el urlopen del reporte **arranca después del preámbulo**, no en t=0:

| caso | cuenta | vs ventana 240 s |
|---|---|---|
| típico | 47.4 (preámbulo medido) + 225 = **272.4 s** | **desborda +32.4 s** |
| peor | 105 (query-gen sin acotar) + 8 + 225 = **338 s** | **desborda +98 s** |

Ese desborde es precisamente el modo de fallo que este pack viene a matar: el
dispatcher se rinde, pero el hilo del worker **no se cancela**
(`run_in_executor`), así que el turno sigue vivo en el gateway. Un huérfano
más, del mismo tipo que llevó al OOM de §12.4.

Y lo peor: **mi test pasaba igual**, porque afirmaba sólo `225 < 240`. Falsa
confianza — la misma clase de defecto que §13.5. Corregido en tres frentes:
ventana a 300 s, techos que suman 280 s, presupuesto dinámico, y un test que
ahora fija **la suma del peor caso** (verificado por mutación: con los
valores viejos, falla).

**2. El e2e se rendía antes que el runtime.** `test_composite_research`
poleaba 90 × 2 s = **180 s**, por debajo de los 205.6 s que yo mismo acababa
de medir. O sea: el WINDOW podía funcionar y el e2e lo iba a reportar como
FAIL, y el reflejo natural habría sido ensanchar el runtime para perseguir un
deadline que vivía en el test. Subido a 170 × 2 s = 340 s (> la ventana del
dispatcher, que es contra lo que hay que dimensionar, no contra el wall
medido). Hay un test que ata las dos cosas.

### 14.6 Live de verificación — por el dispatcher, que es donde dolía `[E]`

Una sola corrida, **encolada** (no POST directo), después del código:

| | valor |
|---|---|
| `status` | **done** — wall 201.1 s, reporte de **18.467 chars** |
| `generation_time_ms` | 154.191 s |
| `report_generation_attempts` | 1 |
| **ejecuciones de composite** | **1** (en T8 fueron 8: el pile-up) |
| **re-encolas por timeout** | **0** |
| gateway `MainPID` / `NRestarts` | 3436104 / 1 — **sin cambio** |
| RSS pico | 748 MB (vs 3.5 GB del OOM de §12.4) |

Consistente con FASE 0 (205.6 s directo vs 201.1 s encolado): el camino por
la cola no agrega costo material.

**La latencia sigue en ~200 s, y en este pack eso es aceptable** — no era el
gate. Lo que cambió es que ahora **termina** en vez de expirar y apilarse.

### 14.7 Estado

**`P5_L2_COMPOSITE_WINDOW = Y`.** Los dos multiplicadores cerrados, la
escalera de timeouts correcta (y verificada por mutación), el presupuesto
acotado por construcción, y una corrida encolada que termina con el gateway
intacto.

Sigue en pie lo de siempre: **composite NO va a cron**. Que una corrida
aislada funcione no dice nada sobre varias en paralelo, y el gateway sigue
siendo compartido y con historial de OOM.

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t10/`.

---

## 15. CLOSEOUT — los 4 tests sobre main, y un desajuste que llevaba 5 meses escondido (PKG-MACRO-P5-L2-T11, 2026-08-14)

**GO citado de David (2026-08-14):** CLOSEOUT secuencial. No concurrencia. No
atacar el piso de ~27k tokens. Composite **NO** a cron. No Gemini. No Azure.

Este pack no cambia código: corre los 4 tests originales de §1 **uno a uno**
sobre `main` con el WINDOW ya mergeado, y sella el resultado.

**`P5_L2_E2E = BLOCKED`** — pero por una capa que no es ninguna de las que
veníamos persiguiendo. **El runtime pasó los cuatro.** Lo que falla es la
aserción de dos tests.

### 15.1 Resultados

| # | Test | Resultado | Elapsed | RSS pico | ΔNRestarts |
|---|---|---|---|---|---|
| a | `test_llm_generate` | **PASS** | 35.3 s | 905 MB | 0 |
| b | `test_routing_coding_selects_claude` | **FAIL\*** | 36.6 s | 906 MB | 0 |
| c | `test_routing_research_selects_gemini` | **FAIL\*** | 39.2 s | 924 MB | 0 |
| d | `test_composite_research` | **PASS** | 206.6 s | 941 MB | 0 |

**\* FAIL de aserción, no de runtime.**

Método: las 4 funciones llamadas **una a una** (nunca `run_e2e_suite`, que
dispara `notion.add_comment` y providers Gemini/Claude/Vertex), pausa ≥12 s
entre cada una, RSS muestreado cada 5 s. `worker`+`dispatcher` reiniciados
desde el tip; gateway **no** tocado.

### 15.2 composite: el WINDOW se sostiene

| | |
|---|---|
| `status` | **done**, 206.6 s |
| **ejecuciones** | **1** |
| **re-encolas** | **0** |
| reporte real | **19.459 chars** |
| `stats` | `total_sources=15`, `sources_sent_to_model=15`, `research_time_ms=7279`, `generation_time_ms=160966`, `report_generation_attempts=1` |

Consistente con T10 (201.1 s / 18.467 chars). El pile-up no volvió.

### 15.3 Por qué fallan b y c — con la evidencia al lado

El runtime hizo **exactamente lo que el test esperaba**. Leído del status de
cada tarea:

| test | task | status | `model` real | `provider` |
|---|---|---|---|---|
| b | `bb6bfa6e…` | done | `anthropic/claude-sonnet-4-6` | `openclaw_proxy` |
| c | `be414971…` | done | `anthropic/claude-sonnet-4-6` | `openclaw_proxy` |

…que es literalmente el `effective_model` contra el que comparan. El problema
es de **shape**: los dos endpoints no devuelven lo mismo.

```
POST /run              → {ok, task, result: {text, model, provider, usage}}
GET  /task/<id>/status → {status, result: {ok, task, result: {text, model, …}}}
```

El status **envuelve el sobre completo** del worker, así que el modelo vive en
`result.result.model`. El test lee `status_data["result"]["model"]` → `None`
→ `"?"` → `ValueError: Expected …, got=?`.

El mismo desajuste está en composite: lee `result["report"]` (0 chars) cuando
el reporte real está en `result.result.report` (19.459 chars). Ahí **no** rompe
el test —sólo chequea `status == "done"`— pero el `detail` que imprime
("reporte 0 chars") es engañoso.

### 15.4 De cuándo viene: no es de esta cadena

`git log -S` sobre esas líneas apunta a **`a5cd0d0`, 2026-03-22** — casi cinco
meses antes de T1. Está presente en `98d9a954`, el commit base de toda la
cadena P5-L2 (4 ocurrencias). **No lo introdujeron T8, T9 ni T10.**

> **Matiz sobre mis propios reportes previos:** en §12.4 di R8 coding y R8
> research como PASS. Los corrí con `curl` verificando `status=done` —
> **no ejercité la aserción del test**. Este pack corre las funciones reales
> por primera vez, y ahí apareció. Los PASS de §12.4 describen el runtime
> correctamente; lo que no probaron fue el test.

### 15.5 Qué no se hizo, a propósito

**No se parcheó el test.** El pack autoriza tocar código sólo si el fallo es un
bug de T10, y no lo es. El fix es un one-liner evidente (leer `result.result`),
pero toca el script que corre el **cron de validación**, así que merece su
propio pack con `/code-review` — no un parche al pasar dentro de un CLOSEOUT.

### 15.6 Estado

| Capa | Estado |
|---|---|
| Auth del gateway (§6, §7) | cerrada |
| Ruteo + default al proxy (§8, §12) | cerrada |
| Reruteo silencioso, rutas directas (§9.4, §11) | cerrada |
| Ventana + pile-up de composite (§14) | cerrada — se sostiene acá |
| **Aserción del e2e (`result.result`)** | **abierta** — única que queda |

**Runtime: 4/4.** **Suite: 2/4**, por el desajuste de arriba.

Salud durante todo el pack: `MainPID=3436104` y `NRestarts=1` **sin cambio** en
las cuatro corridas; RSS 887 → 941 MB pico, lejos de los 2 GB de STOP; cero
OOM; cero concurrencia.

Y lo de siempre, explícito: **composite sigue FUERA de cron.**

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t11/`.

---

## 16. UNWRAP — la última capa: P5-L2 cierra en verde (PKG-MACRO-P5-L2-T12, 2026-08-14)

**GO de David (orquestador):** UNWRAP. Un helper, no tres one-liners copiados.
Tras este pack se cierra P5-L2. No concurrencia. Composite NO a cron.

§15 dejó una sola capa abierta: la aserción. El runtime pasaba los cuatro tests
y la suite reportaba 2/4 porque dos endpoints no devuelven el mismo shape. Este
pack cierra eso y nada más.

### 16.1 El desajuste, con la línea exacta que lo produce

```
POST /run              → {ok, task_id, task, team, trace_id, result:{model, report, ...}}
GET  /task/<id>/status → {status, result:{ok, task_id, task, ..., result:{model, report, ...}}}
```

El worker devuelve un sobre (`worker/app.py:729-735`). `WorkerClient.run()` pasa
ese sobre entero, y `dispatcher/queue.py:243` lo guarda tal cual:

```python
envelope["result"] = result      # ← `result` ya ES el sobre del worker
```

Así que sobre un status el payload del handler queda **un nivel más adentro**.
Leer `result["model"]` ahí da `None` → el test imprime `?`. No hay nada roto en
el runtime: está leyendo el lugar equivocado.

### 16.2 El helper, y por qué es estricto

Un solo `_worker_payload(status_data)` en `scripts/e2e_validation.py`, usado en
las tres funciones que pasan por `_enqueue_and_wait` (routing coding, routing
research, composite). Los lectores de `POST /run` no se tocaron: ya leen bien.

El criterio **no** puede ser "¿tiene un `result` dict adentro?". Hay handlers
cuyo payload propio ya trae un `result` anidado — `granola` devuelve
`{followup_type, result:{task_id, ...}}` — y un unwrap laxo se comería un nivel
de más justo ahí. Se exige el juego completo de marcadores que el worker
**siempre** pone en el sobre y que ningún handler tiene junto: `ok` + `task_id`
+ `task`. Verificado recorriendo con AST todos los `return {...}` de
`worker/tasks/`: **ningún handler devuelve los tres**.

Aplicado a una respuesta de `POST /run` el helper es pass-through: no hay
segundo unwrap.

### 16.3 Lo que encontró el `/code-review`

8 hallazgos. **5 eran de este diff y se corrigieron en el mismo PR:**

1. **El helper devolvía el sobre cuando el payload del handler no era dict.** La
   condición mezclaba dos preguntas: *¿es el sobre?* y *¿el inner es dict?*. Un
   handler que devuelva lista o string caía al `return` de abajo y el caller
   recibía `{ok, task_id, task, trace_id, result:[...]}` → `report=''`,
   `model='?'`. **El bug de T11 de vuelta, en silencio, justo en el caso que el
   helper decía cubrir.** Ahora la detección depende sólo de los marcadores.
2. **`test_composite_research` seguía dando PASS con "reporte 0 chars".**
   `_run_test` marca `passed=True` con que la función retorne. El largo del
   reporte sólo es una métrica honesta si el vacío falla. Sin ese guard, la
   próxima regresión del shape se vuelve a colar como verde en el cron de las
   06:00 — que es *exactamente* lo que pasó durante cinco meses.
3. Un `result` corrupto pasaba de `AttributeError` ruidoso a `{}` silencioso.
   Queda el `{}`, pero ya ninguna de las tres funciones puede reportar verde
   sobre datos corruptos.
4. Faltaba el caso *inner no-dict* en los tests: era la rama del hallazgo 1 y
   pasaba los 24 tests sin hacer ruido.
5. Los asserts positivos de routing eran casi tautológicos: llegar al `assertIn`
   ya implicaba que el modelo había coincidido. Pasan a `assertEqual` sobre el
   string completo.

**3 quedaron fuera del alcance ordenado** y van al siguiente pack:

- **`scripts/sim_to_make.py:211` tiene el mismo bug, contra un webhook externo.**
  Encola por `/enqueue`, pollea el status y lee `result.result` como si fuera el
  payload → manda `report=''` y `sources_count=0` a Make.com y devuelve exit 0.
  Es el mismo defecto que el e2e, pero acá no falla un assert: **manda datos
  vacíos a un sistema externo en silencio.**
- El helper es local al script mientras el shape pertenece al contrato
  worker/dispatcher. Ya conviven **cuatro** variantes ad-hoc del mismo unwrap
  (`dispatcher/service.py:345` y `:763`, `sim_to_make.py:211`, y este).
- `test_llm_generate` también da PASS con 0 chars. La orden decía no tocarlo.

### 16.4 Mutación: 4 de 4

Ninguna guarda es vacua — se verificó mutando el **fuente**, no sólo por patch:

| Mutación | Resultado |
|---|---|
| M1 — helper degradado al unwrap ingenuo pre-T12 | 7 failed |
| M2 — detección de sobre atada al tipo del inner | 1 failed (el test nuevo) |
| M3 — sin el guard de reporte no-vacío | 2 failed |
| M4 — unwrap laxo, sin marcadores | 1 failed (caso granola) |

`pytest`: **4831 passed**, 6 skipped, 2 xfailed. Deselect de 3 `test_pit_*`
ajenos (PIT archivado); verificado que fallan igual sobre `main` sin este diff.

### 16.5 Live: sólo b y c

Composite **no** se re-corrió: ya está `[E]` en §15 y son ~200s de turno.

| test | resultado | elapsed | RSS pico | ΔNRestarts |
|---|---|---|---|---|
| b) `test_routing_coding_selects_claude` | **PASS** | 36.7 s | 731 MB | 0 |
| c) `test_routing_research_selects_gemini` | **PASS** | 36.5 s | 782 MB | 0 |

Los dos: `expected=anthropic/claude-sonnet-4-6, actual=anthropic/claude-sonnet-4-6`.

El dato que cierra el argumento: **elapsed T11 → T12 fue 36.6 → 36.7 s y 39.2 →
36.5 s.** El runtime era idéntico en los dos packs. Lo único que cambió es dónde
mira el test.

### 16.6 Estado

| Capa | Estado |
|---|---|
| Auth del gateway (§6, §7) | cerrada |
| Ruteo + default al proxy (§8, §12) | cerrada |
| Reruteo silencioso, rutas directas (§9.4, §11) | cerrada |
| Ventana + pile-up de composite (§14) | cerrada |
| Aserción del e2e (`result.result`) | **cerrada acá** |

**`P5_L2_E2E = Y`**, con la evidencia repartida en dos packs, cada uno midiendo
lo suyo: **el runtime de los 4 en §15 (T11)** — incluido composite, 206.6 s, 1
ejecución, 0 re-encolas, 19.459 chars — **y la aserción de b y c acá (T12)**.

Salud: `MainPID=3436104` y `NRestarts=1` sin cambio; RSS 637 → 782 MB pico,
lejos de los 2 GB de STOP; cero OOM; cero concurrencia; gateway nunca reiniciado.

Y lo de siempre, explícito: **composite sigue FUERA de cron.** Que la suite esté
verde no cambia que un turno de composite son ~200 s sobre un gateway
compartido; habilitarlo en cron es una decisión aparte, y no se tomó.

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l2-t12/`.

---

## 17. Coda de L2 — el mismo bug, en un lugar donde nadie miraba (PKG-MACRO-P5-L3-T1, 2026-08-14)

**GO de David (orquestador):** primer ítem del bloque post-L2. No concurrencia.
Composite NO a cron. No POST real a Make. No re-correr composite live.

§16 cerró el unwrap en el e2e y dejó anotado que el mismo desajuste vivía en
`scripts/sim_to_make.py`. Esto es esa coda: misma familia de bug, distinto
final. En el e2e fallaba un assert y se veía. Acá no fallaba nada.

### 17.1 Lo que hacía sim_to_make

Encola un `composite.research_report`, poolea `GET /task/<id>/status` y leía
`result["result"]` como si fuera el payload del handler. Sobre un status ese
nivel es el **sobre del worker**, así que `report` salía `''` y
`sources_count` `0` — y el script mandaba eso al webhook de Make.com
**devolviendo exit 0**. Un pipeline verde entregando nada.

Y un segundo bug encima, que lo habría tapado igual: `DEFAULT_TIMEOUT = 120`.
Un composite mide ~200 s de wall y el dispatcher le da 300 s de ventana, así que
el poll se rendía **antes de que el payload existiera**, aunque el unwrap
estuviera bien. Ahora son 340 s, con la misma cuenta que el e2e: la ventana del
cliente cubre la del **dispatcher**, no el wall medido.

### 17.2 El helper sube a `client/`

`client/task_result.py` — `worker_payload()` + `WORKER_ENVELOPE_MARKERS`.
Criterio idéntico al de T12, palabra por palabra: desenvuelve sólo si el
`result` trae `ok`+`task_id`+`task` juntos **y** la clave `result`; inner
no-dict → `{}`; `granola` es pass-through. Sólo lee: el wrap de `queue.py:243`
no se toca.

Callers migrados:

| Dónde | Estaba | Ahora |
|---|---|---|
| `scripts/e2e_validation.py` | el helper original de T12 | import + alias `_worker_payload` |
| `scripts/sim_to_make.py:224` | **roto** — mandaba `''` a Make | `worker_payload` + guard |
| `dispatcher/service.py:349` | resumen para Linear | `worker_payload`, truncado igual |
| `dispatcher/service.py:767` | resumen para Notion | idem |
| `dispatcher/service.py:592` | issue id de Linear | calzaba exacto |

El alias privado en el e2e se conserva **a propósito**: es el nombre que
parchean los tests de mutación de T12, que son los que prueban que las tres
funciones dependen realmente del unwrap. Los 26 siguen verdes sin relajar una
sola aserción.

**Guard nuevo**: si tras el unwrap el reporte está vacío, `sim_to_make` no llama
a Make y sale 6. Dry-run tampoco finge éxito. Es la misma lección que §16 le
aplicó a composite: el largo del reporte sólo es una métrica honesta si el vacío
falla.

### 17.3 Lo que encontró el `/code-review`

10 hallazgos. **El más serio era mío y repetía la lección de T10.**

Mi test del timeout assertaba `>= 340` — un **literal** — cuando el docstring
decía proteger otra cosa: que la ventana del cliente cubra la del dispatcher. Si
`COMPOSITE_TASK_TIMEOUT_S` subiera a 600, `sim_to_make` quedaría en 340 < 600, el
poll volvería a rendirse antes de tiempo, y el test seguiría **verde**. Es
exactamente el error de §14: un invariante que compara números sueltos en vez de
las dos magnitudes reales. Ahora importa la constante y compara contra ella.

Y hubo uno que escribí **mientras arreglaba los otros**: al cubrir el resumen del
dispatcher, mi test assertaba que apareciera `"informe real"` en el comentario
— pero ese texto también aparece cuando se vuelca el sobre entero, y el fixture
que usé no tenía `trace_id`. La mutación pasaba 66/66. Reanclado a `task_id`,
que sólo existe en el sobre.

El resto: `--timeout` seguía pudiendo reintroducir la ventana corta desde la CLI
(ahora avisa; no se clampea, porque si el operador pide una ventana corta esa es
su decisión — lo que no puede ser es silenciosa); los dos resúmenes del
dispatcher no los fijaba ningún test y son salida visible para David; un leak de
patchers que podía contaminar toda la suite; un alias muerto; un test que pasaba
con `sim_to_make.py` borrado del repo; el fixture del sobre duplicado en tres
archivos, que subió a `conftest.py` junto con el helper.

**No corregido**: `dispatcher/smart_reply.py` (4 lecturas a mano). Hoy son
**correctas** — shape `POST /run`, un solo nivel — así que es inconsistencia, no
bug. La orden enumeraba los call sites y smart_reply no estaba.

### 17.4 Mutación: 8 de 8

| Mutación | Resultado |
|---|---|
| M7 — el dispatcher ensancha su ventana a 600 s | 1 failed |
| M8 — sin el warning de ventana corta | 1 failed |
| M9 — dispatcher sin el fallback `or result` | 4 failed |
| M10 — dispatcher sin unwrap | 1 failed *(tras reanclar)* |
| M11 — helper → unwrap ingenuo pre-T12 | 13 failed |
| M12 — unwrap laxo, sin marcadores | 3 failed |
| M13 — `sim_to_make` sin el guard de no-vacío | 3 failed |

(M1–M6 de la primera vuelta siguen cazando.)

`pytest`: **4853 passed**, 6 skipped, 2 xfailed. Deselect de 3 `test_pit_*`
ajenos (PIT archivado).

### 17.5 Estado

`P5_L3_SIM_UNWRAP = Y`. Cero red viva: ningún test de este pack encola un
composite, y no se hizo un solo POST a Make.com. Composite no se re-corrió: su
runtime ya está `[E]` en §15.

Y lo de siempre, explícito: **composite sigue FUERA de cron — y `sim_to_make`
tampoco entra.** Que el script ahora diga la verdad no lo vuelve un candidato a
correr solo; sigue siendo ~200 s de composite contra un gateway compartido, y
ahora además puede salir 6, que es justamente lo que uno no quiere descubrir por
un mail de cron.

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-l3-t1/`.
