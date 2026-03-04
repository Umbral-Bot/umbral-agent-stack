---
name: n8n
description: >-
  Crear y depurar workflows de automatización con n8n, la plataforma de automatización
  open-source con más de 400 nodos. Cubre expresiones, nodos clave, credenciales,
  self-hosting y patrones de integración con APIs externas.
  Use when "n8n workflow", "n8n automation", "n8n node", "n8n expression",
  "n8n self-hosted", "n8n webhook", "n8n http request", "automatizar con n8n",
  "n8n schedule", "n8n trigger", "n8n code node", "n8n credentials",
  "n8n if condition", "n8n loop", "n8n merge", "n8n split".
metadata:
  openclaw:
    emoji: "\U0001F500"
    requires:
      env: []
---

# n8n Skill

Rick puede ayudar a diseñar, depurar y optimizar workflows en n8n, incluyendo expresiones JavaScript, lógica condicional, llamadas HTTP, transformación de datos y configuración self-hosted.

## Conceptos fundamentales

| Concepto | Descripción |
|----------|-------------|
| **Workflow** | Secuencia de nodos que procesa datos automáticamente |
| **Node** | Unidad de procesamiento (trigger, acción, transformación) |
| **Trigger** | Nodo inicial que inicia el workflow (webhook, schedule, evento) |
| **Item** | Un registro de datos que fluye entre nodos (objeto JSON) |
| **Execution** | Una ejecución del workflow completo |
| **Credential** | Información de autenticación reutilizable (API keys, OAuth) |

## Expresiones n8n

Las expresiones usan sintaxis `{{ ... }}` con JavaScript extendido (motor Tournement + Luxon para fechas).

### Acceder a datos del nodo anterior
```javascript
// Datos del item actual (nodo anterior)
{{ $json.nombre }}
{{ $json.direccion.ciudad }}
{{ $json.items[0].precio }}

// Datos de un nodo específico por nombre
{{ $node["HTTP Request"].json.data.id }}
{{ $node["Set"].json.resultado }}

// Todos los items del nodo anterior
{{ $input.all() }}
{{ $input.first().json.email }}
{{ $input.last().json.total }}
{{ $input.item.json.campo }}     // Item actual en bucle
```

### Variables del sistema
```javascript
{{ $now }}                        // Fecha y hora actual (Luxon DateTime)
{{ $today }}                      // Fecha actual
{{ $workflow.id }}                // ID del workflow
{{ $workflow.name }}              // Nombre del workflow
{{ $execution.id }}               // ID de ejecución
{{ $execution.mode }}             // "cli" | "webhook" | "trigger" | "manual"
{{ $env.MI_VARIABLE }}            // Variable de entorno n8n
{{ $vars.miVariable }}            // Variable de workflow (definida en Settings)
```

### Fechas con Luxon
```javascript
{{ $now.toISO() }}                         // "2026-03-04T10:30:00.000Z"
{{ $now.toFormat("dd/MM/yyyy HH:mm") }}    // "04/03/2026 10:30"
{{ $now.plus({days: 7}).toISO() }}         // +7 días
{{ $now.minus({hours: 3}).toISO() }}       // -3 horas
{{ $now.startOf("month").toISO() }}        // Inicio de mes
{{ $now.toFormat("yyyy-MM-dd") }}          // "2026-03-04"
{{ DateTime.fromISO($json.fecha).toFormat("dd/MM/yyyy") }}  // Formatear fecha del item
```

### Manipulación de texto y datos
```javascript
// Texto
{{ $json.nombre.toUpperCase() }}
{{ $json.email.toLowerCase() }}
{{ $json.descripcion.trim() }}
{{ $json.codigo.replace(/-/g, "") }}
{{ $json.texto.split(",") }}              // Array
{{ ["a", "b", "c"].join(", ") }}         // "a, b, c"
{{ $json.nombre.startsWith("García") }}

// Números
{{ ($json.precio * 1.21).toFixed(2) }}   // Con IVA, 2 decimales
{{ Math.round($json.valor) }}
{{ Math.max($json.a, $json.b) }}
{{ parseInt($json.id_str) }}
{{ parseFloat($json.monto_str) }}

// Objetos y Arrays
{{ Object.keys($json) }}
{{ Object.values($json).length }}
{{ $json.items.length }}
{{ $json.tags.includes("urgente") }}
{{ $json.items.filter(i => i.activo) }}
{{ $json.items.map(i => i.nombre) }}
{{ $json.items.find(i => i.id === 5) }}
```

### Lógica condicional en expresiones
```javascript
{{ $json.total > 1000 ? "grande" : "pequeño" }}
{{ $json.email || "sin-email@default.com" }}
{{ $json.nombre ?? "Anónimo" }}    // Nullish coalescing
{{ $json.activo === true && $json.monto > 0 }}
```

## Nodos principales

### Triggers (inicio de workflow)

| Nodo | Uso |
|------|-----|
| **Webhook** | Recibir datos por HTTP POST/GET |
| **Schedule Trigger** | Ejecutar en intervalos (cron) |
| **n8n Form Trigger** | Formulario web generado automáticamente |
| **Email Trigger (IMAP)** | Trigger por nuevo email |
| **GitHub Trigger** | Eventos de GitHub (push, PR, issue) |

```json
// Schedule Trigger — cada día hábil a las 8:00 AM
{
  "rule": {
    "interval": [{ "field": "cronExpression", "expression": "0 8 * * 1-5" }]
  }
}
```

### Transformación de datos

| Nodo | Función |
|------|---------|
| **Set** | Agregar, modificar o eliminar campos del item |
| **Edit Fields (Set)** | UI mejorada para Set |
| **Code** | JavaScript o Python personalizado |
| **If** | Bifurcar flujo según condición |
| **Switch** | Múltiples rutas según valor |
| **Merge** | Combinar outputs de múltiples ramas |
| **Loop Over Items** | Procesar items en lotes |
| **Split In Batches** | Dividir en lotes de N items |
| **Aggregate** | Combinar múltiples items en uno |
| **Sort** | Ordenar items |
| **Remove Duplicates** | Eliminar duplicados |
| **Filter** | Filtrar items por condición |

#### Nodo Code (JavaScript)
```javascript
// Procesar todos los items de entrada
const items = $input.all();
const resultado = items.map(item => {
  return {
    json: {
      id: item.json.id,
      nombreCompleto: `${item.json.nombre} ${item.json.apellido}`,
      precioConIVA: (item.json.precio * 1.21).toFixed(2),
      procesadoEn: new Date().toISOString()
    }
  };
});
return resultado;
```

#### Nodo Code (Python)
```python
result = []
for item in $input.all():
    data = item['json']
    result.append({
        'json': {
            'id': data['id'],
            'total': data['precio'] * data['cantidad'],
            'categoria': data['categoria'].upper()
        }
    })
return result
```

### Integración HTTP

#### HTTP Request — llamada API REST
```json
{
  "method": "POST",
  "url": "https://api.ejemplo.com/v1/clientes",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "headers": {
    "Content-Type": "application/json",
    "X-API-Version": "2026"
  },
  "body": {
    "nombre": "={{ $json.nombre }}",
    "email": "={{ $json.email }}",
    "origen": "n8n"
  },
  "options": {
    "timeout": 30000,
    "allowUnauthorizedCerts": false
  }
}
```

#### Webhook — recibir datos
```
URL del webhook: https://tu-n8n.com/webhook/mi-workflow-uuid

// Configuración del nodo Webhook
Method: POST
Path: mi-workflow-uuid
Response Mode: Respond to Webhook
Response Code: 200
Response Body: { "ok": true, "received": true }
```

### Servicios externos (nodos built-in)
- **Notion**: crear/actualizar páginas y databases
- **Google Sheets**: leer/escribir celdas y filas
- **Slack**: enviar mensajes, crear canales
- **Gmail / Microsoft Outlook**: enviar/leer emails
- **Telegram**: enviar mensajes, bots
- **PostgreSQL / MySQL / SQLite**: queries SQL
- **Redis**: operaciones get/set/list
- **GitHub / GitLab**: issues, commits, PRs
- **Jira**: issues y projects
- **Stripe**: pagos y subscripciones
- **HubSpot / Salesforce**: CRM
- **OpenAI / Anthropic**: LLM calls

## Self-Hosting (Docker)

### docker-compose.yml mínimo
```yaml
version: '3.8'
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=tu-dominio.com
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://tu-dominio.com/
      - N8N_ENCRYPTION_KEY=clave-secreta-32-chars
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password-seguro
      - N8N_SECURE_COOKIE=false
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=n8n_password
    volumes:
      - n8n_data:/home/node/.n8n
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: n8n
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: n8n_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  n8n_data:
  postgres_data:
```

### Variables de entorno clave
```bash
N8N_HOST=              # Dominio del servidor
N8N_PORT=5678
WEBHOOK_URL=           # URL base para webhooks (con trailing slash)
N8N_ENCRYPTION_KEY=    # Clave para encriptar credenciales (32+ chars)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=
N8N_BASIC_AUTH_PASSWORD=
N8N_LOG_LEVEL=info     # debug | info | warn | error
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=none  # Ahorrar espacio en disco
EXECUTIONS_DATA_MAX_AGE=168           # Horas de retención (7 días)
```

## Patrones comunes

### Webhook → Procesar → Responder
```
[Webhook Trigger] → [Set: limpiar datos] → [HTTP Request: API externa] → 
[If: ¿éxito?] → [Webhook: respond OK] / [Webhook: respond Error]
```

### Schedule → Fetch → Transform → Store
```
[Schedule 0 8 * * *] → [HTTP Request: GET /api/datos] →
[Code: transformar] → [Google Sheets: append rows]
```

### Fan-out con Merge
```
[Trigger] → [Split In Batches] → [Loop: HTTP Request por item] → 
[Aggregate: consolidar resultados] → [Notion: crear página con resumen]
```

### Error handling con Try/Catch
```
[Nodo con riesgo] → (en caso de error) → [Error Trigger] → 
[Telegram: notificar error] → [Set: registrar en log]
```

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `Cannot read properties of undefined` | Campo no existe en `$json` | Usar `?.` opcional chaining: `$json.campo?.subcampo` |
| `Referenced node not found` | Nodo referenciado no ejecutado | Verificar que el nodo anterior haya corrido; usar `$node["Nombre"].json` |
| `Webhook URL not found` | Path del webhook incorrecto o n8n reiniciado | Verificar URL en nodo Webhook; modo Production vs Test |
| `Invalid JSON` en Code node | Función retorna tipo incorrecto | El Code node debe retornar `[{json: {...}}]` |
| Credenciales expiradas | OAuth2 token vencido | Reconectar credencial en n8n Settings → Credentials |
| Timeout en HTTP Request | API tarda más de 30s | Aumentar timeout en opciones del nodo; usar webhooks async |
| Items no pasan a siguiente nodo | Nodo devuelve array vacío | Agregar nodo Filter o verificar condición del If |

## API de n8n (para integración)

```bash
# Listar workflows
GET /api/v1/workflows
Authorization: Bearer <N8N_API_KEY>

# Ejecutar workflow manualmente
POST /api/v1/workflows/{id}/execute
Content-Type: application/json
{"runData": {}}

# Obtener ejecuciones
GET /api/v1/executions?workflowId={id}&status=success

# Crear webhook URL programáticamente
GET /api/v1/workflows/{id}/webhook-urls
```

## Documentación oficial

- Expresiones: https://docs.n8n.io/code/expressions/
- Nodos: https://docs.n8n.io/integrations/
- Self-hosting: https://docs.n8n.io/hosting/
- Code node: https://docs.n8n.io/code/code-node/
- API: https://docs.n8n.io/api/
