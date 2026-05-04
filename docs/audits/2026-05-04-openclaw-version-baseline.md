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
