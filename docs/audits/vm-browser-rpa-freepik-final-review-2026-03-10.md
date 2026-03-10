## Ejecutado por: codex

# Revisión final VM Browser / RPA / Freepik / Mejora Continua — 2026-03-10

## Objetivo

Cerrar la revisión final de cuatro frentes testeados en iteraciones separadas con Rick:

1. control de navegador en la VM
2. RPA GUI de la VM
3. uso de Freepik vía VM
4. equipo de mejora continua y tracking del sistema

## Resumen ejecutivo

### 1. Browser VM

Estado: **operativo**

- `browser.navigate`: OK
- `browser.read_page`: OK
- `browser.screenshot`: OK
- `browser.click`: OK
- `browser.type_text`: OK
- `browser.press_key`: OK

Conclusión:

- el navegador typed en la VM ya es una base real y usable

### 2. RPA GUI VM

Estado: **parcial-alto**

- input GUI: OK
- screenshot/visión GUI: OK por worker interactivo (`8089`)
- screenshot/visión GUI: FAIL por worker estándar (`8088`)

Conclusión:

- el agente puede mover/clickear/tipear
- el agente ya puede verificar visualmente el escritorio si entra por la ruta interactiva correcta
- ya quedó validado un flujo GUI simple sobre Notepad
- todavía falta validar un flujo GUI completo sobre una app objetivo más compleja

### 3. Freepik vía VM

Estado: **parcial-alto / viable**

- Freepik ya abre correctamente con browser headful
- login page accesible
- screenshot browser OK

Conclusión:

- la vía correcta para Freepik es browser typed headful
- no GUI RPA como primera opción

### 4. Mejora continua

Estado: **operativo**

- `notion poller`: OK
- `dashboard cron`: OK
- `daily digest`: OK
- `OODA report`: OK
- `notion.upsert_task`: OK
- cron de seguimiento de embudo: OK tras hardening

Conclusión:

- la infraestructura del frente de mejora continua quedó funcionando
- ya no está bloqueada por env ni por pathing básico

## Hardening adicional hecho en esta iteración

### Cron de seguimiento del embudo

Se detectó que seguía fallando el job:

- `Seguimiento cada 30 min — Proyecto embudo/Drive`

Primero fallaba por un bug de sesión del runtime de `main`.
Después de moverlo a `rick-ops`, quedó claro que el bloqueo real era otro:

- el prompt del cron intentaba revisar `G:\Mi unidad` demasiado arriba
- `windows.fs.list` en esa altura de ruta sigue siendo frágil

Fix aplicado:

- se dejó el job en `rick-ops`
- se le asignó session key propia:
  - `agent:rick-ops:cron:drive-check`
- se acotó el prompt a la ruta exacta:
  - `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas`

Resultado:

- `lastRunStatus: ok`
- `consecutiveErrors: 0`

## Qué quedó realmente corriendo

### VM Worker

- `umbral-worker.service`: activo
- browser typed usable en `8088`
- GUI input usable en `8088`

### VPS

- `openclaw-gateway.service`: activo
- `n8n.service`: activo
- crons principales: OK

## Qué sigue siendo límite real

### RPA GUI

El framebuffer útil sí existe, pero no en todos los caminos:

- `8088` sigue sin captura usable
- `8089` interactivo sí entrega captura útil

Eso hace que:

- GUI RPA deje de ser ciego cuando se enruta bien
- pero todavía no convenga dar por cerrado el frente hasta validar un flujo completo sobre una app real

### Freepik

Falta:

- login real
- flujo interno del sitio

Pero el camino técnico base ya quedó elegido y validado.

## Dónde quedó documentada cada iteración

- `docs/audits/browser-vm-control-validation-2026-03-10.md`
- `docs/audits/rpa-gui-vm-validation-2026-03-10.md`
- `docs/audits/freepik-vm-browser-validation-2026-03-10.md`
- `docs/audits/continuous-improvement-team-validation-2026-03-10.md`

## Veredicto final

El cierre honesto es este:

- Browser VM: listo
- Mejora continua: listo
- Freepik VM: base lista, flujo final pendiente
- RPA GUI VM: listo como baseline técnico, pendiente de validación e2e sobre app real

La estrategia correcta del stack quedó clara:

1. browser typed/headful primero
2. GUI visual + input por worker interactivo como segundo canal
3. no confiar en `8088` para GUI visual
4. PAD solo como última alternativa
