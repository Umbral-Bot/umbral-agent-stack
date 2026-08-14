# SIM fuera de cron — closeout (PKG-MACRO-P5-CRON-T1, 2026-08-14)

**Q8 de la entrevista 2026-08-13 = A:** quitar SIM de `scripts/vps/install-cron.sh`.
Este documento es el closeout canónico. **Donde choque con el reconteo E-6 fila 35
/ E-p12, gana éste.**

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
  correr el instalador, saca del crontab cualquier línea con `sim-report-cron.sh`
  o `sim-to-make-cron.sh`. Un re-run ahora **sanea en vez de reinstalar**, que
  era el agujero. Probado en aislamiento con un `crontab` falso: quita las líneas
  SIM preservando el resto, es idempotente, y no rompe con crontab vacío.
- Los wrappers `sim-report-cron.sh`, `sim-to-make-cron.sh` y `sim-daily-cron.sh`
  **no se borran**: quedan como histórico, con una nota al tope de que están
  retirados y no deben reinstalarse. (`sim-daily-cron.sh` nunca estuvo en el
  instalador; lleva la nota igual para que nadie lo reenganche.)
- Test de no-regresión (`tests/test_install_cron_sim_retired.py`, 9 casos) que
  lee el instalador como texto y falla si reaparecen las variables, si alguien
  reinstala inline sin variable, o si el filtro de strip desaparece o queda
  decorativo. Verificado por mutación: **5 de 5** regresiones detectadas.

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
| Filtro de strip | presente para los dos scripts |
| Wrappers | los 3 conservados y marcados |

**No habilitar SIM en cron.** Si alguna vez se quiere de vuelta, es una decisión
explícita: hay que volver a agregarlo al instalador y sacar el filtro de strip,
y este documento tendría que dejar de valer.
