---
name: copilot-studio
description: >-
  Asistente para crear y depurar agentes conversacionales con Microsoft Copilot
  Studio: topics, actions, generative AI, knowledge sources, canales y API.
  Use when "copilot studio", "power virtual agents", "agente conversacional",
  "topic copilot", "bot microsoft", "chatbot power platform", "action copilot",
  "knowledge source", "generative AI copilot", "canal teams copilot",
  "custom copilot", "agent copilot studio", "orchestration copilot".
metadata:
  openclaw:
    emoji: "\U0001F916"
    requires:
      env: []
---

# Copilot Studio Skill

Rick usa este skill para guiar la creación, configuración y depuración de agentes conversacionales con Microsoft Copilot Studio (antes Power Virtual Agents). Cubre topics, actions, orquestación generativa, knowledge sources y canales de publicación.

Fuente oficial: https://learn.microsoft.com/microsoft-copilot-studio/

---

## Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Agent** | Bot conversacional creado en Copilot Studio |
| **Topic** | Módulo de conversación: maneja una intención o tarea específica |
| **Trigger phrase** | Frase de activación que inicia un topic |
| **Action** | Capacidad externa que el agente puede invocar (Power Automate, API, MCP) |
| **Knowledge source** | Fuente de información para respuestas generativas (sitios web, SharePoint, archivos) |
| **Generative orchestration** | LLM que elige automáticamente qué topic/action/knowledge usar |
| **Node** | Paso dentro de un topic (message, question, condition, action, etc.) |
| **Variable** | Dato almacenado durante la conversación (global, topic o sistema) |
| **Entity** | Tipo de dato reconocido en la conversación (fecha, número, email, custom) |
| **Canvas** | Editor visual de topics drag-and-drop |
| **Environment** | Contenedor Power Platform donde vive el agente |

---

## Arquitectura de un agente

```
Usuario → Canal (Teams/Web/Telegram/API) → Agente Copilot Studio
  → Generative Orchestration (LLM)
    ├── Topics (conversación estructurada)
    ├── Actions (Power Automate / HTTP API / MCP)
    └── Knowledge Sources (SharePoint / sitios web / archivos)
```

---

## Topics — Tipos

| Tipo | Descripción | Cuándo usar |
|------|-------------|-------------|
| **Trigger topic** | Activado por frases del usuario | Intención específica del usuario |
| **System topic** | Manejo de saludos, despedidas, escalada, errores | Siempre configurar estos |
| **Lesson topic** | Ejemplos de demostración | Solo para aprendizaje |

### Topics del sistema (no eliminar)

| Topic | Función |
|-------|---------|
| `Greeting` | Saludo inicial |
| `Goodbye` | Despedida |
| `Escalate` | Escalar a agente humano |
| `Start Over` | Reiniciar conversación |
| `Fallback` | Respuesta cuando no se entiende la intención |
| `Error` | Manejo de errores del sistema |

---

## Nodos en el Canvas

| Nodo | Descripción |
|------|-------------|
| **Message** | Muestra texto, imagen, tarjeta o carrusel al usuario |
| **Question** | Hace una pregunta y guarda la respuesta en variable |
| **Condition** | Bifurcación lógica (if/else) basada en variables |
| **Action** | Llama a Power Automate flow, HTTP request o plugin |
| **Variable Management** | Asignar, copiar o limpiar variables |
| **Topic Redirect** | Navegar a otro topic |
| **Message Variation** | Respuesta aleatoria entre variantes |
| **Generative Answers** | Respuesta generada por LLM desde knowledge sources |
| **Send Message** | Enviar mensaje activo (proactivo) |
| **End Conversation** | Cerrar la sesión de conversación |
| **Transfer to Agent** | Escalar a humano via Omnichannel |

---

## Variables

### Tipos de variables

| Tipo | Scope | Descripción |
|------|-------|-------------|
| **Topic variable** | Solo el topic actual | Datos temporales del topic |
| **Global variable** | Todo el agente | Datos persistentes entre topics |
| **System variable** | Read-only | Datos del sistema y usuario |

### Variables de sistema útiles

```
System.User.DisplayName          → Nombre del usuario
System.User.Id                   → ID único del usuario
System.Conversation.Id           → ID de la conversación
System.Activity.Text             → Último mensaje del usuario
System.Activity.Value            → Datos estructurados (adaptive card)
System.LastMessage.Text          → Mensaje anterior
System.Capability.Audio          → ¿El canal soporta audio?
```

### Question node → guardar en variable

```
Pregunta: "¿Cuál es tu email?"
Guardar como: Topic.UserEmail (tipo: Email)
```

### Condition node — lógica

```
Topic.UserEmail contains "@empresa.com" → ruta VIP
Topic.Cantidad > 10                     → ruta bulk
Global.UserRole = "admin"               → ruta admin
```

---

## Entities — Reconocimiento de entidades

| Entidad predefinida | Reconoce |
|--------------------|---------|
| Email | Direcciones de email |
| Number | Números enteros y decimales |
| Date and time | Fechas, horas, rangos |
| Age | Edades |
| Currency | Montos con moneda |
| Phone number | Números de teléfono |
| URL | Direcciones web |
| Name | Nombres de personas |
| Geography | Ciudades, países, direcciones |

**Entidades custom:** lista cerrada de valores (ej: "Factura", "Pedido", "Consulta") con sinónimos.

---

## Actions — Integración con servicios externos

### Power Automate Flow

1. Crear flow con trigger **"Run a flow from Copilot Studio"**
2. Definir inputs (texto, número, boolean) y outputs
3. En Copilot Studio: nodo **Action > Call an action > Power Automate flow**
4. Mapear variables del topic a inputs del flow

Casos de uso:
- Consultar Dataverse / SharePoint
- Enviar emails de confirmación
- Crear tickets en Linear/Jira
- Llamar APIs externas con auth

### HTTP Request (Direct API Call)

En topics avanzados, usar el nodo **Action > Send HTTP request**:

```
URL: https://api.ejemplo.com/consulta
Method: GET
Headers: Authorization → Bearer {Global.ApiToken}
Response: guardar en Topic.ApiResponse (tipo: Record)
```

### Model Context Protocol (MCP)

Copilot Studio puede conectar tools MCP:

1. Agregar tool en **Settings > AI Capabilities > Add a tool**
2. Tipo: **MCP server** → URL del servidor MCP
3. El agente orquestador decide cuándo usarlo según la descripción

---

## Generative AI — Funciones clave

### Generative Answers (respuestas desde knowledge)

Configura en **Settings > AI Capabilities > Knowledge**:
- SharePoint (sitios, páginas, documentos)
- Sitios web públicos (crawl)
- Archivos subidos (PDF, Word, Excel)
- Dataverse tables
- Azure AI Search

El nodo **Generative Answers** en topics permite invocar knowledge de forma controlada:

```
Nodo: Generative Answers
Fuente: Knowledge sources configuradas
Prompt: Use {System.Activity.Text} para buscar en las fuentes.
```

### Generative Orchestration

Habilitada por defecto en agentes nuevos. El LLM decide automáticamente:
- Si el topic A, B o C maneja la intención
- Si invocar una action
- Si responder con knowledge source
- Si combinar topics + knowledge

**Buena práctica:** escribir descripciones claras de cada topic y action en lenguaje natural para guiar al orquestador.

---

## Canales de publicación

| Canal | Configuración |
|-------|---------------|
| **Microsoft Teams** | Directo desde Publish > Teams; requiere aprobación de admin |
| **Web Chat** | Embed con `<script>` HTML en cualquier sitio |
| **Power Pages** | Integración nativa con portales Power Pages |
| **Email** | Via Power Automate (no canal directo nativo) |
| **Telegram** | Configurar en Channels > Telegram con Bot Token |
| **Facebook Messenger** | App ID + App Secret de Facebook |
| **Direct Line API** | Integración custom vía REST; para apps propias |
| **Omnichannel** | Dynamics 365 Customer Service para escalada a humanos |

---

## Direct Line API (integración programática)

Para llamar al agente desde Umbral:

```
POST https://directline.botframework.com/v3/directline/conversations
Authorization: Bearer {DIRECT_LINE_SECRET}
→ Devuelve: conversationId, token

POST https://directline.botframework.com/v3/directline/conversations/{id}/activities
Authorization: Bearer {token}
Body: {"type": "message", "from": {"id": "user1"}, "text": "¿Cuál es mi saldo?"}

GET  https://directline.botframework.com/v3/directline/conversations/{id}/activities
→ Polling de respuestas del bot
```

---

## Buenas prácticas de diseño

### Topics

- Un topic = una intención clara (no mezclar múltiples intenciones)
- Escribir 5-10 trigger phrases variadas por topic
- Incluir variantes con errores ortográficos comunes
- Usar **Message Variation** para evitar respuestas repetitivas
- Siempre incluir un nodo final (End Conversation o Topic Redirect)

### Variables

- Prefijo `Global.` solo para datos necesarios entre topics
- Limpiar variables con **Variable Management** al inicio de topic si son reutilizadas
- Usar tipos específicos (Email, Number) en Question nodes para validación automática

### Performance y UX

- Limitar profundidad de conversación a 5-7 intercambios máximo
- Usar Adaptive Cards para inputs complejos (selección múltiple, formularios)
- Configurar timeout en acciones largas (> 30s): mostrar mensaje de "procesando..."
- Activar **Generative Answers** como fallback del topic Fallback

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| Topic no activa | Frases de trigger no reconocidas por NLU | Agregar más variantes; usar sinónimos; verificar idioma del agente |
| Action falla silenciosamente | Error en Power Automate flow | Agregar manejo de errores en el flow; verificar logs en Power Automate |
| Variable siempre vacía | Scope incorrecto (topic vs global) | Verificar prefijo; usar Global. si debe persistir |
| Respuesta generativa fuera de tema | Knowledge source muy amplia | Restringir fuentes; agregar instrucciones en System Prompt |
| Teams no muestra el bot | Publicación pendiente o sin aprobación | Ir a Publish > Teams; solicitar aprobación a admin de Teams |
| Direct Line timeout | Polling muy lento | Usar WebSocket en lugar de polling; aumentar timeout |
| Generative orchestration activa topic incorrecto | Descripción ambigua del topic | Mejorar descripción del topic; especificar casos de NO uso |

---

## Testing y depuración

- Usar el **Test Pane** en el canvas para conversaciones de prueba
- Ver variables en tiempo real en el panel lateral durante testing
- Revisar **Analytics** en Copilot Studio para: sesiones, temas top, abandono
- Usar **Conversation transcripts** para analizar conversaciones reales
- Activar **Logging** para integrar con Application Insights (Azure)

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/microsoft-copilot-studio/
- Generative orchestration: https://learn.microsoft.com/microsoft-copilot-studio/advanced-generative-actions
- Direct Line API: https://learn.microsoft.com/azure/bot-service/rest-api/bot-framework-rest-direct-line-3-0-api-reference
- Canales: https://learn.microsoft.com/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams
- Comunidad: https://powerusers.microsoft.com/t5/Microsoft-Copilot-Studio/ct-p/PVACommunity
