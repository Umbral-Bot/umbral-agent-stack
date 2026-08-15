# SIM fuera de cron — closeout (PKG-MACRO-P5-CRON-T1, 2026-08-14)

**Q8 de la entrevista 2026-08-13 = A:** quitar SIM de `scripts/vps/install-cron.sh`.
Este documento es el closeout canónico. **Donde choque con el reconteo E-6 fila 35
/ E-p12, o con la tabla de crons de `docs/62-operational-runbook.md`, gana éste.**

## Qué estaba mal

El crontab vivo ya no tenía SIM — los logs quedaron congelados el **2026-07-19**.
Pero el instalador seguía declarando `SIM_REPORT_LINE` y `SIM_TO_MAKE_LINE`, y
las re-agregaba en cada corrida. O sea: **el retiro a mano no era durable.** El
próximo que corriera `install-cron.sh` por cualquier otro motivo reinstalaba SIM
sin enterarse.

## Qué se hizo

- `install-cron.sh` **ya no declara ni instala** SIM: fuera las dos variables y
  los dos bloques.
- En su lugar quedó un **filtro de strip** al estilo del split de dashboard: al
  correr el instalador, saca del crontab cualquier línea con `sim-report-cron.sh`,
  `sim-to-make-cron.sh` **o `sim-daily-cron.sh`**. Un re-run ahora **sanea en vez
  de reinstalar**, que era el agujero.
- `sim-daily` entra al filtro aunque el instalador **nunca** lo haya instalado:
  se ponía a mano (audit 2026-07-17) y por eso es el más propenso a volver por
  la puerta de atrás. Sacarlo del filtro dejaría retirado-pero-no-saneado justo
  al único de los tres que históricamente entró por fuera.
- **El runbook operativo** (`docs/62-operational-runbook.md`) listaba los tres
  crons SIM en su tabla de crons instalados. El código quedaba durable y la
  documentación no: quien reconstruyera el crontab siguiendo el runbook los
  reinstalaba a mano. Las tres filas quedaron tachadas y marcadas como retiradas.
- Los wrappers `sim-report-cron.sh`, `sim-to-make-cron.sh` y `sim-daily-cron.sh`
  **no se borran**: quedan como histórico, con una nota al tope de que están
  retirados y no deben reinstalarse. (`sim-daily-cron.sh` nunca estuvo en el
  instalador; lleva la nota igual para que nadie lo reenganche.)
- Test de no-regresión (`tests/test_install_cron_sim_retired.py`, **14 casos**)
  en dos capas. La de texto falla si reaparecen las variables, si alguien
  reinstala inline, o si el filtro desaparece o queda decorativo. La de
  **comportamiento** ejecuta el bloque de verdad contra un `crontab` falso en
  `PATH` — nunca el real — y cubre los cuatro casos: con SIM, ya limpio, vacío, y
  el crontab que es *sólo* SIM, que es el que aborta el instalador entero si
  alguien saca el `|| true` bajo `set -euo pipefail`.
  Verificado por mutación: **11 de 11** regresiones detectadas. Tres de ellas
  —quitar `|| true`, cambiar `grep -vF` por `grep -v`, invertir la condición—
  sólo las caza la capa de comportamiento; con los tests de texto solos habrían
  pasado en verde.

## Qué NO se hizo, a propósito

- **No se corrió el instalador contra el crontab vivo.** El repo queda correcto;
  aplicar el strip en producción es un GO aparte, y hoy no hace falta porque no
  hay nada que sacar.
- **No se tocó el código Python.** `scripts/sim_to_make.py` sigue vivo y usable
  **a mano** — de hecho acaba de arreglarse en #650, donde dejó de mandar
  reportes vacíos a Make.com. Que ande mejor no lo vuelve candidato a cron.
- **Composite y `sim_to_make` siguen fuera de cron.** Un turno de composite son
  ~200 s contra un gateway compartido; habilitarlo es otra decisión.

## Estado verificado (2026-08-14)

| | |
|---|---|
| Líneas SIM en el crontab vivo | **0** (`grep` → `EXIT:1`, 14 líneas en total) |
| `SIM_*_LINE` en el instalador | **0** |
| Filtro de strip | presente para los **3** scripts |
| Wrappers | los 3 conservados y marcados |
| Runbook operativo | las 3 filas SIM tachadas y marcadas |

**No habilitar SIM en cron.** Si alguna vez se quiere de vuelta, es una decisión
explícita: hay que volver a agregarlo al instalador y sacar el filtro de strip,
y este documento tendría que dejar de valer.
