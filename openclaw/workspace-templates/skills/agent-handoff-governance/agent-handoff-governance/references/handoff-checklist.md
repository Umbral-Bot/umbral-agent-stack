# Handoff Checklist

## Uso rápido

Usar esta checklist para redactar, revisar o auditar un handoff antes de marcar progreso o cierre.

## 1. Elegir el mecanismo correcto

- **Subagente**: tarea acotada, especializada, dentro del mismo caso, con retorno esperado al solicitante.
- **Issue o sub-issue**: trabajo que debe persistir, requiere prioridad, ETA, seguimiento, visibilidad o dependencia explícita.
- **Update**: solo informar progreso o decisión en trabajo que ya tiene owner y tracking.

## 2. Verificar campos obligatorios

Confirmar que el handoff tenga:

- solicitante original;
- owner explícito;
- caso padre o proyecto;
- problema concreto;
- contexto mínimo suficiente;
- entregable esperado;
- criterio de aceptación;
- ETA o checkpoint;
- registro en Linear y/o Notion;
- condición exacta de cierre.

## 3. Verificar trazabilidad

### Linear

- issue o sub-issue creada si aplica;
- assignee definido;
- relación parent, blocked/blocking o related definida;
- comentario o descripción con el handoff;
- comentario de resolución del experto;
- comentario de integración del solicitante.

### Notion

- página o tarea enlazada al caso padre;
- owner en `Person`;
- ETA o checkpoint en `Date`;
- relación o backlink al contexto padre;
- comentario o sección de resolución;
- comentario o sección de integración.

## 4. Separar progreso real de fake progress

### Señales de progreso real

- existe tracking con owner y aceptación;
- hay resultado concreto del experto;
- el solicitante integró el resultado;
- el caso original recibió respuesta final.

### Señales de fake progress

- solo existe delegación o ping;
- no hay aceptación ni ETA;
- el estado cambió sin evidencia;
- se cerró por lanzar un subagente o abrir un ticket.

## 5. Evitar `NO_REPLY` mal usado

- Permitir `NO_REPLY` solo en housekeeping silencioso.
- Prohibir `NO_REPLY` para ocultar bloqueo, handoff, escalación o resolución pendiente.
- Exigir respuesta visible cuando el solicitante espera estado, resultado o decisión.

## 6. Revisar antes de cerrar

Cerrar solo si todo esto es cierto:

- el experto respondió;
- el criterio de aceptación se cumplió;
- el solicitante integró el resultado;
- el proyecto o caso original fue actualizado;
- el solicitante original recibió respuesta;
- cualquier riesgo residual quedó documentado.

## 7. Escalar si no hay respuesta

- pedir acuse de recibo si nadie tomó ownership;
- escalar al lead o owner alternativo cuando venza la ETA;
- si no hay ETA, escalar tras un día hábil sin acuse;
- actualizar al solicitante original con estado real y nuevo checkpoint.

## Ejemplos express

### Bueno

`owner=@data-agent, problema=validar causa raíz, aceptación=sql + conclusión + impacto, eta=hoy 17:00, linear=DATA-88`

### Malo

`¿alguien puede mirar esto?`
