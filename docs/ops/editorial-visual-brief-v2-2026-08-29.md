# Visual brief v2 - metaconfiguración de cinco alternativas

> Estado: contrato de código. Fecha: 2026-08-29. No implica deploy, corrida
> Magnific, escritura Notion ni modificación de la tanda Drive existente.

## Decisión

La derivación semántica vive **upstream en `rick-editorial`**. Rick lee el copy,
identifica el hecho central y su consecuencia, propone una metáfora núcleo y
deriva cinco ejes de variación. El Worker no vuelve a interpretar el artículo
con otro LLM: valida el brief y ensambla determinísticamente cinco prompts.

Esta frontera usa lo que ya existe:

- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` asigna la
  preparación de visual briefs a Rick Editorial;
- `docs/ops/rick-editorial-agent.md` registra que ese agente produjo el brief
  de HITL-2;
- `magnific.generate_variants` ya es el ejecutor, guard de estado y dueño de la
  transacción Notion/Drive, pero no recibe el copy completo ni tiene hoy un
  paso LLM editorial;
- `Visual brief` tiene un máximo de 2000 caracteres en
  `notion/schemas/publicaciones.schema.yaml`, por lo que persistir cinco prompts
  completos no es viable. El brief guarda campos comunes y cinco direcciones
  compactas; el Worker los expande.

Agregar un LLM dentro del Worker sumaría latencia, credenciales y otra capa de
fallo entre el gate humano y la generación. No hace falta para este contrato.

## Contrato YAML

Sólo `version: 2` o `version: v2` activa el modo nuevo.

```yaml
version: 2
central_fact: "Hecho o comportamiento central del copy"
ignored_consequence: "Consecuencia visible de ignorarlo"
core_metaphor: "Sujeto + condición inicial + transformación + fallo terminal"
invariants:                         # opcional; constantes en las cinco alts
  - "sujeto y causalidad compartidos"
variation_axes:                     # obligatorio: exactamente cinco, orden estable
  - axis: "eje controlado 1"
    direction: "tratamiento concreto para alt-1"
  - axis: "eje controlado 2"
    direction: "tratamiento concreto para alt-2"
  - axis: "eje controlado 3"
    direction: "tratamiento concreto para alt-3"
  - axis: "eje controlado 4"
    direction: "tratamiento concreto para alt-4"
  - axis: "eje controlado 5"
    direction: "tratamiento concreto para alt-5"
negative_prohibitions:              # obligatorio; prohibiciones semánticas
  - "no introducir un remedio que contradiga la consecuencia"
avoid:                              # opcional; fallos visuales clásicos
  - "texto incrustado"
engine: pro                         # opcional; default v2 = Pro
aspect_ratio: "4:3"
resolution: 2K
```

Reglas fail-closed:

- si el texto declara `version: 2`/`v2` pero el YAML es inválido, se rechaza;
  nunca degrada silenciosamente a legacy/Flash;
- `central_fact`, `ignored_consequence` y `core_metaphor` son texto no vacío;
- `variation_axes` contiene exactamente cinco mappings con `axis` y
  `direction` textuales y únicos;
- `negative_prohibitions` contiene al menos una prohibición textual;
- el brief completo no supera 2000 caracteres;
- cada prompt resultante no supera 3000 caracteres y conserva su eje,
  prohibiciones y el sufijo anti-slop;
- un `prompt` singular se rechaza en v2: no puede degradar el modo a un prompt
  por cinco samples;
- el índice es vinculante: `variation_axes[0]` produce `alt-1.png` y así hasta
  `variation_axes[4]` / `alt-5.png`.

Los valores del sandbox ganador no son plantilla. Cubos, nodos, grietas,
núcleos huecos, cortes, BIM, openBIM e IDS pueden aparecer en un brief de ese
caso, pero no existen en el parser, el ensamblador ni el contrato reusable.

## Ensamblaje de prompts

Cada prompt contiene:

1. metáfora núcleo, consecuencia, hecho central e invariantes compartidos;
2. **un solo** `axis` + `direction`, según la posición de la alternativa;
3. `negative_prohibitions`;
4. `avoid`;
5. el sufijo anti-slop y la paleta editorial vigentes.

Rick hace la derivación semántica; el Worker puede validar forma, cantidad y
unicidad, no juzgar por sí solo si una dirección cambia realmente un único eje.
Ese juicio sigue siendo QA/HITL y se prueba además con un segundo dominio.

## Preferencias compositivas HITL (2026-08-30)

Dos rondas de selección humana sobre `CAND-OLA3-03` (`publication_id`
`shortlist-CAND-OLA3-03-SHORTLIST-V1`) fijaron defaults compositivos para la
capa de derivación:

- La tanda live `20260830-0511` (los cinco ejes del fixture openBIM previo)
  la ganó `alt-3` — eje `encuadre`: primer plano contrastando sólo el estado
  inicial y el terminal. Perdieron tres estados con aire de hero, cuatro
  estados graduales, la diagonal ascendente y la sección del estado terminal.
- La tanda de variaciones ancladas a esa `alt-3` la ganó la alternativa de
  ironía de producto: acabado aún más de vitrina en el estado pulido con el
  defecto de origen aún más visible, a la vez. Perdieron más aire, un vacío
  interior más profundo, el cutaway y el crop más cerrado.

Destilado en tres reglas de forma: dos estados del mismo objeto enfrentados en
primer plano como composición base; acabado cosmético y evidencia del defecto
escalando juntos; revelado por daño orgánico visible, no por corte técnico.

Consecuencia por capa:

- las preferencias viven en la capa de derivación:
  `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` y la skill
  `openclaw/workspace-templates/skills/nano-banana-image-briefs/`;
- el parser y el ensamblador del Worker **no cambian**: siguen genéricos y
  sin plantilla, exactamente como define este contrato;
- los fixtures de prueba se realinearon como ejemplos conformes a la
  preferencia; siguen siendo evidencia/entrada de prueba, no templates
  runtime.

Son defaults de forma, no de contenido, y ceden ante una instrucción explícita
de David para un candidato concreto.

## Engine y trampa de aliases

| Campo v2 | Modelo canónico | Endpoint |
|---|---|---|
| omitido, `pro`, `nano-banana-pro`, `imagen-nano-banana-2` | `nano-banana-pro` | Pro |
| `flash`, `nano-banana-pro-flash`, `nano-banana-2`, `nano-banana-2-flash`, `imagen-nano-banana-2-flash` | `nano-banana-pro-flash` | Flash |

`nano-banana-2` **es Flash** en el Worker. El alias Magnific
`imagen-nano-banana-2` **es Pro**. V2 sólo acepta esas familias Pro/Flash;
Mystic no forma parte de este contrato. Un override operacional `model` tiene
precedencia, pero en v2 también queda restringido a Pro/Flash.

## Retrocompatibilidad

| Camino | Detección | Prompts | Default engine | Respuesta dry-run |
|---|---|---|---|---|
| v1/r3 | sin `version: 2`/`v2` | un prompt reutilizado en 5 samples | Flash | conserva `prompt` singular |
| v2 | marcador explícito | cinco prompts distintos | Pro | expone `prompts[5]` + ejes |

El constructor v1 (`scene` + `avoid` + sufijo), su fallback a
`Título`/`Premisa`, el override manual y los aliases existentes no cambian.
Valores de versión ausentes o no reconocidos siguen el camino legacy para no
reinterpretar briefs históricos.

La persistencia introducida por #680 tampoco cambia: cinco resultados en el
mismo orden, normalización PNG, carpeta Drive gobernada y un único patch final
de Notion. Un fallo conserva el set anterior.

## Dry-run sin efectos

Para una fila real ya generada, el modo nuevo hace una lectura Notion y permite
un brief de ejemplo sin modificar la propiedad:

```powershell
python scripts/editorial/magnific_generate_variants.py `
  --page-id <page-id> --dry-run --preview-only `
  --visual-brief-file tests/fixtures/editorial/visual_brief_v2_openbim.yaml
```

`preview_only` distingue el preview hipotético de la elegibilidad real:
`would_generate=false`, `hypothetical_preview=true` si la fila ya está
`Listo para selección`. Cero writes Notion, cero Drive y cero Magnific.

Para un segundo dominio sin Notion ni credenciales:

```powershell
python scripts/editorial/preview_visual_brief_v2.py `
  --brief-file tests/fixtures/editorial/visual_brief_v2_rfi.yaml
```

Ese comando usa el mismo parser, builder, resolución de engine, dimensiones y
sufijo que producción, y reporta contadores de llamadas externas en cero.

Los dos fixtures son evidencia/entrada de prueba, no templates runtime:

- `tests/fixtures/editorial/visual_brief_v2_openbim.yaml`;
- `tests/fixtures/editorial/visual_brief_v2_rfi.yaml`.

## No confundir con Stage 7 legacy

`docs/editorial-pipeline/stage7-visual-brief-spec.md` y el modelo
`scripts.discovery.lib.variants.VisualBrief` son un diseño Wave 1 distinto,
por variante y nunca cableado a este Worker. Sus campos `concept`,
`composition`, `mood` y `target_platform` no activan Visual brief v2. Este doc
define el contrato vivo de la propiedad Notion consumida por
`magnific.generate_variants`.

## Pruebas

- `tests/test_editorial_visual_brief.py`: parsing, campos obligatorios, cinco
  ejes únicos, límites y preview offline de otro dominio;
- `tests/test_magnific.py`: v1 intacto, v2 5/5, default Pro, Flash explícito,
  aliases, preview de fila terminada sin efectos y transacción Drive/Notion.

## Referencias

- `docs/ops/editorial-hitl-drive-2026-08-28.md`
- `docs/ops/editorial-magnific-p22-poller-2026-07-23.md`
- `docs/ops/rick-editorial-agent.md`
- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- `worker/tasks/magnific.py`
- `worker/tasks/editorial_visual_brief.py`
