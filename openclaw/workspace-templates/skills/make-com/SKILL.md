---
name: make-com
description: >-
  Crear y depurar automatizaciones en Make.com (antes Integromat) usando escenarios,
  módulos, webhooks, routers, filtros y funciones integradas. Incluye patrones avanzados
  con iteradores, agregadores y manejo de errores.
  Use when "make.com scenario", "make automation", "integromat", "make scenario",
  "make webhook", "make router", "make filter", "make function", "make module",
  "crear escenario make", "automatizar make", "make.com api", "make iterator",
  "make aggregator", "make error handler", "make data store", "make operations".
metadata:
  openclaw:
    emoji: "\u2699"
    requires:
      env: []
---

# Make.com Skill

Rick puede diseñar, depurar y optimizar escenarios de automatización en Make.com, incluyendo módulos de acción, webhooks personalizados, routers condicionales, funciones de transformación y manejo de errores.

## Conceptos fundamentales

| Concepto | Descripción |
|----------|-------------|
| **Scenario** | Automatización completa (equivalente a workflow) |
| **Module** | Paso individual en el escenario (trigger, acción, búsqueda) |
| **Bundle** | Un registro de datos que fluye entre módulos |
| **Operation** | Una ejecución de módulo (afecta la facturación) |
| **Router** | Módulo que divide el flujo en múltiples rutas |
| **Filter** | Condición entre módulos que decide si el bundle continúa |
| **Iterator** | Divide un array en bundles individuales |
| **Aggregator** | Combina múltiples bundles en uno solo |
| **Data Store** | Base de datos simple integrada en Make |
| **Webhook** | URL para recibir datos externos via HTTP |

## Tipos de módulos

| Tipo | Color (UI) | Función |
|------|-----------|---------|
| Trigger | Naranja | Inicia el escenario (webhook, polling, email) |
| Action | Azul | Realiza una operación (crear, actualizar, enviar) |
| Search | Azul claro | Busca registros existentes |
| Iterator | Morado | Divide array en items individuales |
| Aggregator | Verde | Combina múltiples bundles |
| Router | Gris | Bifurca el flujo en rutas condicionales |

## Expresiones y funciones

En Make, los valores dinámicos se mapean con el panel de datos. Las funciones se escriben directamente en los campos.

### Funciones de texto
```
{{trim(1.nombre)}}                          // Eliminar espacios
{{upper(1.pais)}}                           // Mayúsculas
{{lower(1.email)}}                          // Minúsculas
{{length(1.descripcion)}}                   // Longitud de texto
{{substring(1.codigo; 0; 3)}}              // Subcadena (inicio; fin)
{{replace(1.texto; " "; "_")}}            // Reemplazar
{{split(1.tags; ",")}}                     // Array desde texto
{{join(1.items; "; ")}}                    // Texto desde array
{{contains(1.nombre; "García")}}           // Booleano
{{startsWith(1.email; "admin")}}           // Booleano
{{endsWith(1.archivo; ".pdf")}}            // Booleano
{{toString(1.numero)}}                     // Convertir a texto
{{toNumber("123.45")}}                     // Convertir a número
```

### Funciones matemáticas
```
{{round(1.precio; 2)}}                     // Redondear a 2 decimales
{{ceil(1.valor)}}                          // Redondear hacia arriba
{{floor(1.precio)}}                        // Redondear hacia abajo
{{abs(1.diferencia)}}                      // Valor absoluto
{{max(1.a; 1.b; 1.c)}}                    // Máximo de valores
{{min(1.x; 1.y)}}                         // Mínimo de valores
{{sum(1.items[]; precio)}}                 // Suma de campo en array
{{average(1.puntuaciones[])}}              // Promedio de array
{{mod(1.numero; 3)}}                       // Módulo (resto)
{{pow(2; 10)}}                            // Potencia (2^10)
```

### Funciones de fecha
```
{{now}}                                    // Fecha y hora actuales
{{today}}                                  // Fecha de hoy
{{formatDate(now; "DD/MM/YYYY HH:mm")}}   // Formatear fecha
{{parseDate("2026-03-04"; "YYYY-MM-DD")}} // Parsear texto a fecha
{{addDays(now; 7)}}                       // Sumar días
{{addMonths(now; 1)}}                     // Sumar meses
{{addHours(now; -3)}}                     // Restar horas
{{dateDifference(1.inicio; 1.fin; "days")}} // Diferencia en días
{{setTimezone(now; "America/Buenos_Aires")}} // Cambiar timezone
{{dayOfMonth(now)}}                        // Día del mes (1-31)
{{dayOfWeek(now)}}                         // Día de semana (1=Lunes)
{{month(now)}}                             // Mes (1-12)
{{year(now)}}                              // Año (e.g. 2026)
```

### Funciones de array y colecciones
```
{{first(1.items[])}}                       // Primer elemento
{{last(1.items[])}}                        // Último elemento
{{get(1.items[]; 2)}}                      // Elemento en índice
{{length(1.items[])}}                      // Cantidad de elementos
{{flatten(1.nested_array[])}}              // Aplanar array anidado
{{distinct(1.tags[])}}                     // Eliminar duplicados
{{sort(1.numeros[]; asc)}}                 // Ordenar array
{{slice(1.items[]; 0; 5)}}               // Primeros 5 elementos
{{map(1.items[]; nombre)}}                // Extraer campo de array de objetos
{{filter(1.items[]; activo; true)}}        // Filtrar por campo
{{merge(1.obj1; 1.obj2)}}                 // Combinar objetos
```

### Funciones condicionales
```
{{if(1.total > 1000; "grande"; "pequeño")}}
{{ifempty(1.descripcion; "Sin descripción")}}
{{switch(1.estado; "activo"; "verde"; "inactivo"; "rojo"; "amarillo")}}
{{and(1.activo; greater(1.monto; 0))}}
{{or(isEmpty(1.email); isEmpty(1.telefono))}}
{{not(1.cancelado)}}
```

### Funciones de JSON y HTTP
```
{{parseJSON(1.respuesta_texto)}}           // Parsear JSON string
{{toString(1.objeto)}}                     // Serializar a JSON
{{base64(1.texto)}}                        // Codificar en base64
{{base64ToString(1.encoded)}}              // Decodificar base64
{{encodeURL(1.parametro)}}                // URL encode
{{sha256(1.secreto; "HEX")}}             // Hash SHA-256
{{md5(1.texto; "HEX")}}                  // Hash MD5
```

## Webhook — Recibir datos

```
// URL del webhook Make (tipos)
https://hook.make.com/{token}              // Genérico
https://hook.eu1.make.com/{token}         // Europa 1
https://hook.eu2.make.com/{token}         // Europa 2
https://hook.us1.make.com/{token}         // US 1

// Configuración del módulo Webhooks > Custom Webhook
1. Agregar módulo "Webhooks > Custom Webhook"
2. Click en "Add" para crear nuevo webhook
3. Copiar URL generada
4. Configurar "Data structure" con JSON Schema o hacer click en "Redetermine data structure"
5. Enviar un request de prueba para auto-detectar estructura
```

## Router y Filtros

```
// Escenario con router
[Webhook] → [Router]
              ├─ [Filtro: estado = "urgente"] → [Telegram: notificar gerente]
              ├─ [Filtro: estado = "normal"] → [Email: equipo]
              └─ [Else (sin filtro)] → [Notion: registrar]

// Configurar filtro entre módulos
1. Click en la flecha entre módulos
2. "Set up a filter"
3. Label: "Solo ventas grandes"
4. Condition: 1.monto > 10000
```

## Iterator y Aggregator

### Iterator — procesar array
```
// Módulo "Flow Control > Iterator"
// Input array: {{1.items}}
// Resultado: un bundle por cada elemento del array
// Siguiente módulo recibe: {{1.value}} (el item individual)
```

### Array Aggregator — recombinar
```
// Módulo "Flow Control > Array Aggregator"
// Source module: el módulo que generó los bundles (e.g. Iterator)
// Target structure: elegir estructura o dejar vacío para array de valores
// Resultado: un bundle con array de todos los items procesados
```

### Ejemplo completo: procesar lista de emails
```
[Webhook recibe {emails: ["a@x.com", "b@x.com"]}]
    → [Iterator sobre {{1.emails}}]
    → [Gmail: enviar email a {{1.value}}]
    → [Array Aggregator: consolidar resultados]
    → [Webhook respuesta: {{1.array}} resultados procesados]
```

## Data Stores — Base de datos Make

```
// Crear Data Store: Tools > Data stores > Add
// Fields: definir esquema (Key requerido, tipo de cada campo)

// Módulo: Data store > Get a record
key: {{1.cliente_id}}

// Módulo: Data store > Add/Replace a record
key: {{1.id}}
data: {nombre: {{1.nombre}}, total: {{1.monto}}, fecha: {{now}}}

// Módulo: Data store > Search records
Condition: total greater than 1000

// Módulo: Data store > Delete a record
key: {{1.id}}
```

## Manejo de errores

Make ofrece manejadores de error por módulo:

| Tipo | Comportamiento |
|------|---------------|
| **Rollback** | Revertir todo el escenario si hay transacciones |
| **Commit** | Confirmar transacciones hasta el punto del error |
| **Resume** | Continuar con el siguiente bundle ignorando el error |
| **Break** | Guardar el bundle fallido para reintentar manualmente |
| **Ignore** | Ignorar el error y continuar normalmente |

```
// Configurar error handler:
1. Click derecho sobre el módulo → "Add error handler"
2. Elegir tipo (Break es el más común para producción)
3. Configurar notificación: [Error handler] → [Telegram/Email: notificar fallo]
```

## Módulos más usados

| Servicio | Módulos clave |
|---------|--------------|
| **HTTP** | Make a request (REST), Make an OAuth2 request |
| **Webhooks** | Custom Webhook, Custom Mailhook |
| **Flow Control** | Router, Iterator, Array Aggregator, Repeater, Sleep |
| **Tools** | Set Variable, Get Variable, Increment Function, Text Aggregator |
| **JSON** | Parse JSON, Create JSON |
| **CSV** | Parse CSV, Create CSV |
| **Google Sheets** | Search, Add Row, Update Row, Get Row |
| **Gmail/Outlook** | Watch Emails, Send Email, Get Email |
| **Notion** | Get Page, Create Page, Update Page, Search Objects |
| **Slack** | Create Message, Update Message, Get Message |
| **Airtable** | Search Records, Create Record, Update Record |
| **HTTP** | Make a request (para cualquier API REST) |
| **OpenAI** | Create a Completion, Create a Chat Completion |

## API de Make (automatización de escenarios)

```bash
# Listar escenarios
GET https://eu1.make.com/api/v2/scenarios?teamId={teamId}
Authorization: Token {API_KEY}

# Activar/desactivar escenario
PATCH https://eu1.make.com/api/v2/scenarios/{scenarioId}
Content-Type: application/json
{"isActive": true}

# Ejecutar escenario manualmente
POST https://eu1.make.com/api/v2/scenarios/{scenarioId}/run
Content-Type: application/json
{}

# Ver logs de ejecución
GET https://eu1.make.com/api/v2/scenarios/{scenarioId}/logs
```

Autenticación API: `Authorization: Token {MAKE_API_KEY}`
La API Key se genera en: Account → API → Add token

## Rate limits por plan

| Plan | Operaciones/mes | Requests API/min |
|------|----------------|-----------------|
| Free | 1,000 | 60 |
| Core | 10,000 | 60 |
| Pro | 10,000+ | 120 |
| Teams | Sin límite | Sin límite |

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `Connection error` | Credencial inválida o expirada | Reconnect en Make connections o renovar OAuth |
| `Bundle error` | Un bundle falló sin error handler | Agregar error handler (Break + notificación) |
| `Operation limit reached` | Superó el límite mensual | Optimizar operaciones; considerar upgrade |
| `Data structure mismatch` | Campo esperado no llega | Verificar estructura con "Redetermine data structure" |
| `Invalid JSON` | Módulo JSON mal configurado | Revisar mapeo de campos; usar Parse JSON |
| Escenario activo pero no corre | Webhook URL no coincide | Verificar URL destino; usar "Run once" para test |
| Duplicados en Data Store | Key repetida sin verificar existencia | Usar Search antes de Add/Replace; lógica upsert |

## Documentación oficial

- Referencia de funciones: https://www.make.com/en/help/functions/
- Escenarios: https://www.make.com/en/help/scenarios
- Webhooks: https://www.make.com/en/help/tools/webhooks
- API Make: https://developers.make.com/api-documentation/
- App customization: https://developers.make.com/custom-apps-documentation/
