# Rick Competitive Benchmark Hardening - 2026-03-12

## Contexto

En un test real, David pidio a Rick estudiar en profundidad el caso de Cristian Talana como referencia para el proyecto embudo. Rick si consulto fuentes reales, pero cerro demasiado pronto:

- uso la captura aportada por David;
- hizo `web_fetch` de la landing `lp.cristiantala.com/linkedin-cheatsheets/`;
- hizo `web_fetch` del sitio `cristiantala.com`;
- no dejo evidencia suficiente de browser real ni de inspeccion profunda del post de LinkedIn.

El resultado fue tacticamente util, pero no cumplio el estandar de "estudiarlo en profundidad".

## Causa raiz

No era un problema de modelo. La brecha principal era de runtime y skilling:

1. faltaba una regla explicita de benchmark profundo;
2. Rick podia cerrar con una sola landing o una captura;
3. no existia una skill especifica para teardown competitivo/funnel;
4. no estaba obligado a separar evidencia observada de inferencia.

## Cambios aplicados

### Runtime

Se endurecieron los prompts base de Rick en:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`

Se anadieron reglas para:

- exigir evidencia multiple en benchmarks externos;
- exigir teardown minimo para casos de LinkedIn/funnel;
- marcar como `no verificado` cualquier parte no observada directamente.

### Skills

Se anadio y reforzo la skill:

- `openclaw/workspace-templates/skills/competitive-funnel-benchmark/SKILL.md`

Con referencias operativas:

- `references/teardown-template.md`
- `references/evidence-checklist.md`
- `references/linkedin-benchmark-format.md`

Tambien se aclaro en:

- `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`

que esa skill no reemplaza un teardown profundo de persona/funnel.

## Despliegue

Las reglas endurecidas y la skill nueva quedaron sincronizadas a la instalacion viva de OpenClaw en la VPS para:

- `main`
- `rick-orchestrator`
- `rick-tracker`
- `rick-delivery`
- `rick-qa`
- `rick-ops`

El gateway se reinicio despues de la sincronizacion.

## Re-test controlado

Se ejecuto una corrida aislada de Rick en la VPS, sin depender de Telegram, usando el mismo caso de Cristian Talana.

### Evidencia observada en traza real

Rick ya no se quedo solo con una captura o una landing. Esta vez cubrio multiples fuentes con browser real:

1. post de LinkedIn de Cristian Tala:
   - `umbral_browser_navigate`
   - `umbral_browser_read_page`
2. landing `lp.cristiantala.com/linkedin-cheatsheets/`:
   - `umbral_browser_navigate`
   - `umbral_browser_read_page`
3. continuidad del funnel / comunidad:
   - `https://www.skool.com/cagala-aprende-repite`
   - `umbral_browser_navigate`
   - `umbral_browser_read_page`

### Resultado

El benchmark paso de "parcial util" a "parcial solido" porque ahora:

- hay evidencia directa del post principal;
- hay evidencia directa de la landing;
- hay evidencia directa de la continuidad del funnel;
- la respuesta final se apoya en navegacion real, no solo en captura + inferencia.

### Limite actual

Todavia no hay evidencia automatica de una inspeccion profunda de:

- comentarios del post;
- primer comentario;
- thank-you page o continuidad privada detras del opt-in.

Para el objetivo del prompt actual, el sistema ya esta listo para re-testear a Rick con una base razonablemente robusta.
