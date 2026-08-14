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
- **(c)** Aceptar conscientemente que esas tres rutas paguen ~32s y ~12.8k
  tokens por llamada, con el riesgo de saturación del gateway compartido ya
  demostrado en §9.2.

Una tercera vía que este pack no exploró (fuera de su autorización): darle
al worker una API key propia de algún provider (`gemini`/`azure`) para
`llm.generate`, que no depende del gateway en absoluto — es la "vía B" que
§6 ya mencionaba como disponible e independiente de la capa 3.

Evidencia completa (4 sondas, journal, diff de keys sin secretos) en
`~/.coord-ag-evidence/pkg-macro-p5-l2-t6/`.
