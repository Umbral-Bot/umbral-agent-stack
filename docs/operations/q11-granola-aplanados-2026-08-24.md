# Q11-T6 — Los 4 "aplanados" no estaban rotos: eran monólogos — 2026-08-24

Cierre de `PKG-MACRO-P5-Q11-T6`. T5 (#665) dejó 4 archivos fuera de Notion con
`--exclude` porque la auditoría los clasificó `VERBATIM_APLANADO`. David
preguntó por qué y pidió repararlos. La reparación resultó ser otra cosa que la
esperada.

## Qué son realmente

Los 4 del gap, por nombre real de la carpeta:

| Archivo | chars | líneas | `Me:` | `Them:` | turnos |
|---|---|---|---|---|---|
| `Conecta 3 -USM.md` | 73 320 | 2 | 1 | 1 | 2 |
| `Lleve la IA al flujo de trabajo… y al flujo empresarial.md` | 28 784 | 1 | 0 | 1 | 1 |
| `Promueva el crecimiento con la productividad y seguridad basada en IA .md` | 15 461 | 4 | 2 | 2 | 4 |
| `Webinar Microsoft Transforme su pequeña o mediana empresa en una Frontier Firm.md` | 20 329 | 1 | 0 | 1 | 1 |

La hipótesis de trabajo era "el pegado perdió los saltos de línea". Tres
medidas la descartan:

1. **No hay marcadores mid-línea que recuperar.** `Conecta 3 -USM.md` contiene
   exactamente **2** ocurrencias de `Me:`/`Them:` en todo el cuerpo, y son las
   2 de inicio de línea. No hay turnos corridos: no hay turnos.
2. **El `.md` crudo tiene 5–8 saltos de línea en total**, todos en la cabecera.
   El cuerpo es genuinamente una línea.
3. **~83–125 caracteres por frase.** Prosa continua normal, no turnos
   concatenados.

Cero separadores ocultos: sin NBSP, sin `U+2028`, sin espacios dobles, sin
caracteres de control más allá de 0–3 por archivo.

Tres de los cuatro son **webinars**; el cuarto es una presentación con una
intro corta. Granola etiquetó la sesión entera como un solo turno `Them:`
porque hablaba una sola persona. Eso no es un defecto del pegado — es una
descripción correcta de lo que pasó en la reunión.

**La conclusión que importa: el contenido siempre estuvo completo.** Lo que
estaba mal era la clasificación.

## El split, y por qué igual se implementó

`unflatten_transcript()` en `granola_drive_md_ingest.py`: cuando una línea del
cuerpo llega o supera `FLATTENED_LINE_CHARS` (5 000), inserta saltos antes de
cada etiqueta que aparezca **en medio de línea**.

El vocabulario es cerrado: `Me` y `Them` (las de Granola) más las que ya
demostraron ser etiquetas empezando alguna línea de ese mismo archivo. Eso es
lo que impide que la prosa se haga trizas en cada `Entonces:` o `https:`. Y
sólo cambia espacios en blanco — la corrida de espacios previa a la etiqueta se
vuelve un salto — así que ninguna transcripción puede perder contenido acá.

> **Efecto real sobre la carpeta: cero.** Los 118 archivos actuales salen del
> split byte-idénticos, porque ninguno tiene marcadores mid-línea. Es
> maquinaria para un modo de falla que todavía no se observó. Vale la pena
> igual: si un pegado llega realmente corrido, se repara solo en vez de entrar
> a Notion como un párrafo de 70 k. Pero no fue lo que desbloqueó a estos 4.

Se aplica dentro de `parse_drive_transcript_md`, no en el auditor ni en el
feeder, para que la clasificación del gap, la auditoría de completitud y el
cuerpo que efectivamente se escribe en Notion vean exactamente los mismos
turnos.

## Lo que sí desbloqueó: `EXECUTABLE_CLASSES`

```python
EXECUTABLE_CLASSES = frozenset({VERBATIM, VERBATIM_FLATTENED})
```

`VERBATIM_APLANADO` pasa a ejecutable. Un cuerpo aplanado es contenido
**completo**; retenerlo significaba que una reunión real nunca llegaba a Notion
por una forma que no es un defecto.

`SOLO_RESUMEN`, `VACIO` y `DUDOSO` siguen afuera: esos son cuerpos cortos o no
reconocidos, es decir, contenido que sí puede estar faltando.

Único no-ejecutable que queda en la carpeta: `BIM Forum 3.md` (1 163
caracteres, ya ingerido, `skip`).

## Corrida

```
$ python scripts/vm/granola_drive_feeder.py --execute --max-creates 4 --max-updates 0
{"drive_files": 118, "notion_pages": 151,
 "gap": {"create": 4, "update_transcript": 0, "skip": 114, "review_ambiguous": 0},
 "selected": 4, "excluded": 0, "written": 4, "declined": 0, "failed": 0, "execute": true}
```

Sin `--exclude`. Los 4 confirmados por el dry-run del worker antes de escribir
(`recon=create`, `matched=False`), ninguno declinado.

Verificación en Notion: las 4 existen como `Fuente=granola_drive_md` con
73 397 / 28 861 / 15 538 / 20 406 caracteres. **Notion 151 → 155 páginas**,
`granola_drive_md` 113 → 117.

**Gap final: `{"create": 0, "update_transcript": 0, "skip": 118}`.** Los 118
archivos elegibles de Drive están en Notion.

## Scheduled Task

Re-registrada 08:30 diaria **sin los 4 `--exclude`**, mismos caps (10 create /
1 update):

```
ANTES  : ... --max-creates 10 --max-updates 1 --exclude "Conecta 3 -USM.md" [+3] --execute
DESPUES: ... --max-creates 10 --max-updates 1 --execute
```

Corrida de verificación: `LastTaskResult: 0`, `excluded_requested: []`,
`notion_source: live`, gap 0, nada que hacer. `unmatched_exclusions` no quedó
pegado a nombres viejos porque ya no hay exclusiones.

## Cero capitalización

`notify_enlace=False`, `allow_legacy_raw_task_writes=False`, `Procesar con
agente=False`. Cero API/MCP de Granola, cero n8n, cero `openclaw.json`, cero
cron VPS. Ninguna variable de entorno tocada: la tarea arrancó sin problemas.

## Cambios de código

| Archivo | Cambio |
|---|---|
| `scripts/vm/granola_drive_md_ingest.py` | `unflatten_transcript()` + `turn_labels_in()` + `FLATTENED_LINE_CHARS`; aplicado en `parse_drive_transcript_md` |
| `scripts/vm/granola_drive_transcript_audit.py` | importa el umbral (una sola fuente); `VERBATIM_APLANADO` pasa a ejecutable |
| `tests/test_granola_drive_md_ingest.py` | +16 tests del split |
| `tests/test_granola_drive_transcript_audit.py` | política de ejecutables actualizada |

```
$ python -m pytest tests/ -q -k granola
471 passed
```

Del `/code-review`: sin el lookbehind `(?<=\S)`, el split se comía la sangría
propia de una línea larga y la convertía en salto, dejando una línea vacía al
inicio del cuerpo — un carácter de más, un párrafo en blanco en la página, y un
`reconcile` innecesario al re-ingerir. Corregido y fijado con test.
