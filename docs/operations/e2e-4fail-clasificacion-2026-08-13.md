# Clasificación de los 4 FAIL repetidos del e2e (2026-08-13)

> **Status:** acta docs-only del PKG-MACRO-P5-L2-T1. **Clasifica, no arregla.**
> **Superficie:** VPS `srv1431451`, clone canónico `~/umbral-agent-stack` @ `98d9a954`.
> Cero escrituras a Notion, cero mutación de config, servicio, cron o n8n.
> **Origen:** reconteo E6 fila 34 / E-p4 — "mismos 4 FAIL en las 2 últimas
> corridas completas", hipótesis Fable *(no verificada)*: login de modelo del
> gateway.

## 0. Veredicto

Los 4 FAIL **no son cuatro fallos**: son **uno solo**, y la hipótesis de partida
era incorrecta en un punto que cambia el costo del fix.

**No hay ningún login expirado.** El gateway OpenClaw está `active` y con 5
modelos configurados. Lo que pasa es que **el worker no tiene credencial de
ningún provider LLM**: `/providers/status` devuelve `"configured": []` con los 9
providers declarados en `unconfigured`. El worker está aislado del gateway que
sí funciona.

Capa única para las 4 filas: **preflight del modelo** — variante *credencial
ausente en el env del worker*, no *login vencido*.

## 1. Tabla de clasificación

| # | Test | Último resultado (2026-08-13 06:00 -04) | Capa | Causa raíz |
|---|---|---|---|---|
| 4 | `llm.generate` | `HTTPStatusError: Server error '500' for url 'http://127.0.0.1:8088/run'` | preflight del modelo | `RuntimeError: GOOGLE_API_KEY not configured` en el worker |
| 5 | `composite.research` | `ValueError: composite.research_report terminó en status=blocked: None` | preflight del modelo | **Derivado de #4**: `composite.py` importa y llama `handle_llm_generate` (líneas 13, 105, 130) |
| 14 | `R8: Routing coding` | `ValueError: No effective configured route for coding` | preflight del modelo | `has_configured_route: false`; los 4 providers de la cadena (`azure_foundry`, `claude_pro`, `gemini_pro`, `gemini_flash`) están `unconfigured` |
| 15 | `R8: Routing research` | `ValueError: No effective configured route for research` | preflight del modelo | Idéntico a #14 sobre la cadena de `research` |

## 2. Repo dice vs VPS verifica

| | Repo dice | VPS verifica |
|---|---|---|
| Providers | `openclaw.json` declara 9 providers y cadenas de fallback por tarea (`coding`, `research`, `critical`, …) | `/providers/status` → `"configured": []`, los 9 en `unconfigured`, `has_configured_route: false` en toda ruta |
| Credenciales | El worker lee `GOOGLE_API_KEY`/`GOOGLE_API_KEY_NANO` (`research_backends.py:257-258`), `AZURE_OPENAI_API_KEY` (`llm.py:203`), `OPENCLAW_GATEWAY_TOKEN` (`llm.py:219`), `ANTHROPIC_API_KEY` (`llm.py:221`) | **Ninguna de las 4 está en `~/.config/openclaw/env`**, que sí tiene otras 16 claves (Notion, Linear, X, YouTube, Tavily, GitHub, …) |
| Gateway | — | `openclaw-gateway` `active`; default `openai/gpt-5.5`, fallback `openai/gpt-5.4`, 5 modelos configurados |

**La consecuencia práctica:** hay LLM disponible en la VPS; el worker no lo
alcanza. `openclaw_proxy` es el provider que lo puentearía y depende de
`OPENCLAW_GATEWAY_TOKEN`, que es una de las cuatro ausentes.

## 3. Hallazgo lateral (no es uno de los 4)

El cron `e2e-validation-cron.sh` corre con `--notion` y su post final falla
aparte, por longitud:

```
[ERROR] Notion add_comment failed (400): ... body.rich_text[0].text.content.length
should be ≤ 2000, instead was 2001
```

Un carácter por encima del límite. Es una quinta rotura del mismo cron, con
causa propia (truncado del cuerpo), independiente de los 4 FAIL.

## 4. Qué NO se hizo

Cero fixes: no se cargó ninguna credencial, no se tocó `openclaw.json`, el
crontab, el gateway ni el worker. La corrida analizada es la del cron
(2026-08-13 06:00 -04, **posterior** al merge de T1), así que no hizo falta
re-ejecutar el e2e a mano.
