# Rick Notion Poller Hardening — 2026-03-16

## Contexto

Se estaba intentando corregir a Rick en el caso del benchmark de Kris Wojslaw usando comentarios en Notion Control Room. El problema visible era que los comentarios correctivos no estaban produciendo efecto operativo observable.

## Hallazgos

1. `worker.notion_client.poll_comments` tenia un bug real:
   - hacia una sola lectura efectiva en la practica
   - comparaba `created_time` y `since` como strings
   - no recorria bien el backlog de comentarios

2. `dispatcher.notion_poller._do_poll` tenia un bug mas grave:
   - leia `comments` en la raiz de la respuesta
   - pero `WorkerClient.run()` devuelve `{"ok": ..., "result": {...}}`
   - por lo tanto el poller no estaba consumiendo comentarios nuevos aunque el worker respondiera `200`

3. El canal de mensajeria `scripts/post_notion_message.py` no era fiable para mensajes con espacios:
   - tomaba solo `sys.argv[1]`
   - al hablarle a Rick desde scripts/remoto el mensaje podia truncarse

4. Incluso con el poller arreglado, una correccion operativa del tipo:
   - "Rick, el caso Kris Wojslaw sigue abierto..."
   caia como `echo` y se perdia como un simple `Rick: Recibido.`

## Cambios aplicados

### 1. Poller de comentarios

- `worker/notion_client.py`
  - parseo real de datetimes Notion
  - paginacion de `/comments`
  - retorno ordenado de comentarios no vistos

- `dispatcher/notion_poller.py`
  - soporte para payload real `result.comments`
  - comparacion de timestamps por datetime y no por string
  - avance correcto de `last_ts`
  - deduplicacion por `comment_id` en Redis para evitar doble procesamiento

### 2. Comunicacion remota a Rick

- `scripts/post_notion_message.py`
  - ahora acepta mensajes completos por `argv[1:]`
  - y tambien por `stdin`, lo que evita problemas de quoting remoto

### 3. Clasificacion y trazabilidad de instrucciones

- `dispatcher/intent_classifier.py`
  - se ampliaron verbos de instruccion/correccion (`corrige`, `rehaz`, `reabre`, `baja`, etc.)

- `dispatcher/smart_reply.py`
  - las instrucciones ya no solo acusan recibo
  - ahora tambien registran una tarea real en Notion via `notion.upsert_task`

## Validacion

- Tests locales:
  - `tests/test_notion_poll_comments.py`
  - `tests/test_notion_poller.py`
  - `tests/test_intent_classifier.py`
  - `tests/test_smart_reply.py`

- Resultado:
  - `61 passed`

- Smoke real en VPS:
  - comentario multi-palabra enviado por `stdin` a `post_notion_message.py`
  - comentario recibido por Control Room
  - respuesta de Rick generada por el poller
  - correccion del caso Kris clasificada como `instruction`
  - tarea real creada en Notion:
    - `Task ID = notion-instruction-3265f443`
    - titulo relacionado al caso Kris

## Conclusion operativa

Quedo corregida la parte tecnica y de trazabilidad del canal Notion -> Rick.

Pero la conclusion importante es esta:

- Control Room ya sirve para:
  - dejar instrucciones
  - recibir acuse
  - dejar tarea trazable en Notion

- Control Room todavia NO sirve como sustituto del canal principal de Rick para trabajo profundo de benchmark externo.
  - no ejecuta por si solo un benchmark tipo Kris
  - no reemplaza el flujo principal donde Rick trabaja con skills, browser, research, carpeta compartida y proyecto activo

En otras palabras:

- ya no se pierde la correccion
- pero tampoco conviene asumir que un comentario en Control Room va a re-hacer el benchmark por si mismo

## Recomendacion

Para benchmarks/referencias externas:

1. endurecer skills y guardrails del workspace de Rick
2. usar el canal principal de Rick para pedir el trabajo
3. usar Control Room para:
   - dejar correcciones
   - registrar seguimiento
   - crear trazabilidad cuando haga falta

