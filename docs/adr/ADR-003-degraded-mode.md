# ADR-003: Modo Degradado

## Estado
Aceptado — 2026-02-27

## Contexto
La VM Windows no siempre está encendida. Algunos proveedores LLM tienen cuotas o pueden caerse. El sistema necesita operar de forma resiliente ante fallos parciales.

## Decisión
**Definir niveles de degradación explícitos con acciones automáticas.**

### Niveles

| Nivel | Condición | Capacidad | Acción |
|-------|-----------|-----------|--------|
| **Normal** | Todos los componentes UP | 100% | Operación estándar |
| **Partial** | VM offline | Solo LLM + Notion | Encolar tareas VM; alertar David |
| **Limited** | VM offline + proveedor caído | LLM fallback + Notion | Usar fallback chain; alertar David |
| **Minimal** | Solo VPS + OpenClaw | Telegram + mensajes | Registrar todo; alertar URGENTE |

### Detección
- Health check al Worker cada 60s: `GET /health`
- Si 3 checks consecutivos fallan → marcar VM como offline
- Si proveedor LLM retorna 429/503 → activar fallback chain
- Si fallback chain agotada → nivel Minimal

### Comportamiento por nivel
- **Partial**: Tareas `LLM-only` se ejecutan normalmente. Tareas con `capabilities_required: [vm]` se encolan con status `blocked`. David recibe notificación con lista de tareas en cola y ETA estimada.
- **Limited**: Igual que Partial + modelo secundario activo. Log de cada fallback en Langfuse.
- **Minimal**: Solo registro de instrucciones. Rick responde "Capacidad reducida — VM y proveedores no disponibles" + lista de lo pendiente.

## Razones
1. La VM se apaga cuando el host Windows duerme o reinicia.
2. Los proveedores LLM tienen rate limits y outages.
3. David necesita saber qué está pasando sin tener que investigar.
4. Es mejor encolar que perder tareas.

## Consecuencias
- El VPS necesita Redis para la cola de tareas bloqueadas.
- El Health Monitor es un componente crítico que corre en VPS.
- Al restaurarse la VM, se procesan tareas encoladas (FIFO).
