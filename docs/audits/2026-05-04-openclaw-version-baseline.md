# OpenClaw Version Baseline — 2026-05-04 (O14.0)

**Tarea:** `.agents/tasks/2026-05-04-002-copilot-vps-openclaw-version-baseline.md`
**Tipo:** Lectura pura (no instala, no actualiza, no modifica `~/.openclaw/openclaw.json`).
**Sigue regla:** "VPS Reality Check Rule" (`.github/copilot-instructions.md`, commit `fbc5dae`). Todo lo de la sección "VPS muestra Y" fue capturado en VPS real vía SSH/CLI; el repo se cita como "Repo dice X".

---

## 1. Versión instalada en VPS

**Repo dice:** ningún script de Umbral pinea una versión activa de OpenClaw a 2026-05-04. Los únicos pins en repo son referencias históricas en audits viejos: `docs/audits/2026-03-23-...` menciona `2026.3.2`, audits previos citan `2026.2.25` y `2026.3.23`. No hay `package.json` ni `requirements.txt` en este repo que pinee OpenClaw — se instala globalmente en VPS.

**VPS muestra:**

```
$ which openclaw
/home/rick/.npm-global/bin/openclaw

$ ls -la /home/rick/.npm-global/bin/openclaw
... -> ../lib/node_modules/openclaw/openclaw.mjs

$ openclaw --version
2026.4.9

$ npm ls -g --depth=0 2>/dev/null | grep -i openclaw
└── openclaw@2026.4.9

$ jq -r '.version' /home/rick/.npm-global/lib/node_modules/openclaw/package.json
2026.4.9
```

- **Versión:** `2026.4.9`
- **Manager:** npm global (`~/.npm-global/`), no pip, no binario propietario.
- **Binario:** symlink `~/.npm-global/bin/openclaw → ../lib/node_modules/openclaw/openclaw.mjs`.
- **Node runtime:** v24.14.0 (capturado en `openclaw status --all`).

---

## 2. Versión upstream actual

Capturado vía `npm view openclaw` (registry oficial npm).

- **Última estable publicada:** `2026.5.3-1` (publicada 2026-05-02).
- **Última beta publicada:** `2026.5.4-beta.1` (publicada 2026-05-03).
- **Tag `latest` en npm:** apunta a `2026.5.3-1`.

Se descargó el tarball `openclaw-2026.5.3-1.tgz` para inspeccionar `CHANGELOG.md` upstream sin instalarlo en el sistema (extraído en `/tmp/openclaw-latest/package/`, no instalado).

---

## 3. Delta de releases entre instalada y upstream

**17 releases estables** publicadas entre `2026.4.9` (instalada) y `2026.5.3-1` (latest), más 2 betas intermedias:

```
2026.4.10, 4.11, 4.12, 4.14, 4.15, 4.18,
2026.4.19-beta.1, 4.19-beta.2,
2026.4.20, 4.21, 4.22, 4.23, 4.24, 4.25, 4.26, 4.27, 4.29,
2026.5.2, 5.3, 5.3-1
```

Cadencia ~1 release cada 1–2 días (proyecto activo). Brecha temporal aproximada: **~25 días** entre publicación de 4.9 y 5.3.

---

## 4. Breaking changes relevantes para Umbral

Se inspeccionó el `CHANGELOG.md` del tarball upstream (`/tmp/openclaw-latest/package/CHANGELOG.md`) para todas las secciones `### Breaking` entre 4.10 y 5.3.

**Resultado:** **una sola entrada Breaking** en todo el rango, en `2026.4.24`:

> Plugin SDK/tool-result transforms: remove the Pi-only `api.registerEmbeddedExtensionFactory(...)` compatibility path. Bundled tool-result rewrites must use `api.registerAgentToolResultMiddleware(...)` with `contracts.agentToolResultMiddleware` declaring the targeted harnesses, so transforms run consistently across Pi and Codex app-server dynamic tools.

**Impacto en Umbral:** **ninguno**. Umbral no es un plugin SDK consumer de OpenClaw — usa OpenClaw como gateway/dispatcher externo vía:
- CLI: `openclaw status --all`, `openclaw models status`, `sessions_list`, `models list`.
- HTTP gateway local (loopback + WS) consumido por `worker/openclaw_panel_vps.py` y similares.
- Config en `~/.openclaw/openclaw.json` (formato user config, no SDK).

Ninguno de esos surfaces toca `registerEmbeddedExtensionFactory`, que es API interna de plugins bundled (Pi/Codex). El resto de cambios entre 4.9–5.3 son aditivos: nuevos providers (DeepSeek V4, Gemini Live, Gradium TTS), mejoras de Gateway/Control UI, refactors lazy-load, OTEL diagnostics. **Cero breaking changes que rompan cómo Umbral usa OpenClaw.**

Notas relevantes (no breaking pero a vigilar en O14.2 si se ejecuta upgrade):

- **4.24 — Gateway autorestore policy:** "stop Gateway startup and hot reload from auto-restoring invalid config; invalid config now fails closed and `openclaw doctor --fix` owns last-known-good repair." → Si tras upgrade el `openclaw.json` actual (971 líneas, md5 `0df7a03297a67d88f5be8f404c262946`) tiene algún drift incompatible, el gateway no restaurará silenciosamente; habrá que correr `openclaw doctor --fix`. Recomendación O14.2: snapshot del config antes del upgrade.
- **4.x — `models/commands` deprecation:** `/models add` ahora deprecated. Umbral no agrega modelos vía slash command, así que no aplica.
- **4.x — Gateway config `$include`:** nueva flag `OPENCLAW_INCLUDE_ROOTS`. Aditivo, default seguro.
- **5.x — Sessions/list bounded reads:** `sessions_list` ahora cap'd. Si Umbral usa este endpoint para listas largas, podría ver paginación distinta. Verificar en O14.2.

---

## 5. Health snapshot pre-upgrade

Capturado 2026-05-04 ~14:30 -03 en VPS (Ubuntu, Linux 6.8.0-106).

### `openclaw status --all`

```
OpenClaw status
  Version          2026.4.9
  Node runtime     v24.14.0
  Gateway service  active (running) since Fri 2026-04-24 03:50:44; pid 1000650
  Agents           9 configured
  Active sessions  165
  Models           10 configured (default: azure-openai-responses/gpt-5.4)
  Workspace        ~/.openclaw/workspace
  Config           ~/.openclaw/openclaw.json (md5 0df7a03297a67d88f5be8f404c262946, 971 lines)
```

### `openclaw models status`

- **Default:** `azure-openai-responses/gpt-5.4` ✓
- **Fallbacks (5):** configured per `openclaw.json`.
- **Models configured:** 10.
- **Issue detectado (pre-existente, no causado por versión):** `[openai-codex] Token refresh failed: 401 refresh_token_reused`. El refresh token de Codex está quemado. **No bloqueante para O14.0** (Umbral usa Azure como default, no Codex). A trackear separado si Codex se va a usar.

### `systemctl --user status openclaw-gateway`

```
● openclaw-gateway.service — OpenClaw Gateway (v2026.3.2)
   Loaded: loaded (~/.config/systemd/user/openclaw-gateway.service; enabled)
   Active: active (running) since Fri 2026-04-24 03:50:44 -03; ~10 days ago
   Main PID: 1000650 (node)
```

**Divergencia repo vs VPS:** la unit file describe "v2026.3.2" pero el binario corriendo es `2026.4.9`. La descripción quedó desactualizada en algún upgrade pasado. **No funcional** (es solo un string en `Description=`), pero conviene refrescarlo en O14.2 al hacer el próximo upgrade para evitar confusión.

### `openclaw.json` snapshot

```
$ wc -l ~/.openclaw/openclaw.json
971 ~/.openclaw/openclaw.json

$ md5sum ~/.openclaw/openclaw.json
0df7a03297a67d88f5be8f404c262946  /home/rick/.openclaw/openclaw.json
```

Estos dos valores son la línea base para detectar drift post-upgrade en O14.2. Si tras upgrade el `md5` cambia sin intención humana, es signo de que `openclaw doctor --fix` o el self-migration tocó algo y hay que revisar diff.

---

## 6. Recomendación para O14.1 (insumo, no decisión)

**Recomendación:** **Opción (b) — upgrade tras O13.1 estable**, con caveat de baja urgencia.

Razonamiento:

- **Riesgo de upgrade:** **bajo**. Cero breaking changes que afecten cómo Umbral usa OpenClaw (CLI + gateway HTTP + `openclaw.json`). El único Breaking del rango (Plugin SDK `registerEmbeddedExtensionFactory`) no aplica.
- **Beneficio inmediato:** **bajo-medio**. Mejoras útiles pero no críticas: `gateway status` startup más rápido (4.24), `sessions list` más responsivo bajo carga (5.x), opt-in OTEL diagnostics (4.24). Ninguna feature que Umbral esté esperando hoy.
- **Riesgo de no upgrade:** **bajo a corto plazo, medio a 1–2 meses**. 17 versiones de drift ya. Cada release nueva amplía el delta y reduce la posibilidad de que el changelog upstream siga citando paths de migración para configs viejos como el actual.
- **Por qué no (a) "upgrade ya":** O13.1 (Mission Control dashboard) está en flight y depende de runtime estable de gateway. Hacer upgrade en paralelo agrega una variable. El upgrade debe ser una ventana dedicada con health snapshot pre/post y validación de los 4 surfaces (CLI, gateway HTTP, worker upserts, smart replies).
- **Por qué no (c) "hold con razón":** no hay razón fuerte para hold indefinido — el delta es bajo riesgo y sigue creciendo.

**Sugerencias para O14.2 si pasa a ejecución:**

1. Snapshot pre-upgrade: copiar `~/.openclaw/openclaw.json` a `~/.openclaw/openclaw.json.bak-pre-5.3` y guardar md5 actual (`0df7a03297a67d88f5be8f404c262946`).
2. `npm install -g openclaw@2026.5.3-1` (o la stable más reciente al momento de ejecución).
3. `openclaw doctor --fix --non-interactive` (esperado por changelog 4.24: gateway ya no auto-restaura config inválido).
4. Refrescar el `Description=` del unit file `openclaw-gateway.service` para reflejar versión nueva (cosmético, lo arrastramos desde 3.2 → 4.9 → 5.3).
5. Validación post-upgrade: `openclaw status --all`, `openclaw models status`, smoke test del worker (`scripts/vps/verify-openclaw.sh` si existe equivalente), validar que `openclaw_panel_vps.py` sigue refrescando vía notion.upsert_*.
6. Trackear separado el issue de Codex `refresh_token_reused` — no se resuelve con el upgrade, requiere re-auth manual (`openclaw login codex` o equivalente).

La decisión final (a/b/c) la toma David.

---

## 7. Resumen "Repo dice X" vs "VPS muestra Y"

| Item | Repo dice | VPS muestra |
|---|---|---|
| Versión OpenClaw | Sin pin activo (audits citan 3.2, 3.23, etc.) | `2026.4.9` instalada vía npm global |
| Manager | No declarado en repo | npm global en `~/.npm-global/` |
| Gateway service | Unit file describe "v2026.3.2" | Binario corriendo es `2026.4.9` (descripción stale, no funcional) |
| Default model | `~/.config/openclaw/env` referencia Azure | `azure-openai-responses/gpt-5.4` activo y respondiendo |
| Codex provider | Configurado en openclaw.json | Token refresh fallando (`401 refresh_token_reused`, pre-existente) |
| Config md5 | N/A (no en repo) | `0df7a03297a67d88f5be8f404c262946` (971 líneas) |
| Upstream latest | N/A (no se trackea en repo) | `2026.5.3-1` en npm (delta: 17 stable releases) |

---

**Fin baseline O14.0.** Commit hash de este audit se enlaza en `## Log` de `.agents/tasks/2026-05-04-002-...md`.

---

## Upgrade attempt 2026-05-04 — FAILED (O14.2)

**Tarea origen:** `.agents/tasks/2026-05-04-004-copilot-vps-openclaw-upgrade-failure-diagnosis.md`
**Disparo:** David clickeó "Update now" en dashboard del gateway (`2026.4.9` → `2026.5.3`) ~19:15 -04.
**Tipo:** Diagnóstico read-only. **Cero acciones reversivas ejecutadas.**

### Síntoma exacto del dashboard

> **Update error: global install verify. See the gateway logs for the exact failure and retry once the cause is fixed.**

Banner sigue mostrando "Update available v2026.5.3 (running v2026.4.9)" tras el intento.

### Estado real del runtime — SPLIT

```
$ openclaw --version
OpenClaw 2026.5.3-1 (2eae30e)

$ ps -o pid,etime,cmd -p 1000650
    PID     ELAPSED CMD
1000650 10-15:45:59 openclaw-gateway

$ systemctl --user is-active openclaw-gateway.service
active

$ jq -r '.version' /home/rick/.npm-global/lib/node_modules/openclaw/package.json
2026.5.3-1
```

**Diagnóstico:** install en disco **completó OK**. El binario y `package.json` ya son `2026.5.3-1`. **Pero** el daemon corriendo (PID 1000650) sigue siendo el de `2026.4.9` arrancado 2026-04-24 — nunca se reinició. Resultado: nuevas invocaciones CLI usan código `5.3-1`, RPCs al gateway pegan al daemon `4.9`.

### Logs relevantes

**Gateway journal** — tres intentos `update.run completed ... status=error`:

```
19:17:44 [gateway] update.run completed actor=openclaw-control-ui ... restartReason=update.run status=error
19:17:44 [ws] ⇄ res ✓ update.run 136183ms conn=b1c5747d…5cd2
19:19:16 [gateway] update.run completed actor=openclaw-control-ui ... restartReason=update.run status=error
19:19:16 [ws] ⇄ res ✓ update.run 22460ms conn=69afb71e…8453
```

El gateway loguea `status=error` **sin mensaje subyacente** — el error queda swallowed en el RPC. La duración del primer intento (136s) es consistente con un `npm install -g` completo + step adicional de verify.

**npm debug log del intento (`~/.npm/_logs/2026-05-04T23_19_39_043Z-debug-0.log`, 352KB):**

```
4083 verbose cwd /home/rick/.npm-global/lib/node_modules/openclaw
4084 verbose os Linux 6.8.0-106-generic
4085 verbose node v24.14.0
4086 verbose npm  v11.9.0
4087 verbose exit 0
4088 info ok
```

`npm install -g openclaw@latest` **exitó 0**. Cero `EACCES`/`EPERM`/`EEXIST`/`EINTEGRITY`/`ENOSPC` en el log. La falla está **downstream** de npm, en el step "verify" propio del orquestador del gateway (probablemente un health check post-install que el gateway corre antes del self-restart, y que falló porque el daemon viejo todavía está sirviendo y no responde con la versión nueva, o porque algún subprocess de verificación timeout-eó).

### Hipótesis chequeadas y descartadas

| Hipótesis | Check | Resultado |
|---|---|---|
| Disk full | `df -h` | 19G/96G usado, **78G libre** ✓ |
| npm cache corrupto | `npm cache verify` | clean (4968 entries verified) ✓ |
| Permisos `~/.npm-global` rotos | `ls -ld` | `rwxrwxr-x rick rick` ✓ |
| Network / registry timeout | `npm ping` | PONG 753ms ✓ |
| Node incompatible | `node --version` vs `engines.node` | v24.14.0 vs `>=22.14.0` ✓ |
| Peer deps no satisfechas | `npm view ... peerDependencies` | empty ✓ |
| `npm ls -g` extraneous/UNMET | inspección | clean ✓ |
| Integrity hash mismatch | log `--verbose` | sin `EINTEGRITY` ✓ |

**Ninguna de las hipótesis comunes aplica.** La install completó. La falla es del gateway verify, no de npm.

### Causa raíz identificada

**"global install verify" es un step del orquestador del gateway (control-ui RPC `update.run`), NO del subproceso `npm install`.** El subproceso `npm install -g openclaw@latest` exitó 0 limpio — los archivos ya están en disco con la versión nueva. Lo que falló es el step de verificación que el daemon corre **después** del install y **antes** del self-restart, probablemente porque:

- El daemon viejo (PID 1000650, ya 10+ días corriendo) no se reinició para hacer el verify con la versión nueva, y el verify orquestado intra-proceso no detectó la nueva versión cargada.
- O bien el verify intenta spawnear `openclaw --version` y comparar contra la target version, y algo en ese subproceso falla (sin más info porque el RPC no propaga el mensaje).

El gateway reporta `status=error` swallowed sin stack — bug observable de UX/debuggability del orquestador upstream (no de Umbral).

### Estado actual del runtime

| Surface | Estado | Versión efectiva |
|---|---|---|
| CLI binario (`openclaw --version`) | ✓ funciona | `2026.5.3-1` |
| Files en `~/.npm-global/lib/node_modules/openclaw/` | ✓ presentes | `2026.5.3-1` (mtime 2026-05-04 19:19) |
| Symlink `~/.npm-global/bin/openclaw` | ✓ intacto | apunta a `openclaw.mjs` nuevo |
| Daemon `openclaw-gateway.service` | ✓ active running | **`2026.4.9` (PID 1000650, since 2026-04-24)** |
| `~/.openclaw/openclaw.json` md5 | ✓ unchanged | `0df7a03297a67d88f5be8f404c262946` (sin drift) |
| `npm cache verify` | ✓ clean | 4968 entries |

**Severidad:** SPLIT — runtime degradado pero servicio NO caído. Tráfico WS sigue siendo atendido por el daemon viejo. Las próximas invocaciones CLI usarán código nuevo (mismatch potencial si un script combina `openclaw --foo` con un RPC al gateway).

### Recomendación de remediación

**R5 (otra) — restart explícito del gateway service.**

Razonamiento:
- El install completó. La única acción pendiente es que el daemon levante el binario nuevo. `systemctl --user restart openclaw-gateway.service` debería hacerlo en una sola operación reversible (la unit ya apunta al symlink, que ya resuelve a `openclaw.mjs` nuevo).
- Pre-restart conviene validar: snapshot config (`cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-5.3-restart`), confirmar md5 sin drift, y tener el comando de rollback listo (`npm install -g openclaw@2026.4.9` + restart) por si el daemon `5.3-1` falla al arrancar contra el config 4.9.
- Per changelog 4.24 (capturado en §4 de este audit): el gateway nuevo **no auto-restaura config inválido**, falla cerrado y requiere `openclaw doctor --fix`. Si tras restart el gateway no levanta, ese es el siguiente paso.
- Riesgo de R5: bajo. La instalación ya está hecha; solo se está completando el step que el orquestador no logró cerrar.
- Riesgo de no hacer nada: el SPLIT crece — cada invocación CLI nueva (5.3-1) que pegue al daemon viejo (4.9) puede ver schema/RPC mismatch. Ya se observan en log dos errores `models.list` con `unexpected property 'view'` y `commands.list` con `unknown method` (líneas 19:18:39 y 19:19:19), que pueden ser exactamente este tipo de mismatch (CLI nueva preguntando con shape nuevo a daemon viejo).

**Plan propuesto (NO ejecutado, requiere OK de David):**

1. `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-5.3-restart`
2. `md5sum ~/.openclaw/openclaw.json` (esperado: `0df7a03297a67d88f5be8f404c262946`).
3. `systemctl --user restart openclaw-gateway.service`
4. `sleep 3 && systemctl --user status openclaw-gateway.service --no-pager | head -20`
5. `openclaw status --all` — esperar versión `2026.5.3-1` y gateway `active`.
6. Si gateway no levanta: `openclaw doctor --fix --non-interactive`.
7. Rollback de emergencia si todo falla: `npm install -g openclaw@2026.4.9 && systemctl --user restart openclaw-gateway.service`.
8. Refrescar cosmético `Description=` del unit file en oportunidad separada.

**Alternativas consideradas y descartadas:**

- **R1 (retry simple):** descartada. Re-clickear "Update now" probablemente reproduce el mismo verify-error porque el install ya está hecho y el daemon sigue siendo el mismo. No ataca la causa.
- **R2 (cache + retry):** descartada. Cache está clean.
- **R3 (CLI manual `npm install -g`):** descartada. **Ya se hizo** — el dashboard mismo lo ejecutó y exitó 0. Repetir sería redundante.
- **R4 (hold en 4.9):** descartada como first-line. No hay evidencia de bug del paquete `5.3-1`; el problema es de orquestación. Si tras R5 el daemon `5.3-1` falla al arrancar, R4 (rollback a 4.9) pasa a ser el plan.

### Notas para upstream (no-bloqueante)

El orquestador `update.run` del gateway debería propagar el mensaje del error de verify al RPC en lugar de devolver `status=error` swallowed. El log actual obliga a inferir desde duración + ausencia de restart. Loggable como issue cosmético/UX en upstream OpenClaw cuando se quiera.

---

**Fin apéndice O14.2.** No se ejecutó remediación. Decisión queda en David.
