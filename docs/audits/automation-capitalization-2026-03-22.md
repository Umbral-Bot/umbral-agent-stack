# Capitalizacion de automatizaciones Umbral - 2026-03-22

## Que habia y de donde salio

Se encontraron seis automatizaciones locales en `C:\Users\david\.codex\automations`:

- `monitoreo-umbral`
- `monitoreo-umbral-2`
- `monitoreo-umbral-3`
- `seguimiento-diario-umbral`
- `seguimiento-diario-umbral-2`
- `seguimiento-diario-umbral-3`

No eran seis automatizaciones distintas. Eran dos familias duplicadas:

- `Monitoreo Umbral`: mismo prompt, mismo repo, mismo schedule horario.
- `Seguimiento Diario Umbral`: mismo prompt, mismo repo, mismo schedule diario.

Los `created_at` muestran que se generaron casi seguidas el `2026-03-17`:

- primera tanda alrededor de `2026-03-17 04:55 UTC`
- segunda tanda segundos despues
- tercera tanda alrededor de `2026-03-17 04:56 UTC`

La variante `-3` solo cambia `reasoning_effort = "xhigh"`. El resto era duplicado funcional.

## Accion tomada

Las seis automatizaciones quedaron en `status = "PAUSED"` el `2026-03-22` para cortar ejecuciones redundantes.

## Resultado capitalizado

### 1. Estado operativo real del stack

Lo mas valioso no fue la repeticion, sino la convergencia de diagnostico:

- El stack **si estuvo operativo en vivo** cuando la automatizacion corrio con acceso real a la VPS.
- `openclaw-gateway`, `worker` VPS, `worker` VM (`8088`) y `worker` interactivo VM (`8089`) respondieron saludablemente.
- Redis llego a estar limpio (`pending=0`, `blocked=0`).
- `scripts/openclaw_panel_vps.py` y `scripts/dashboard_report_vps.py --force` pudieron refrescar `OpenClaw` y `Dashboard Rick`.
- `Bandeja Puente` quedo accesible y vacia, que es muy distinto de "sin acceso".

### 2. Riesgos operativos persistentes

Las corridas tambien convergieron en riesgos que siguen abiertos:

- El camino de recuperacion por tunel reverso `127.0.0.1:28088/28089` quedo degradado o innecesario; ambas rutas seguian haciendo timeout en `/health`.
- La VM llego a alternar entre caida, online por relay y online directa; la conectividad no esta endurecida del todo.
- En la VPS llegaron a coexistir **dos procesos `dispatcher.service`** aunque el servicio apareciera inconsistente en `systemctl`.
- El worker de VM publica menos handlers que el worker VPS: faltan `notion.upsert_deliverable` y `notion.upsert_bridge_item`.

### 3. Deuda operativa en Notion y proyectos

La señal mas consistente de las automatizaciones fue de gobernanza y cierre humano:

- `deliverables_pending_review` subio de `3` a `4` segun los cortes mas recientes.
- Persisten entregables vencidos en Editorial, Embudo y Granola.
- `tasks_unlinked` bajo de `7` a `4`, pero las restantes siguen siendo duplicados `queued` de Granola.
- `Bandeja Puente` quedo limpia y operativa, pero sin items vivos.
- Los proyectos con mas drift/atencion repetidos en casi todos los cortes fueron:
  - `Sistema Editorial Automatizado Umbral`
  - `Proyecto Granola`
  - `Auditoria Mejora Continua - Umbral Agent Stack`
  - `Autonomia RPA GUI en VM`
  - `Control de Navegador VM`
  - `Sistema Automatizado de Busqueda y Postulacion Laboral`

### 4. Drift de representacion

Las automatizaciones volvieron a marcar un mismo patron:

- `.agents/board.md` no refleja bien el trabajo mas reciente.
- Hay task files en `.agents/tasks/` que quedaron `assigned` o `blocked` aunque el board declare rondas cerradas.
- La capacidad documentada del sistema y su uso real siguen desalineados, especialmente en Editorial, Laboral y Granola.

## Sintesis ejecutiva util

Si hay que convertir todo esto en un plan accionable corto, la secuencia correcta es:

1. Dejar **un solo dispatcher** vivo y coherente con el metodo de arranque.
2. **Resincronizar el deployment del worker VM** para recuperar los handlers Notion faltantes.
3. **Revisar los 4 entregables vencidos/pedientes** y tomar decision humana.
4. **Curar las 4 tareas huerfanas de Granola**.
5. **Actualizar board y tasks** para que la representacion no siga atrasada respecto de la operacion real.

## Que no conviene perder

Aunque las automatizaciones se duplicaron, dejaron tres conclusiones utiles:

- la infraestructura principal ya no parece ser el cuello de botella dominante;
- la deuda principal paso a ser cierres humanos, drift y consistencia de deployment;
- correr esta clase de chequeo sirve, pero solo si queda una sola automatizacion canonica y con acceso real a VPS/Notion/Tailscale.
