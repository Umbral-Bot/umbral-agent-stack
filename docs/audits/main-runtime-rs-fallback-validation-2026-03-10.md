## Ejecutado por: codex

# Validación runtime `main` y error `rs_* not found` — 2026-03-10

## Objetivo

Diagnosticar el error visible en producción:

- `HTTP 400: Item with id 'rs_...' not found. Items are not persisted when store is set to false`

y validar si el resumen de Rick sobre el frente de mejora continua era correcto o estaba mezclando un problema del proyecto con un problema del runtime del agente `main`.

## Hallazgo principal

El error `rs_* not found` **no** vino del contenido del proyecto de mejora continua.

Vino de la cadena de fallback del agente `main` cuando se dio esta secuencia:

1. `openai-codex/gpt-5.4` pegó contra rate limit
2. `openai-codex/gpt-5.3-codex` también quedó dentro de la misma presión de cuota
3. el siguiente fallback era `google-vertex/gemini-3.1-pro-preview`
4. ese fallback falló por credenciales ADC ausentes
5. el runtime quedó reintentando con un reasoning item no persistido (`rs_*`) y terminó en `HTTP 400`

## Evidencia

`journalctl --user -u openclaw-gateway.service --since '2026-03-10 03:20:00' --until '2026-03-10 03:40:00'`

Se observaron, en ese orden:

- `API rate limit reached`
- `Could not load the default credentials`
- `HTTP 400: Item with id 'rs_...' not found`

## Cambio aplicado en producción

Se ajustó la lista de fallback de `main` para evitar que un rate limit de Codex cayera directamente en `google-vertex`, que hoy no tiene un path de credenciales sano para ese runtime.

### Antes

1. `openai-codex/gpt-5.3-codex`
2. `google-vertex/gemini-3.1-pro-preview`
3. `azure-openai-responses/gpt-5.2-chat`
4. `azure-openai-responses/gpt-4.1`
5. `azure-openai-responses/kimi-k2.5`

### Después

1. `openai-codex/gpt-5.3-codex`
2. `azure-openai-responses/gpt-5.4`
3. `azure-openai-responses/gpt-5.2-chat`
4. `azure-openai-responses/gpt-4.1`
5. `azure-openai-responses/kimi-k2.5`
6. `google/gemini-3-pro-preview`

El cambio se aplicó con el CLI nativo de OpenClaw:

- `openclaw models fallbacks clear --agent main`
- `openclaw models fallbacks add ... --agent main`

y luego:

- `systemctl --user restart openclaw-gateway.service`

## Verificación posterior

`openclaw models status --probe-provider openai-codex` quedó así:

- `Default`: `openai-codex/gpt-5.4`
- `Fallbacks`:
  - `openai-codex/gpt-5.3-codex`
  - `azure-openai-responses/gpt-5.4`
  - `azure-openai-responses/gpt-5.2-chat`
  - `azure-openai-responses/gpt-4.1`
  - `azure-openai-responses/kimi-k2.5`
  - `google/gemini-3-pro-preview`

Con esto, si vuelve a haber rate limit en Codex, `main` debería caer primero en Azure y evitar el tramo roto `rate limit -> Vertex sin ADC -> rs_*`.

## Verificación del resumen de Rick

El resumen de Rick sobre mejora continua fue **mayormente correcto**, pero mezcló una afirmación técnica ya desactualizada:

- dijo: `GUI/RPA VM: no entra al baseline; falta pyautogui`

Eso ya no era correcto al momento de la revisión:

- `gui.click`: OK
- `gui.type_text`: OK
- `gui.hotkey`: OK

El bloqueo real de GUI/RPA no es `pyautogui`, sino:

- la captura visual sigue siendo negra o no confiable
- el canal GUI sigue siendo útil para input, pero no para validación visual fuerte

## Conclusión

- el error `rs_* not found` era un problema del runtime de `main`, no del proyecto auditado
- el resumen de Rick fue útil, pero contenía un drift técnico en el frente GUI/RPA
- el runtime de `main` quedó endurecido con una cadena de fallback más sana para la operación real actual
