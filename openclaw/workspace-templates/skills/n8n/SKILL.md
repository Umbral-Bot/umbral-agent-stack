---
name: n8n
description: >-
  Design and debug n8n workflows using nodes, expressions, credentials, and the
  Code node (JavaScript/Python) for self-hosted or cloud automation pipelines.
  Use when "create n8n workflow", "n8n webhook", "n8n expression", "n8n node",
  "automate with n8n", "n8n http request", "n8n schedule", "n8n code node",
  "n8n credential", "n8n self-hosted", "trigger n8n flow", "n8n error handling".
metadata:
  openclaw:
    emoji: "\U0001F9BE"
    requires:
      env: []
---

# n8n Skill

Rick puede asistir en el diseño, depuración y mantenimiento de workflows n8n — tanto en instancia self-hosted como en n8n Cloud.

Documentación oficial: https://docs.n8n.io/

---

## Conceptos fundamentales

| Concepto | Descripción |
|----------|-------------|
| **Workflow** | Conjunto de nodos conectados que procesan datos |
| **Node** | Bloque de acción o disparador. Produce ítems de salida |
| **Item** | Unidad de dato que fluye entre nodos (objeto JSON) |
| **Trigger node** | Nodo que inicia el workflow (webhook, cron, evento) |
| **Regular node** | Nodo de procesamiento/acción invocado después del trigger |
| **Expression** | Valor dinámico calculado con `{{ }}` en parámetros |
| **Credential** | Autenticación almacenada de forma segura para servicios externos |
| **Execution** | Una corrida del workflow (manual, trigger, programada) |

---

## Nodos core más usados

### Triggers

| Nodo | Cuándo usar |
|------|-------------|
| **Webhook** | Recibir llamadas HTTP POST/GET desde sistemas externos |
| **Schedule Trigger** | Ejecutar según cron (ej: `0 8 * * 1-5` = lun-vie 8:00) |
| **Manual Trigger** | Ejecución manual durante desarrollo/testing |
| **Email Trigger (IMAP)** | Trigger cuando llega un email |
| **RSS Read** | Monitorear feeds RSS |

### Procesamiento y lógica

| Nodo | Uso |
|------|-----|
| **HTTP Request** | Llamar cualquier API REST/HTTP |
| **Code** | Ejecutar JavaScript o Python personalizado |
| **Set** | Crear/modificar campos en los ítems |
| **If** | Bifurcación condicional (true/false) |
| **Switch** | Múltiples ramas según valor |
| **Merge** | Combinar datos de múltiples ramas |
| **Split In Batches** | Procesar ítems en grupos (evitar rate limits) |
| **Filter** | Filtrar ítems que cumplan condición |
| **Aggregate** | Agrupar múltiples ítems en uno |
| **Loop Over Items** | Iterar sobre un array dentro de un ítem |
| **Wait** | Pausar ejecución por tiempo o hasta evento |
| **Edit Fields (Set)** | Mapear y transformar campos |

### Integraciones comunes

| Nodo | Servicio |
|------|---------|
| **OpenAI** | GPT-4, embeddings, Assistants |
| **Slack** | Mensajes, canales, usuarios |
| **Gmail** | Leer, enviar, etiquetar emails |
| **Google Sheets** | Leer, escribir, actualizar hojas |
| **Notion** | Crear páginas, actualizar propiedades |
| **Airtable** | CRUD en bases Airtable |
| **GitHub** | Issues, PRs, repositorios |
| **Telegram** | Enviar mensajes, bots |
| **MySQL / PostgreSQL** | Queries SQL |
| **Redis** | Get, Set, Push en Redis |
| **HTTP Request** | Cualquier API personalizada |

---

## Expresiones (Expressions)

Las expresiones se escriben entre `{{ }}` en cualquier campo de parámetro:

### Acceder a datos de nodos anteriores

```javascript
// Dato del nodo anterior (output[0])
{{ $json.nombre }}
{{ $json.email }}
{{ $json["campo con espacio"] }}

// Nodo específico por nombre
{{ $node["HTTP Request"].json.data.id }}
{{ $node["Webhook"].json.body.payload }}

// Primer ítem de un nodo
{{ $node["Google Sheets"].json[0].Title }}

// Input del trigger
{{ $input.first().json.event_type }}
{{ $input.all() }}       // todos los ítems como array
```

### Variables de entorno y workflow

```javascript
{{ $env.MI_API_KEY }}           // variable de entorno
{{ $workflow.id }}               // ID del workflow
{{ $workflow.name }}             // nombre del workflow
{{ $execution.id }}              // ID de la ejecución actual
{{ $now }}                       // DateTime actual (objeto Luxon)
{{ $today }}                     // fecha de hoy (objeto Luxon)
```

### Luxon — Fechas y tiempo

```javascript
{{ $now.toISO() }}                                    // "2026-03-04T10:30:00.000-06:00"
{{ $now.toFormat('dd/MM/yyyy') }}                     // "04/03/2026"
{{ $now.plus({days: 7}).toISO() }}                    // +7 días
{{ $now.minus({hours: 2}).toISO() }}                  // -2 horas
{{ $now.startOf('month').toISO() }}                   // primer día del mes
{{ $now.toUTC().toISO() }}                            // convertir a UTC
{{ DateTime.fromISO($json.fecha).toFormat('yyyy') }}  // año de una fecha
```

### Transformaciones de texto

```javascript
{{ $json.nombre.toUpperCase() }}
{{ $json.email.toLowerCase() }}
{{ $json.texto.replace(/\n/g, ' ') }}
{{ $json.nombre.split(' ')[0] }}          // primer nombre
{{ `Hola, ${$json.nombre}!` }}            // template literal
```

### JMESPath — Consultas en JSON

```javascript
{{ $jmespath($json, "items[?status=='active'].name") }}
{{ $jmespath($json, "orders | length(@)") }}
```

---

## Nodo Code (JavaScript/Python)

### JavaScript — Run Once for All Items

```javascript
// items = array de todos los ítems de entrada
const results = [];

for (const item of items) {
  const data = item.json;
  
  results.push({
    json: {
      id: data.id,
      nombre: data.nombre.trim().toUpperCase(),
      total: data.precio * data.cantidad,
      timestamp: new Date().toISOString()
    }
  });
}

return results;
```

### JavaScript — Run Once for Each Item

```javascript
// item = ítem actual (acceder con $input.item.json)
const data = $input.item.json;

return {
  json: {
    procesado: true,
    valor_doble: data.valor * 2,
    categoria: data.valor > 1000 ? 'alto' : 'bajo'
  }
};
```

### Python (Code node)

```python
results = []
for item in _input.all():
    data = item.json
    results.append({
        "json": {
            "nombre": data.get("nombre", "").upper(),
            "total": data.get("precio", 0) * data.get("cantidad", 0)
        }
    })
return results
```

---

## Webhook — Configuración

```json
// Nodo Webhook: método POST, authentication: Header Auth
// Headers requeridos: X-API-Key: <valor>

// URL del webhook (self-hosted):
// https://tu-n8n.dominio.com/webhook/abc123-uuid

// URL test (solo disponible con workflow activo en modo test):
// https://tu-n8n.dominio.com/webhook-test/abc123-uuid
```

**Responder al webhook desde n8n:**
```javascript
// Nodo "Respond to Webhook" con status 200
{
  "status": "ok",
  "message": "Procesado exitosamente",
  "execution_id": "{{ $execution.id }}"
}
```

---

## Credenciales — Configuración

Tipos más comunes:
- **Header Auth**: `Name: Authorization`, `Value: Bearer <token>`
- **Basic Auth**: usuario + contraseña
- **OAuth2**: flujo OAuth estándar con callback a n8n
- **API Key**: clave en header o query param

Crear credencial: `Configuración → Credenciales → + Nueva credencial`

Usar en expresiones: `{{ $credentials.MiCredencial.apiKey }}` (solo en Code node)

---

## Manejo de errores

### Error Workflow (workflow de manejo de errores)

```
Workflow Principal
  └── En caso de error → Ejecuta Error Workflow
                             ├── Obtiene detalles del error
                             ├── Envía notificación (email, Slack, Telegram)
                             └── Registra en Notion/Airtable
```

Activar: `Configuración del workflow → Error Workflow → Seleccionar workflow`

### Try/Catch con nodo If

```
[Acción riesgosa]
    ├── Success → Continuar flujo normal
    └── Error → [If: $execution.error != null]
                    ├── Sí → Manejar error, notificar
                    └── No → No aplica
```

### En nodo Code:

```javascript
try {
  const response = await fetch($env.API_URL);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  return [{ json: data }];
} catch (error) {
  return [{ json: { error: true, message: error.message } }];
}
```

---

## Self-Hosted n8n

### Instalación con Docker

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=changeme \
  -e N8N_HOST=tu-dominio.com \
  -e N8N_PROTOCOL=https \
  -e WEBHOOK_URL=https://tu-dominio.com/ \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### Variables de entorno clave

```bash
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_HOST=tu-dominio.com
WEBHOOK_URL=https://tu-dominio.com/
N8N_ENCRYPTION_KEY=clave-aleatoria-larga
DB_TYPE=postgresdb          # sqlite (default) o postgresdb
EXECUTIONS_DATA_PRUNE=true  # limpiar ejecuciones antiguas
EXECUTIONS_DATA_MAX_AGE=336 # horas (14 días)
```

### CLI commands

```bash
# Ejecutar workflow
n8n execute --id <workflow-id>

# Exportar workflows
n8n export:workflow --all --output=./workflows-backup/

# Importar workflows
n8n import:workflow --input=./workflows-backup/

# Exportar credenciales (cifradas)
n8n export:credentials --all --output=./credentials-backup.json
```

---

## Integración con Umbral Agent Stack

n8n puede actuar como orquestador externo que dispara tareas al Worker de Umbral:

```javascript
// Nodo HTTP Request → POST al Worker
// URL: http://localhost:8088/execute
// Auth: Bearer token (WORKER_TOKEN)
// Body:
{
  "task_type": "research.web",
  "input": {
    "query": "{{ $json.search_query }}",
    "max_results": 5
  },
  "callback_url": "{{ $env.N8N_WEBHOOK_URL }}/webhook/resultado"
}
```

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `Cannot read property of undefined` | Campo inexistente en `$json` | Usar `$json.campo ?? 'default'` o verificar con `if ($json.campo)` |
| `Workflow could not be started` | Trigger no activo | Activar el workflow (toggle ON en la lista) |
| `Webhook not registered` | n8n reiniciado sin reload | Desactivar y reactivar el workflow |
| `Credential not found` | Credencial eliminada o mal referenciada | Verificar nombre en `Credenciales` y reasignar en el nodo |
| `ECONNREFUSED` | Servicio externo no disponible | Agregar nodo **Wait** + retry loop, o verificar URL |
| `Too many requests (429)` | Rate limit alcanzado | Usar **Split in Batches** + **Wait** entre lotes |
| `Execution timeout` | Workflow tarda demasiado | Aumentar `EXECUTIONS_TIMEOUT` o dividir en subworkflows |
| `Expression Error` | Sintaxis incorrecta en expresión | Revisar `{{ }}`, comillas y nombres de nodo exactos |

---

## Buenas prácticas

- **Nombrar nodos descriptivamente**: `Get User Data` en lugar de `HTTP Request 3`.
- **Usar Sticky Notes** para documentar lógica compleja dentro del workflow.
- **Variables de entorno** para URLs, tokens y configuraciones cambiables.
- **Error Workflow** configurado para todos los workflows productivos.
- **Sub-workflows**: encapsular lógica reutilizable en workflows separados y llamarlos con el nodo **Execute Workflow**.
- **Logging**: agregar nodo **Code** con `console.log` durante desarrollo, o nodo **Notion/Airtable** para audit trail en producción.
- **Split in Batches** antes de acciones con rate limit (APIs, email masivo).
- **Pinning de datos**: en desarrollo, "pinear" datos de salida de nodos para iterar sin re-ejecutar triggers.

---

## Referencias

- Documentación oficial: https://docs.n8n.io/
- Nodos disponibles: https://docs.n8n.io/integrations/
- Expresiones y variables: https://docs.n8n.io/code/expressions/
- Hosting self-hosted: https://docs.n8n.io/hosting/
- Ejemplos de workflows: https://n8n.io/workflows/
