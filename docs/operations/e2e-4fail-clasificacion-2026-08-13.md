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
