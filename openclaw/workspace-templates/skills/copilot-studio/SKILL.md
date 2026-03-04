---
name: copilot-studio
description: >-
  Crear agentes conversacionales con Microsoft Copilot Studio (antes Power Virtual Agents).
  Cubre topics, actions, knowledge sources, variables, canales de despliegue, integración
  con Power Automate y la API de Direct Line.
  Use when "copilot studio", "power virtual agents", "chatbot microsoft", "agente conversacional",
  "crear bot teams", "topic copilot", "action copilot studio", "copilot studio flow",
  "generative ai copilot", "copilot studio webhook", "copilot studio api",
  "bot sin código microsoft", "copilot studio knowledge", "adaptive card copilot".
metadata:
  openclaw:
    emoji: "\U0001F916"
    requires:
      env: []
---

# Copilot Studio Skill

Rick puede guiar el diseño y despliegue de agentes conversacionales en Microsoft Copilot Studio, incluyendo topics, variables, llamadas a Power Automate, fuentes de conocimiento y publicación en Teams o sitios web.

## Arquitectura de un agente

```
Canales (Teams, Web, WhatsApp, etc.)
    ↓
Agente en Copilot Studio
    ├── Topics (flujos de conversación)
    │     ├── Trigger phrases / Conditions
    │     ├── Messages, Questions, Conditions
    │     └── Call actions (Power Automate, REST, Connector)
    ├── Knowledge Sources (SharePoint, sitios web, archivos)
    ├── Generative AI (respuestas sin topic específico)
    └── Tools (REST API, MCP, Custom Connectors, Agent Flows)
```

## Topics — Flujos de conversación

### Tipos de topics

| Tipo | Descripción |
|------|-------------|
| **Custom topic** | Topic creado por el usuario |
| **System topic** | Topics predefinidos del sistema |
| Conversational start | Bienvenida al iniciar la conversación |
| Escalate | Transferencia a agente humano |
| End conversation | Cierre de conversación |
| Confirmed success/failure | Confirmación de resolución |
| Fallback | Cuando no reconoce la intención |

### Nodos de un topic

| Nodo | Función |
|------|---------|
| **Message** | Enviar texto, imagen o Adaptive Card |
| **Question** | Hacer una pregunta y guardar respuesta en variable |
| **Condition** | Bifurcar según valor de variable |
| **Set Variable** | Asignar valor a una variable |
| **Call action** | Ejecutar Power Automate flow o conector |
| **Redirect** | Ir a otro topic |
| **End topic** | Terminar el topic actual |
| **End conversation** | Terminar la conversación completa |
| **Send an HTTP request** | Llamar a REST API directamente |
| **Generative Answer** | Respuesta generativa desde knowledge sources |

### Ejemplo de topic: consultar estado de pedido

```
Topic: "Estado de pedido"
Trigger phrases: 
  - "¿dónde está mi pedido?"
  - "quiero saber el estado de mi compra"
  - "seguimiento de pedido"

Nodos:
1. Message: "¡Hola! Voy a consultar tu pedido."
2. Question: "¿Cuál es el número de pedido?"
   → Guardar en: Topic.NumeroPedido (tipo: Number)
3. Call action: Flow "Consultar Estado Pedido"
   Input: NumeroPedido → Topic.NumeroPedido
   Output: Estado → Topic.EstadoPedido
4. Condition: 
   Topic.EstadoPedido is equal to "enviado"
     → Message: "Tu pedido está en camino. Llegará en 2-3 días."
   Topic.EstadoPedido is equal to "pendiente"
     → Message: "Tu pedido está siendo procesado."
   Else:
     → Message: "No encontré información sobre ese pedido."
5. End topic
```

## Variables

Copilot Studio tiene tres tipos de variables:

### Variables de Topic
```
// Scope: solo el topic actual
Topic.NombreUsuario     // Texto
Topic.CantidadItems     // Número
Topic.EsCliente         // Booleano
Topic.FechaConsulta     // Fecha y hora
Topic.ListaProductos    // Tabla

// Crear: nodo Question → variable name
// Usar: seleccionar en cualquier campo dinámico
```

### Variables Globales
```
// Scope: toda la sesión de conversación (persiste entre topics)
Global.UserEmail
Global.UserLanguage
Global.SessionID
Global.AccountType

// Crear: Topic Variables panel → "Global"
// Usar: se comparten automáticamente entre todos los topics
```

### Variables del Sistema
```
System.User.DisplayName      // Nombre del usuario autenticado
System.User.Email            // Email del usuario
System.User.Id               // ID del usuario
System.Conversation.Id       // ID de la conversación
System.Activity.Text         // Último mensaje del usuario
System.Activity.Timestamp    // Timestamp del último mensaje
System.Utterance             // Texto exacto enviado por el usuario
System.Channel               // Canal de comunicación (teams, web, etc.)
System.Locale                // Idioma (e.g. es-AR, en-US)
```

## Actions — Integración externa

### Power Automate Flow desde Copilot Studio

```
// En Copilot Studio → nodo "Call an action" → "Create a flow"
// Esto abre Power Automate con template especial:
// - Trigger: "When Power Virtual Agents calls a flow"
// - Return: "Return value(s) to Power Virtual Agents"

// Pasar variables al flow:
Input name: clienteId
Value: Topic.ClienteID (variable del topic)

// Recibir variables del flow:
Output name: estadoPedido
Save to variable: Topic.EstadoPedido
```

### HTTP Request directo (sin Power Automate)

```json
// Nodo "Send an HTTP request"
{
  "url": "https://api.empresa.com/v1/clientes/{{Topic.ClienteID}}",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer {{Global.APIToken}}",
    "Content-Type": "application/json"
  },
  "responseVariable": "Topic.APIResponse"
}
```

### Tools — tipos disponibles

| Tipo | Descripción |
|------|-------------|
| **REST API** | Conectar a cualquier endpoint OpenAPI |
| **Model Context Protocol (MCP)** | Protocolo estándar para tools LLM |
| **Custom Connector** | Conector Power Platform personalizado |
| **Agent Flow** | Flow de Power Automate optimizado para agentes |
| **Prompt-based tool** | Instrucción al modelo para tarea específica |
| **Computer use** | Interacción con interfaz gráfica (preview) |

## Fuentes de conocimiento (Knowledge Sources)

```
// Tipos soportados
1. SharePoint — sitios y bibliotecas de documentos
2. Archivos — PDF, DOCX, PPTX, XLSX subidos directamente
3. Sitios web públicos — indexación de páginas web
4. Dataverse — tablas y vistas
5. Azure AI Search — índice de búsqueda vectorial

// Configuración básica:
Copilot Studio → Knowledge → Add Knowledge →
  SharePoint: URL del sitio o biblioteca
  File upload: arrastrar archivos (máx. 512MB)
  Public website: URL a indexar (hasta 2 niveles de profundidad)
```

### Generative Answers
```
// Copilot Studio usa GenAI para responder preguntas con las fuentes configuradas
// Sin necesidad de crear topics específicos para cada pregunta

// Activar en: Settings → Generative AI → Generative answers → On
// Nivel de moderación del contenido: Low / Medium / High

// El agente puede combinar topics explícitos + generative answers
// Prioridad: topic match > generative answers > fallback topic
```

## Adaptive Cards

Las Adaptive Cards permiten respuestas ricas con botones, imágenes y formularios.

```json
// Ejemplo de card simple con acciones
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "Tu pedido **#{{Topic.NumeroPedido}}** está {{Topic.EstadoPedido}}",
      "wrap": true,
      "size": "Medium"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Fecha estimada:", "value": "{{Topic.FechaEntrega}}"},
        {"title": "Transportista:", "value": "{{Topic.Transportista}}"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "Ver más detalles",
      "data": {"action": "verDetalle"}
    },
    {
      "type": "Action.OpenUrl",
      "title": "Rastrear envío",
      "url": "{{Topic.URLRastreo}}"
    }
  ]
}
```

## Canales de despliegue

| Canal | Configuración |
|-------|--------------|
| **Teams** | Publish → Channels → Teams → Submit for approval |
| **Demo website** | Share → Demo website link (URL pública de prueba) |
| **Custom website** | Embed script en HTML |
| **Mobile app** | SDK de Direct Line |
| **WhatsApp Business** | Integración vía Azure Communication Services |
| **Telephony** | Azure Communication Services (voz) |

### Embed en sitio web
```html
<script src="https://cdn.botframework.com/botframework-webchat/latest/webchat.js"></script>
<div id="webchat"></div>
<script>
  window.WebChat.renderWebChat({
    directLine: window.WebChat.createDirectLine({
      token: 'TOKEN_DE_DIRECT_LINE'
    }),
    userID: 'user-id-unico',
    username: 'Usuario',
    locale: 'es-AR'
  }, document.getElementById('webchat'));
</script>
```

## Autenticación

```
// Tipos de autenticación
1. No authentication — acceso libre
2. Authenticate with Microsoft — Azure AD (para usuarios internos)
3. Manual (OAuth 2.0) — custom OAuth provider

// Configurar en: Settings → Security → Authentication
// Scope recomendado para Microsoft 365: openid profile email

// En topics, verificar autenticación:
System.User.Email != "" → usuario autenticado
```

## API de Direct Line (integración programática)

```bash
# 1. Generar token de Direct Line
POST https://directline.botframework.com/v3/directline/tokens/generate
Authorization: Bearer {DIRECT_LINE_SECRET}

# 2. Iniciar conversación
POST https://directline.botframework.com/v3/directline/conversations
Authorization: Bearer {TOKEN}

# 3. Enviar mensaje al bot
POST https://directline.botframework.com/v3/directline/conversations/{convId}/activities
Authorization: Bearer {TOKEN}
Content-Type: application/json
{
  "type": "message",
  "from": {"id": "user1"},
  "text": "¿cuál es el estado de mi pedido 12345?"
}

# 4. Recibir respuesta
GET https://directline.botframework.com/v3/directline/conversations/{convId}/activities
Authorization: Bearer {TOKEN}
```

## Buenas prácticas

### Topics
- Usar nombres descriptivos en inglés para topics (mejor para búsqueda interna)
- Agrupar topics por dominio (pedidos, cuenta, soporte, etc.)
- Crear topic de "bienvenida" personalizado sobrescribiendo el de sistema
- Mínimo 5 trigger phrases variadas por topic (lenguaje natural diverso)

### Variables
- Prefixar con tipo: `Topic.strNombre`, `Topic.numTotal`, `Topic.boolActivo`
- Variables globales solo para datos persistentes de sesión (usuario, idioma, cuenta)
- Limpiar variables sensibles al final de la sesión

### Performance
- Knowledge sources: indexar solo documentos relevantes (calidad > cantidad)
- Evitar loops infinitos entre topics (siempre agregar nodo End conversation)
- Probar con usuarios reales en canal de demo antes de publicar en Teams

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| "No matching topics found" | Trigger phrases no coinciden con lo que dice el usuario | Agregar más variaciones; habilitar Generative AI |
| Flow no se ejecuta | Power Automate flow desactivado | Verificar flow activo en Power Automate portal |
| Variable vacía en flow | Input no mapeado correctamente | Revisar binding de input/output en nodo Call action |
| Bot no responde en Teams | App no aprobada por admin | Admin debe aprobar la app en Teams Admin Center |
| Respuesta genérica incorrecta | Fuente de conocimiento mal indexada | Verificar que el documento esté indexado y tenga permiso de lectura |
| Loop entre topics | Redirect circular | Asegurarse que cada topic tenga un End topic/conversation |

## Documentación oficial

- Crear topics: https://learn.microsoft.com/microsoft-copilot-studio/authoring-create-edit-topics
- Actions: https://learn.microsoft.com/microsoft-copilot-studio/add-tools-custom-agent
- Knowledge sources: https://learn.microsoft.com/microsoft-copilot-studio/knowledge-copilot-studio
- Variables: https://learn.microsoft.com/microsoft-copilot-studio/authoring-variables
- Canales: https://learn.microsoft.com/microsoft-copilot-studio/publication-fundamentals-publish-channels
- Direct Line API: https://learn.microsoft.com/azure/bot-service/rest-api/bot-framework-rest-direct-line-3-0-concepts
