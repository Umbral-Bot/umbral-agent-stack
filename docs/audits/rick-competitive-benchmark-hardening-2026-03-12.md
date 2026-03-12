# Rick Competitive Benchmark Hardening — 2026-03-12

## Contexto

En un test real, David pidió a Rick estudiar en profundidad el caso de Cristian Talana como referencia para el proyecto embudo. Rick sí consultó fuentes reales, pero cerró demasiado pronto:

- usó la captura aportada por David;
- hizo `web_fetch` de la landing `lp.cristiantala.com/linkedin-cheatsheets/`;
- hizo `web_fetch` de `cristiantala.com`;
- no dejó evidencia de browser real ni de inspección profunda del post de LinkedIn.

El resultado fue tácticamente útil, pero no cumplió el estándar de "estudiarlo en profundidad".

## Causa raíz

No era un problema de modelo. La brecha principal era de runtime y skilling:

1. faltaba una regla explícita de benchmark profundo;
2. Rick podía cerrar con una sola landing o una captura;
3. no existía una skill específica para teardown competitivo/funnel;
4. no estaba obligado a separar evidencia observada de inferencia.

## Cambios aplicados

### Runtime

Se endurecieron los prompts base de Rick en:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`

Se añadieron reglas para:

- exigir evidencia múltiple en benchmarks externos;
- exigir teardown mínimo para casos de LinkedIn/funnel;
- marcar como `no verificado` cualquier parte no observada directamente.

### Skills

Se añadió la skill nueva:

- `openclaw/workspace-templates/skills/competitive-funnel-benchmark/SKILL.md`

Y se aclaró en:

- `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`

que esa skill no reemplaza un teardown profundo de persona/funnel.

## Efecto esperado

Ante pedidos como:

- estudiar un referente en profundidad;
- analizar un perfil de LinkedIn como landing;
- evaluar un lead magnet;
- comparar un funnel externo con Umbral;

Rick debería ahora:

1. cubrir varias fuentes;
2. no cerrar solo con una landing;
3. separar evidencia observada de inferencia;
4. producir un teardown reutilizable para Umbral.

## Pendiente

Sincronizar estas reglas y la nueva skill a la instalación viva de OpenClaw en la VPS para que el runtime de Rick las use en producción.
