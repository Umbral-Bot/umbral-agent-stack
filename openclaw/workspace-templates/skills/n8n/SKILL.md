---
name: n8n
description: >-
  Asistente para crear y depurar workflows de automatización con n8n: nodos,
  expresiones, credenciales, webhooks, código JavaScript/Python y self-hosting.
  Use when "n8n", "workflow n8n", "nodo n8n", "expresión n8n", "webhook n8n",
  "automatización n8n", "trigger n8n", "HTTP request n8n", "código n8n",
  "self-hosted n8n", "credencial n8n", "loop n8n", "transformar datos n8n".
metadata:
  openclaw:
    emoji: "\U0001F504"
    requires:
      env: []
---

# n8n Skill

Rick usa este skill para guiar la creación, depuración y optimización de workflows de automatización con n8n. Cubre la plataforma self-hosted o cloud, nodos nativos, expresiones y código custom.

Fuente oficial: https://docs.n8n.io/

Rick tiene n8n instalado en la VPS. Ver `docs/37-n8n-vps-automation.md` para configuración local.

---

## Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Workflow** | Cadena de nodos conectados que automatizan un proceso |
| **Node** | Bloque funcional: trigger, acción, transformación o lógica |
| **Trigger Node** | Nodo de inicio; activa el workflow (webhook, schedule, email, etc.) |
| **Connection** | Enlace entre nodos que transfiere items |
| **Item** | Unidad de datos que fluye entre nodos (JSON object) |
| **Expression** | Código dinámico `{{ ... }}` para referenciar datos de nodos anteriores |
| **Credential** | Autenticación almacenada y reutilizable para servicios externos |
| **Execution** | Una corrida completa del workflow |
| **Sub-workflow** | Workflow llamado desde otro workflow vía Execute Workflow node |

---

## Triggers principales

| Trigger | Cuándo usar |
|---------|-------------|
| **Webhook** | Recibir datos HTTP externos (Make.com, GitHub, Notion) |
| **Schedule** | Ejecución periódica (cron) |
| **Email Trigger (IMAP)** | Cuando llega un email |
| **RSS Feed Trigger** | Nuevo artículo en feed RSS |
| **Kafka / RabbitMQ Trigger** | Mensajes de colas enterprise |
| **Execute Workflow Trigger** | Como sub-workflow llamado por otro |
| **Manual Trigger** | Ejecución manual desde UI (desarrollo/testing) |
| **Chat Trigger** | Integración con chat (modo AI agent) |

---

## Nodos de acción más usados

| Nodo | Función |
|------|---------|
| **HTTP Request** | Llamar cualquier API REST |
| **Code** | JavaScript o Python custom |
| **Set** | Definir / transformar campos del item |
| **Edit Fields (Set)** | Versión visual de Set node |
| **Function** | Procesar todos los items con JS |
| **IF** | Bifurcación condicional |
| **Switch** | Múltiples branches según valor |
| **Merge** | Combinar outputs de múltiples ramas |
| **Loop Over Items** | Iterar sobre arrays |
| **Wait** | Pausa por tiempo o evento |
| **Respond to Webhook** | Enviar respuesta HTTP al caller |
| **Error Trigger** | Capturar errores del workflow |
| **Send Email** | Enviar emails (SMTP o Gmail) |
| **Slack / Teams / Discord** | Notificaciones en chat |
| **Google Sheets** | Leer/escribir spreadsheets |
| **Airtable / Notion** | Bases de datos no-code |
| **OpenAI** | Llamadas a GPT, embeddings, DALL-E |
| **Anthropic** | Claude API |

---

## Expresiones — Sintaxis `{{ }}`

Las expresiones se escriben en el campo de valor de cualquier parámetro de nodo.

### Referenciar datos de nodos anteriores

```javascript
// Dato del nodo anterior (primer item)
{{ $json.campo }}
{{ $json["campo con espacios"] }}

// Dato de nodo específico por nombre
{{ $('Nombre del Nodo').item.json.campo }}

// Todos los items del nodo anterior
{{ $('Webhook').all() }}

// Item en posición específica
{{ $('Get Data').item(0).json.nombre }}

// Dato del trigger
{{ $trigger.item.json.body }}
```

### Variables de entorno y ejecución

```javascript
{{ $execution.id }}              // ID de la ejecución actual
{{ $execution.resumeUrl }}       // URL para reanudar (wait node)
{{ $workflow.id }}               // ID del workflow
{{ $workflow.name }}             // Nombre del workflow
{{ $now }}                       // DateTime actual (Luxon)
{{ $today }}                     // Fecha actual
{{ $env.MI_VARIABLE }}           // Variable de entorno del sistema
```

### Manipulación de texto

```javascript
{{ $json.nombre.toUpperCase() }}
{{ $json.email.toLowerCase() }}
{{ $json.texto.trim() }}
{{ $json.nombre.replace('_', ' ') }}
{{ $json.descripcion.split(',') }}
{{ `Hola ${$json.nombre}, tu ID es ${$json.id}` }}
```

### Fechas con Luxon

```javascript
{{ $now.toISO() }}                           // ISO 8601
{{ $now.toFormat('yyyy-MM-dd') }}            // 2026-03-04
{{ $now.setZone('America/Argentina/Buenos_Aires').toISO() }}
{{ $now.minus({days: 7}).toISO() }}          // hace 7 días
{{ $now.plus({hours: 2}).toISO() }}          // en 2 horas
{{ DateTime.fromISO($json.fecha).toFormat('dd/MM/yyyy') }}
```

### Lógica condicional

```javascript
{{ $json.estado === 'activo' ? 'Sí' : 'No' }}
{{ $json.monto > 1000 ? 'Premium' : 'Standard' }}
{{ $json.nombre ?? 'Sin nombre' }}            // nullish coalescing
{{ $json.tags?.length > 0 ? $json.tags[0] : '' }}  // optional chaining
```

### Transformar arrays

```javascript
// Mapeado
{{ $json.items.map(i => i.nombre) }}

// Filtrado
{{ $json.items.filter(i => i.activo === true) }}

// Longitud
{{ $json.items.length }}

// Join
{{ $json.tags.join(', ') }}

// Primer elemento
{{ $json.items[0] }}

// JMESPath
{{ $jmespath($json, 'items[?precio > `100`].nombre') }}
```

---

## Code Node — JavaScript

El Code node procesa items con JS completo.

```javascript
// Procesar todos los items
for (const item of $input.all()) {
  item.json.nombreUpper = item.json.nombre.toUpperCase();
  item.json.fechaProcesado = new Date().toISOString();
}
return $input.all();

// Crear nuevos items desde array
const datos = $input.first().json.lista;
return datos.map(d => ({ json: { id: d.id, nombre: d.nombre } }));

// Filtrar items
return $input.all().filter(item => item.json.precio > 100);

// Combinar datos de múltiples inputs
const itemsA = $input.all();
// En Code node con múltiples inputs:
const itemsB = $('Otro Nodo').all();
return itemsA.map((a, i) => ({
  json: { ...a.json, extra: itemsB[i]?.json }
}));
```

---

## HTTP Request Node — Patrones

```json
{
  "method": "POST",
  "url": "https://api.ejemplo.com/endpoint",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {"name": "Content-Type", "value": "application/json"},
      {"name": "Authorization", "value": "Bearer {{ $env.API_TOKEN }}"}
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {"name": "campo", "value": "{{ $json.valor }}"}
    ]
  }
}
```

---

## Patrones frecuentes

### Webhook → procesar → responder

1. **Webhook Trigger** (modo: Respond immediately / Last node)
2. **Set Node** → extraer y transformar campos
3. **HTTP Request** → llamar API externa
4. **Respond to Webhook** → devolver respuesta al caller

### Loop sobre lista grande con batches

1. **Split in Batches** (tamaño de batch: 10-50)
2. **Nodo de acción** (API call por cada batch)
3. Conectar de vuelta al **Split in Batches** (auto-loop)
4. Al terminar: **Merge** para consolidar resultados

### Error handling

1. Activar **Continue On Fail** en nodo propenso a errores
2. Usar **IF** para detectar `{{ $json.error !== undefined }}`
3. O agregar **Error Trigger** workflow separado para notificaciones

### AI Agent con tools

1. **Chat Trigger** (o Webhook)
2. **AI Agent Node** → modelo (OpenAI/Anthropic/Ollama)
3. Conectar tools: HTTP Request, Google Sheets, Notion, etc.
4. El agente decide qué tool usar según el mensaje

---

## Credenciales frecuentes

| Servicio | Tipo de auth |
|---------|--------------|
| HTTP genérico | Header Auth / Query Auth / OAuth2 |
| Google Sheets/Gmail | OAuth2 (Google) |
| Slack | OAuth2 / Bot Token |
| Notion | API Key |
| OpenAI | API Key |
| PostgreSQL / MySQL | Host + usuario + contraseña |
| SMTP | Host + usuario + contraseña + puerto |
| GitHub | Personal Access Token |
| Telegram Bot | Bot Token |

---

## Self-hosting en VPS (Linux)

### Variables de entorno clave

```bash
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_EDITOR_BASE_URL=https://n8n.tudominio.com
WEBHOOK_URL=https://n8n.tudominio.com/
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=secreto
DB_TYPE=postgresdb
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_HOST=localhost
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=pass
EXECUTIONS_PROCESS=main
GENERIC_TIMEZONE=America/Argentina/Buenos_Aires
```

### Comandos útiles

```bash
# Iniciar (PM2)
pm2 start n8n --name n8n

# Ver logs
pm2 logs n8n

# Exportar workflows
n8n export:workflow --all --output=./backups/workflows.json

# Importar workflows
n8n import:workflow --input=./backups/workflows.json

# Actualizar
npm update -g n8n
pm2 restart n8n
```

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| `Cannot read property of undefined` | Campo nulo en expresión | Usar `?.` optional chaining o `?? 'default'` |
| `Workflow did not return data` | Nodo final sin output | Agregar **Set** o **Respond to Webhook** al final |
| `Credential not found` | Credencial eliminada o desvinculada | Reseleccionar credencial en el nodo |
| `Execution timeout` | Workflow muy largo (default: 1h) | Aumentar `EXECUTIONS_TIMEOUT` o dividir en sub-workflows |
| `Too many requests` | Rate limit de API externa | Agregar **Wait** node entre iteraciones |
| Webhook no recibe datos | URL incorrecta o tunnel caído | Verificar `WEBHOOK_URL`; usar ngrok en desarrollo local |
| `Expression error: is not defined` | Variable de nodo inexistente | Verificar nombre exacto del nodo (case-sensitive) |

---

## Referencias

- Documentación oficial: https://docs.n8n.io/
- Expresiones: https://docs.n8n.io/code/expressions/
- Code node: https://docs.n8n.io/code/code-node/
- Nodos: https://docs.n8n.io/integrations/
- Self-hosting: https://docs.n8n.io/hosting/
- Comunidad: https://community.n8n.io/
- Configuración VPS: `docs/37-n8n-vps-automation.md`
