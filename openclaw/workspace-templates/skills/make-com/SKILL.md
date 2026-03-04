---
name: make-com
description: >-
  Asistente para crear y depurar escenarios de automatización con Make.com
  (antes Integromat): módulos, webhooks, routers, iterators, agregadores,
  data stores y funciones integradas.
  Use when "make.com", "integromat", "escenario make", "módulo make",
  "webhook make", "router make", "automatización make", "make scenario",
  "función make", "data store make", "trigger make", "API make".
metadata:
  openclaw:
    emoji: "\U0001F9E9"
    requires:
      env: []
---

# Make.com Skill

Rick usa este skill para guiar la creación, depuración y optimización de escenarios de automatización con Make.com. Cubre escenarios, módulos, webhooks, routers, expresiones y la API de Make.

Fuente oficial: https://www.make.com/en/help/ y https://developers.make.com/

---

## Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Scenario** | Flujo automatizado compuesto de módulos conectados |
| **Module** | Bloque de acción: trigger, acción, búsqueda, iterador, agregador |
| **Bundle** | Unidad de datos que fluye entre módulos (equivalente a item/row) |
| **Trigger** | Módulo inicial que detecta un evento o inicia el escenario |
| **Router** | Módulo que divide el flujo en múltiples ramas condicionales |
| **Iterator** | Convierte un array en bundles individuales para procesar uno a uno |
| **Aggregator** | Combina múltiples bundles en uno solo (array u objeto) |
| **Data Store** | Base de datos simple integrada en Make para persistir datos |
| **Data Structure** | Esquema JSON que define la estructura de un data store o webhook |
| **Connection** | Autenticación guardada para un servicio externo |
| **Webhook** | URL única para recibir datos y disparar escenarios |
| **Queue** | Buffer de bundles pendientes de procesar (modo instant) |

---

## Tipos de módulos

| Tipo | Ícono | Función |
|------|-------|---------|
| **Trigger** | Reloj/rayo | Inicia el escenario (polling o instant webhook) |
| **Action** | Engranaje | Ejecuta una operación (crear, actualizar, enviar) |
| **Search** | Lupa | Busca y devuelve múltiples registros |
| **Aggregator** | Embudo | Une bundles en un solo bundle |
| **Iterator** | Flechas | Divide array en bundles individuales |
| **Router** | Bifurcación | Divide el flujo en rutas condicionales |
| **Converger** | Unión | Une rutas del router en una sola |
| **HTTP** | Globo | Llamada HTTP a cualquier API |
| **JSON** | Llaves | Parsear o crear JSON |

---

## Triggers — Modos de ejecución

| Modo | Descripción | Latencia |
|------|-------------|---------|
| **Polling (Scheduled)** | Make consulta la fuente según intervalo (1-60 min) | Minutos |
| **Instant (Webhook)** | La fuente envía datos a Make en tiempo real | Segundos |
| **Instant + Queue** | Procesa bundles uno a uno con cola FIFO | Segundos |

---

## Funciones integradas (Make formula language)

Make usa su propio lenguaje de funciones en los campos mapeados.

### Texto

```
{{lower(1.nombre)}}                    → minúsculas
{{upper(1.email)}}                     → mayúsculas
{{trim(1.descripcion)}}                → quitar espacios
{{length(1.texto)}}                    → cantidad de caracteres
{{substring(1.texto; 0; 50)}}          → primeros 50 chars
{{replace(1.nombre; "_"; " ")}}        → reemplazar
{{split(1.tags; ",")}}                 → string → array
{{join(1.lista; ", ")}}                → array → string
{{contains(1.texto; "error")}}         → true/false
{{startswith(1.url; "https")}}
{{endswith(1.archivo; ".pdf")}}
{{md5(1.password)}}                    → hash MD5
{{sha256(1.dato; "base64")}}
{{encodeURL(1.param)}}
{{decodeURL(1.param)}}
{{base64(1.texto)}}
{{toString(1.numero)}}
{{toNumber(1.texto)}}
```

### Fechas

```
{{now}}                                → timestamp actual
{{formatDate(now; "YYYY-MM-DD")}}
{{formatDate(now; "DD/MM/YYYY HH:mm"; "America/Argentina/Buenos_Aires")}}
{{addDays(now; -7)}}                   → hace 7 días
{{addHours(now; 2)}}
{{dateDifference(1.fechaFin; 1.fechaInicio; "days")}}
{{parseDate("2026-03-04"; "YYYY-MM-DD")}}
{{day(now)}}  {{month(now)}}  {{year(now)}}
{{dayOfWeek(now)}}                     → 1=Lunes … 7=Domingo
{{timestamp(now)}}                     → Unix timestamp
```

### Matemáticas

```
{{round(1.precio; 2)}}
{{ceil(1.valor)}}
{{floor(1.valor)}}
{{abs(1.diferencia)}}
{{max(1.a; 1.b; 1.c)}}
{{min(1.a; 1.b)}}
{{sum(map(1.items; "precio"))}}
{{average(map(1.items; "precio"))}}
{{parseNumber(1.textoNumero; ".")}}    → punto decimal
```

### Arrays y colecciones

```
{{length(1.lista)}}                    → cantidad de elementos
{{first(1.lista)}}                     → primer elemento
{{last(1.lista)}}                      → último elemento
{{get(1.lista; 0)}}                    → elemento en índice 0
{{slice(1.lista; 0; 5)}}               → primeros 5 elementos
{{flatten(1.anidado)}}                 → aplanar arrays anidados
{{distinct(1.lista; "id")}}            → deduplicar por campo
{{sort(1.lista; false; "nombre")}}     → ordenar descendente por nombre
{{map(1.lista; "email")}}              → extraer campo de cada elemento
{{filter(1.lista; "activo"; true)}}    → filtrar por campo=valor
{{contains(1.lista; "valor")}}         → ¿contiene elemento?
{{merge(1.obj1; 1.obj2)}}              → combinar objetos
{{keys(1.objeto)}}                     → array de claves
{{values(1.objeto)}}                   → array de valores
```

### Condicionales

```
{{if(1.estado == "activo"; "Sí"; "No")}}
{{ifempty(1.nombre; "Sin nombre")}}    → si vacío usa default
{{switch(1.codigo; "A"; "Opción A"; "B"; "Opción B"; "Otro")}}
```

---

## Router — Condicionar rutas

El **Router** es central en Make para manejar múltiples caminos.

### Configurar filtro de ruta

Cada rama del router tiene un filtro (condición):

| Campo | Operador | Valor |
|-------|----------|-------|
| `1.estado` | equal to | `activo` |
| `1.monto` | greater than | `1000` |
| `1.email` | contains | `@empresa.com` |

### Patrón: clasificar por tipo

```
Router →
  Ruta 1: filtro: 1.tipo = "factura"   → módulo facturación
  Ruta 2: filtro: 1.tipo = "pedido"    → módulo pedidos
  Ruta 3: (sin filtro = fallback)      → módulo default / error
```

---

## Webhooks

### Webhook instantáneo (recibir datos)

1. Crear módulo **Webhooks > Custom webhook**
2. Copiar URL generada: `https://hook.make.com/xxxx`
3. Definir **Data Structure** para parsear el payload
4. Configurar el servicio externo para enviar POST a esa URL

### Enviar datos a webhook externo

```
HTTP > Make a request
URL: https://hook.eu1.make.com/xxxx
Method: POST
Headers: Content-Type: application/json
Body type: Raw / JSON
Content: {"campo": "{{1.valor}}", "fecha": "{{formatDate(now; \"YYYY-MM-DD\")}}"}
```

---

## Data Stores

Bases de datos simples para persistir datos entre ejecuciones.

### Operaciones disponibles

| Módulo | Descripción |
|--------|-------------|
| **Add/replace a record** | Insertar o reemplazar (por key) |
| **Update a record** | Actualizar campos específicos |
| **Get a record** | Obtener por clave única |
| **Search records** | Buscar con filtros |
| **Delete a record** | Eliminar por key |
| **Get all records** | Listar todos los registros |
| **Check the existence of a record** | Verificar si existe |

### Data Structure — ejemplo

```json
{
  "id": "text",
  "nombre": "text",
  "monto": "number",
  "fecha": "date",
  "activo": "boolean",
  "tags": "array"
}
```

---

## Patrones frecuentes

### Webhook → validar → procesar → responder

1. **Webhooks > Custom webhook** (trigger)
2. **Router** → ruta 1: datos válidos / ruta 2: error
3. Ruta 1: módulo de procesamiento (Notion, Sheets, API)
4. **Webhooks > Webhook response** → `{"status": "ok"}`
5. Ruta 2: **Webhooks > Webhook response** → `{"error": "invalid data"}`

### Procesar lista con Iterator + Aggregator

1. Trigger que devuelve array en `1.items`
2. **Tools > Iterator** → array: `{{1.items}}`
3. Nodo de acción por cada elemento (`{{2.value.campo}}`)
4. **Tools > Array aggregator** → agrupar resultados
5. Nodo final con el array consolidado

### Deduplicar con Data Store

1. Obtener registro de Data Store por ID
2. **Router** → ruta 1: no existe → procesar + guardar en Data Store; ruta 2: ya existe → skip

### Retry con error handler

1. Configurar **Error handler** en módulo propenso a fallos
2. **Flow Control > Sleep** (esperar N segundos)
3. Reroute to the module que falló (crear loop de retry)
4. Contador en Data Store para limitar intentos

---

## API de Make (para automatizar Make desde Umbral)

Base URL: `https://eu1.make.com/api/v2/` (o `us1` según región)

```
GET  /scenarios                              → listar escenarios
GET  /scenarios/{id}                         → detalle de escenario
POST /scenarios/{id}/run                     → ejecutar escenario manualmente
GET  /scenarios/{id}/executions              → historial de ejecuciones
PATCH /scenarios/{id}                        → activar/desactivar (scheduling.active: true/false)
GET  /hooks                                  → listar webhooks
POST /hooks                                  → crear webhook
```

Headers requeridos:
```
Authorization: Token {MAKE_API_TOKEN}
Content-Type: application/json
```

---

## Make ↔ Umbral (integración actual)

Rick tiene la task `make.post_webhook` disponible:

```json
{
  "task": "make.post_webhook",
  "payload": {
    "webhook_url": "https://hook.eu1.make.com/xxxx",
    "payload": {
      "tipo": "reporte",
      "datos": "..."
    }
  }
}
```

Ver skill `make-webhook` para la implementación en el Worker.

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| `422 Unprocessable Entity` | Payload inválido o campos requeridos faltantes | Verificar Data Structure; revisar campos obligatorios |
| `429 Too Many Requests` | Rate limit del servicio externo o de Make | Reducir frecuencia; agregar **Sleep** entre iteraciones |
| `Scenario is not running` | Escenario desactivado | Activar en dashboard; verificar scheduling |
| `Webhook queue backed up` | Escenario lento, bundles acumulados | Optimizar módulos; aumentar concurrency; usar Instant trigger |
| `Data structure mismatch` | Datos recibidos no coinciden con estructura definida | Re-determinar data structure con payload real |
| `Connection expired` | OAuth token caducado | Reconectar en Connections > escenario |
| Aggregator devuelve vacío | Iterator sin bundles de entrada | Verificar que el array de entrada no esté vacío |

---

## Límites por plan

| Plan | Operaciones/mes | Ejecuciones min | Data stores |
|------|----------------|-----------------|-------------|
| Free | 1,000 | 15 min | No |
| Core | 10,000+ | 1 min | Sí |
| Pro | 100,000+ | 1 min | Sí |
| Teams | 800,000+ | 1 min | Sí |

---

## Referencias

- Documentación: https://www.make.com/en/help/
- Developer Hub: https://developers.make.com/
- API Reference: https://developers.make.com/api-documentation/
- Funciones: https://www.make.com/en/help/functions/
- Templates: https://www.make.com/en/templates/
- Comunidad: https://community.make.com/
