# OpenClaw dashboard follow-up opportunities

Fecha: 2026-03-16  
Autor: Codex

## Revisión posterior al hardening

Se revisó nuevamente la shell `OpenClaw` ya desplegada en VPS y su renderer local.

## Mejoras aplicadas en esta pasada

1. **Menor riesgo de dejar la página rota**
   - El renderer ahora construye `snapshot` y `panel_blocks` antes de borrar la región vieja.
   - Esto reduce el riesgo de dejar la página vacía si falla un query intermedio.

2. **Deletes con verificación real**
   - `_delete_blocks()` ahora valida la respuesta de Notion en vez de asumir éxito.

3. **Priorización más útil**
   - Entregables ordenados por `Fecha limite sugerida` y prioridad de revisión.
   - Proyectos ordenados por severidad real:
     - bloqueos primero,
     - luego `Issues abiertas`,
     - luego menor tracción (`task_count`).
   - `Bandeja viva` ordenada por `Último movimiento`.

4. **Validación de shell más estricta**
   - ya no basta con `callout` + `Bases operativas`
   - ahora se exige la presencia de headings clave:
     - `Resumen operativo`
     - `Entregables por revisar`
     - `Proyectos que requieren atencion`
     - `Bandeja viva`
     - `Proximos vencimientos`
     - `Accesos rapidos`
     - `Bases operativas`

## Oportunidades todavía abiertas

### 1. Bandeja Puente sigue fuera del flujo real

El renderer ya no se rompe por esto, pero sigue siendo una deuda operativa:

- la integración Rick no tiene acceso actual a `Bandeja Puente`
- por eso el KPI y la tabla quedan honestamente en modo degradado

Acción recomendada:

- recompartir la base con la integración Rick
- o reemplazar `Bandeja Puente` por una base nueva oficialmente soportada

### 2. `OpenClaw` sigue siendo shell generada, no linked views nativas

La página ya no es texto suelto, pero sigue siendo una shell escrita por script:

- tarjetas KPI
- tablas compactas
- navegación preservada

No está usando linked database views ni board views nativos.

Acción recomendada:

- si el workspace y tooling de Notion quedan estables, migrar la shell a vistas nativas manuales y dejar el script en modo `summary-only`.

### 3. Quick access todavía mezcla accesos operativos y de contexto

`Accesos rapidos` hoy contiene:

- `Dashboard Rick`
- `Proyecto Multiagente v3`
- `Lovable - Rick`
- `Perfil David Moreira`

Sirve, pero no está optimizado.

Acción recomendada:

- decidir una política:
  - o `Accesos rapidos` = solo accesos operativos,
  - o `Accesos rapidos` = atajos humanos de contexto

## Estado final de esta pasada

- shell viva: estable
- validación local: OK
- refresh remoto: OK
- riesgo de corrupción parcial: reducido
- priorización: mejorada
- deuda principal restante: `Bandeja Puente` fuera de alcance para la integración
