---
name: make-com
description: >-
  Design and debug Make.com (formerly Integromat) automation scenarios using
  modules, webhooks, routers, filters, iterators, aggregators, and built-in
  functions for no-code/low-code integrations.
  Use when "create make scenario", "make.com automation", "make webhook",
  "make router", "make filter", "make module", "make iterator", "make aggregator",
  "integromat scenario", "make functions", "schedule make scenario",
  "connect apps in make", "make error handler", "make api".
metadata:
  openclaw:
    emoji: "\U0001F504"
    requires:
      env: []
---

# Make.com Skill

Rick puede asistir en el diseño, depuración y optimización de escenarios Make.com — la plataforma de automatización visual (antes llamada Integromat).

Documentación oficial: https://www.make.com/en/help/ | https://developers.make.com/

---

## Conceptos fundamentales

| Concepto | Descripción |
|----------|-------------|
| **Scenario** | Flujo de automatización compuesto por módulos conectados |
| **Module** | Bloque individual (acción, trigger, función o utilidad) |
| **Bundle** | Unidad de dato que fluye entre módulos (equivale a "ítem" en n8n) |
| **Trigger** | Módulo que inicia el escenario (instant o polling) |
| **Instant trigger (webhook)** | Trigger que responde inmediatamente a un evento entrante |
| **Polling trigger** | Make consulta el servicio cada N minutos en busca de nuevos datos |
| **Router** | Divide el flujo en múltiples ramas (caminos paralelos) |
| **Filter** | Condición en una conexión — el bundle pasa solo si la condición es verdadera |
| **Iterator** | Descompone un array en bundles individuales |
| **Aggregator** | Combina múltiples bundles en uno solo (ej: array, string, tabla) |
| **Error handler** | Ruta alternativa cuando ocurre un error en un módulo |

---

## Módulos clave (built-in y universales)

### HTTP / Webhooks

| Módulo | Uso |
|--------|-----|
| **Webhooks → Custom webhook** | Recibir datos desde sistemas externos (URL única por webhook) |
| **HTTP → Make a request** | Llamar cualquier API REST con headers, query params, body |
| **HTTP → Make a Basic Auth request** | API con autenticación básica |
| **HTTP → Make an API Key Auth request** | API con API key en header |
| **HTTP → Make an OAuth 2.0 request** | API con OAuth 2.0 |
| **Webhooks → Webhook response** | Responder al sistema que llamó el webhook con custom body/status |

### Flujo y control

| Módulo | Uso |
|--------|-----|
| **Flow Control → Router** | Dividir en ramas (hasta 10); cada rama puede tener su filtro |
| **Flow Control → Repeater** | Repetir un conjunto de módulos N veces |
| **Flow Control → Iterator** | Descomponer array en bundles individuales |
| **Flow Control → Array aggregator** | Reunir bundles en un array |
| **Flow Control → Numeric aggregator** | Sumar, promediar, contar bundles |
| **Flow Control → Text aggregator** | Unir texto de múltiples bundles |
| **Flow Control → Table aggregator** | Crear tabla/CSV a partir de bundles |
| **Tools → Set variable** | Guardar valor para usar en módulos posteriores |
| **Tools → Get variable** | Recuperar variable guardada |
| **Tools → Sleep** | Pausa en segundos |
| **Tools → JSON → Parse JSON** | Convertir string JSON a estructura Make |
| **Tools → JSON → Create JSON** | Convertir estructura Make a string JSON |

## Expresiones y funciones

## Triggers más usados

### Instant (Webhook)
1. Agregar módulo **Webhooks → Custom webhook**
2. Make genera una URL única: `https://hook.make.com/abc123...`
3. El escenario se activa inmediatamente al recibir POST/GET
4. Usar **Webhooks → Webhook response** al final para responder al caller

### Polling (Schedule)
- El trigger hace polling cada 15 min (plan básico) o cada 1 min (planes superiores)
- Ejemplos: Gmail (nuevos emails), Google Sheets (nuevas filas), RSS (nuevos ítems)
- Make guarda el cursor/timestamp del último dato procesado

### Schedule (Cron)
- En `Scenario settings → Scheduling` definir: cada X minutos, cada hora, diariamente, etc.
- Para cron avanzado: usar el módulo **Tools → Sleep** + scheduler externo

---

## Filtros

Los filtros se configuran **entre módulos** (clic en la conexión entre dos módulos):

```
Condición: [Campo] [Operador] [Valor]

Operadores de texto: Equal to, Not equal to, Contains, Not contains, 
                     Starts with, Ends with, Matches pattern (regex)

Operadores numéricos: Equal to, Greater than, Less than, Between

Operadores de fecha: Equal to, After, Before, Between

Operadores booleanos: Equal to true/false

Operadores de null: Exists, Does not exist
```

**Ejemplo de filtro combinado (AND):**
```
Status = "active"
AND Amount > 1000
AND Email contains "@empresa.com"
```

---

## Funciones integradas de Make

Make tiene funciones agrupadas por tipo, accesibles al mapear campos:

### Texto

### Funciones de texto
```
toString(valor)
lower(texto)                      → minúsculas
upper(texto)                      → mayúsculas
trim(texto)                       → quitar espacios
length(texto)                     → número de caracteres
substring(texto; inicio; fin)     → subcadena (índices desde 1)
replace(texto; buscar; reemplazo)
contains(texto; subcadena)        → true/false
startsWith(texto; prefijo)
endsWith(texto; sufijo)
split(texto; delimitador)         → array
join(array; separador)            → string
```

### Funciones matemáticas
```
now                               → fecha y hora actual
formatDate(fecha; "DD/MM/YYYY")
formatDate(fecha; "YYYY-MM-DDTHH:mm:ssZ")
parseDate("04/03/2026"; "DD/MM/YYYY")
addDays(fecha; días)
addHours(fecha; horas)
dateDifference(fecha1; fecha2; "days")
setDay(fecha; día_del_mes)
setHour(fecha; hora)
startOfDay(fecha)
startOfMonth(fecha)
```

### Números y matemáticas

```
round(número; decimales)
floor(número)
ceil(número)
abs(número)
max(a; b)
min(a; b)
sum(array)
average(array)
parseNumber("1,234.56"; "1,234.56")
formatNumber(número; decimales; separador_decimal; separador_miles)
```

### Arrays / Colecciones

```
length(array)                     → cantidad de elementos
first(array)                      → primer elemento
last(array)                       → último elemento
get(array; índice)                → elemento por índice (desde 1)
add(array; elemento)              → agregar al final
remove(array; índice)             → eliminar por índice
merge(array1; array2)             → combinar arrays
map(array; clave)                 → extraer campo de objetos
filter(array; clave; valor)       → filtrar por campo
sort(array; dirección; clave)     → ordenar
slice(array; inicio; fin)         → subcorte
```

### Lógica y control

```
if(condición; valor_si_true; valor_si_false)
ifempty(valor; valor_si_vacío)
switch(valor; caso1; res1; caso2; res2; default)
and(cond1; cond2)
or(cond1; cond2)
not(condición)
```

---

## Router con filtros — Patrón común

```
[Webhook recibe solicitud]
         ↓
      [Router]
    /    |    \
   F1   F2   F3 (sin filtro = ruta default)
   ↓     ↓    ↓
[Accion1] [Accion2] [Accion3]
```

**Configuración de filtro en cada ruta:**
- Ruta 1: `tipo = "urgente"`
- Ruta 2: `tipo = "normal"`
- Ruta 3: *(sin filtro — todas las demás)*

---

## Manejo de errores

### Directivas de error en módulo

Hacer clic derecho en un módulo → `Add error handler`:

| Directiva | Comportamiento |
|-----------|---------------|
| **Ignore** | Ignora el error y continúa con el siguiente bundle |
| **Rollback** | Revierte todos los módulos marcados como "transaccionales" |
| **Commit** | Finaliza la transacción actual y comienza una nueva |
| **Resume** | Continúa desde el módulo después del fallado |
| **Break** | Guarda el bundle en "Incomplete executions" para reintentar |
| **Retry** | Reintenta el módulo automáticamente |

### Error handler route

```
[Módulo con error]
    ├── Éxito → Siguiente módulo normal
    └── Error → [Error handler] → Notify Slack → Log in Notion
```

---

## API de Make.com

La API permite gestionar escenarios programáticamente:

### Autenticación
```bash
curl -H "Authorization: Token TU_API_TOKEN" \
  https://eu1.make.com/api/v2/scenarios
```

### Endpoints principales

```
GET  /api/v2/scenarios                     # Listar escenarios
GET  /api/v2/scenarios/{id}                # Detalle de escenario
POST /api/v2/scenarios/{id}/run            # Ejecutar escenario manualmente
GET  /api/v2/scenarios/{id}/logs           # Logs de ejecuciones
POST /api/v2/scenarios                     # Crear escenario
PATCH /api/v2/scenarios/{id}              # Actualizar escenario
GET  /api/v2/connections                   # Listar conexiones/credenciales
GET  /api/v2/webhooks                      # Listar webhooks
```

### Ejecutar escenario con datos vía API

```bash
# POST a un webhook de Make con datos
curl -X POST "https://hook.make.com/abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{"evento": "nuevo_lead", "nombre": "Juan", "email": "juan@empresa.com"}'
```

---

## Integración con Umbral Agent Stack

Make.com se integra con el Worker de Umbral como orquestador externo:

```json
// Módulo HTTP → Make a request
// URL: http://tu-vps:8088/execute
// Method: POST
// Headers: Authorization: Bearer {{WORKER_TOKEN}}
// Body:
{
  "task_type": "research.web",
  "input": {
    "query": "{{1.search_term}}",
    "max_results": 5
  },
  "callback_url": "https://hook.make.com/TU_WEBHOOK_DE_RESPUESTA"
}
```

El Worker ejecuta la tarea y notifica al webhook de Make cuando termina (si se configura `callback_url`).

---

## Casos de uso típicos

- Recibir lead desde formulario web → enriquecer con API → agregar a CRM + notificar en Slack.
- Monitorear menciones en RSS/Twitter → clasificar con LLM → postear resumen en Notion.
- Procesar facturas PDF entrantes → extraer datos → registrar en Google Sheets + enviar aprobación.
- Sincronizar contactos entre HubSpot y Pipedrive en tiempo real.
- Automatizar reportes: Make dispara workflow → llama al Worker de Umbral → postea en Notion.
- Trigger de Power Automate → webhook de Make → continúa el flujo en Make para lógica compleja.

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `422 Unprocessable Entity` | Datos requeridos faltantes o formato incorrecto | Verificar estructura del payload con un módulo HTTP de prueba |
| `429 Too Many Requests` | Rate limit de la app destino | Agregar módulo **Tools → Sleep** entre iteraciones |
| `Scenario stopped due to error` | Módulo falló sin handler | Configurar Error Handler en el módulo o directiva "Break" |
| `Webhook data structure was modified` | Se actualizó la estructura pero Make no la re-detectó | Clic en "Re-determine data structure" en el módulo webhook |
| `Bundle not processed` | Filtro rechazó el bundle | Revisar condiciones del filtro; activar "Fall through" para diagnóstico |
| `Connection expired` | OAuth token vencido | Ir a Connections → reconectar la credencial |
| `Array aggregator returns empty` | Iterator procesó 0 bundles | Verificar que el módulo fuente devuelva datos; revisar el campo mapeado como array |
| Campos vacíos en mapeo | Campo no existe en la estructura | Usar `ifempty({{campo}}; "default")` para manejar nulos |

## Documentación oficial

## Buenas prácticas

- **Usar nombres descriptivos** en módulos: clic derecho → Rename.
- **Notas en módulos** (clic derecho → Add a note) para documentar lógica.
- **Incomplete executions**: activar en `Scenario settings → Incomplete executions → Store data` para poder reintentar bundles fallados.
- **Staging vs. Producción**: crear escenario duplicado para testing antes de activar en producción.
- **Variables reutilizables**: usar `Tools → Set variable` / `Get variable` para valores usados múltiples veces.
- **Limitar datos procesados**: en triggers de polling, configurar un límite razonable de ítems por ejecución.
- **Webhook response siempre**: responder al caller con `Webhooks → Webhook response` para evitar timeouts en el sistema que llamó.
- **Monitorear con History**: revisar el historial de ejecuciones regularmente para detectar errores silenciosos.

---

## Referencias

- Documentación oficial: https://www.make.com/en/help/
- API Developer: https://developers.make.com/api-documentation/
- Funciones built-in: https://www.make.com/en/help/functions
- Academy (cursos): https://academy.make.com/
- Plantillas: https://www.make.com/en/templates
