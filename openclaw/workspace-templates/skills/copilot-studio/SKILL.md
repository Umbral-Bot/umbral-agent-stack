---
name: copilot-studio
description: >-
  Build and configure Microsoft Copilot Studio conversational agents using topics,
  actions, Power Automate flows, entities, variables, and the REST API for deployment
  across Teams, web, and custom channels.
  Use when "copilot studio agent", "create bot copilot studio", "copilot topic",
  "copilot action", "microsoft bot builder", "teams bot copilot studio",
  "copilot studio topic trigger", "conversational ai microsoft", "copilot studio flow",
  "agent plugin copilot", "copilot studio variables", "deploy copilot to teams".
metadata:
  openclaw:
    emoji: "\U0001F916"
    requires:
      env: []
---

# Microsoft Copilot Studio Skill

Rick puede asistir en el diseño y configuración de agentes conversacionales en Microsoft Copilot Studio — la plataforma low-code de Microsoft para crear copilots (chatbots) integrados con Microsoft 365 y servicios externos.

Documentación oficial: https://learn.microsoft.com/microsoft-copilot-studio/

---

## Arquitectura general

```
Usuario (Teams / Web / Custom)
         ↓
    [Canal de publicación]
         ↓
    [Copilot Studio Agent]
         ├── Topics          → lógica de conversación
         ├── Knowledge       → bases de conocimiento (SharePoint, URL, archivos)
         ├── Actions/Tools   → Power Automate, HTTP, MCP, A2A
         └── Entities        → extracción de entidades del input del usuario
         ↓
    [Dataverse] ← almacenamiento de variables, contexto
```

---

## Componentes clave

### Topics (Temas)

Los topics son la unidad fundamental de la conversación. Definen cómo el agente responde a los usuarios.

| Tipo de topic | Descripción |
|---------------|-------------|
| **Trigger phrase topic** | Se activa cuando el usuario escribe algo similar a las frases de disparo |
| **System topics** | Topics predefinidos: Greeting, Goodbye, Escalate, Error, Fallback |
| **Conversational boosting** | Responde directamente desde Knowledge usando IA generativa |
| **Custom topic** | Topic creado por el desarrollador para una tarea específica |

**Configuración de un topic:**
1. `Topics → + Add topic → From blank`
2. Definir **frases de disparo** (trigger phrases): al menos 5 variaciones.
3. Agregar **nodos de conversación** en el canvas.

### Nodos de conversación

| Nodo | Función |
|------|---------|
| **Message** | Enviar mensaje al usuario (texto, tarjeta adaptiva, imagen) |
| **Question** | Hacer pregunta y guardar respuesta en variable |
| **Condition** | Bifurcación lógica (if/else) |
| **Action** | Ejecutar Power Automate flow, HTTP call, o plugin |
| **Redirect** | Redirigir a otro topic |
| **End conversation** | Finalizar el topic |
| **Go to step** | Saltar a un nodo específico dentro del topic |
| **Set variable** | Asignar valor a una variable |
| **Send adaptive card** | Mostrar tarjeta con formato rico |

---

## Variables

### Tipos de variable

| Tipo | Scope | Descripción |
|------|-------|-------------|
| **Topic variable** | Solo el topic actual | Se borra al salir del topic |
| **Global variable** | Todo el agente y sesión | Persiste durante toda la conversación |
| **System variable** | Solo lectura | Info del usuario, canal, actividad |

### Variables de sistema más usadas

```
System.User.DisplayName        → Nombre del usuario
System.User.Id                 → ID del usuario (AAD)
System.User.Email              → Email del usuario
System.Channel                 → Canal de comunicación (teams, web...)
System.Conversation.Id         → ID de la conversación
System.Activity.Text           → Último mensaje del usuario
System.LastTopic.Name          → Nombre del último topic activado
System.Transcript              → Transcript completo de la conversación
```

### Crear y usar variables

```
// En nodo Question:
Variable name: Var_UserInput    (topic variable)
Variable name: Global.UserCity  (global variable)

// En nodo Condition:
Var_UserInput is equal to "ayuda"
Global.UserCity contains "Ciudad de México"

// En nodo Message:
"Hola, {System.User.DisplayName}. Tu ciudad es {Global.UserCity}."
```

---

## Entities (Entidades)

Las entidades extraen información estructurada del input del usuario.

### Tipos de entidad

| Entidad | Extrae |
|---------|--------|
| **Person name** | Nombres de personas |
| **Email** | Direcciones de email |
| **Number** | Números |
| **Date and time** | Fechas y horas |
| **Duration** | Duraciones ("por 3 días") |
| **Money** | Cantidades monetarias |
| **Percentage** | Porcentajes |
| **Boolean** | Sí/No, Verdadero/Falso |
| **Custom list entity** | Lista de valores específicos del negocio |
| **Regular expression** | Extracción por patrón regex |

**Ejemplo: entidad personalizada para tipo de servicio**
```
Nombre: TipoServicio
Tipo: Closed list (Lista cerrada)
Valores:
  - "soporte técnico" → soporte
  - "facturación", "cobro" → facturacion
  - "consulta general" → consulta
```

---

## Actions (Acciones)

Las acciones conectan el agente a sistemas externos.

### 1. Power Automate Flow

```
En el topic → Nodo "Action" → Create a flow
// El flow aparece en Power Automate con trigger "When an agent calls a flow"
// Inputs: variables del topic → parámetros del flow
// Outputs: resultados del flow → variables del topic
```

**Ejemplo de flow integrado:**
```
Copilot: "Busco los pedidos del cliente {Var_ClienteID}"
  ↓
Action → Power Automate flow:
  Input: ClienteID = Var_ClienteID
  → Consulta SharePoint/Dataverse
  → Retorna: ListaPedidos (string con resultados)
  Output: Var_ResultadoPedidos = ListaPedidos
  ↓
Message: "Aquí están tus pedidos: {Var_ResultadoPedidos}"
```

### 2. HTTP Request (REST API)

```
Nodo Action → Call an API
  URL: https://api.ejemplo.com/clientes/{Var_ClienteID}
  Method: GET
  Headers: Authorization: Bearer [WORKER_TOKEN]
  Response: Guardar en variable Var_APIResponse
```

### 3. Model Context Protocol (MCP)

MCP permite que el agente descubra y use herramientas dinámicamente:
```
Action → Add tool → Model Context Protocol (MCP)
  Server URL: https://mi-servidor-mcp.com/sse
  Tools disponibles: se descubren automáticamente
```

### 4. Agent-to-Agent (A2A)

```
Action → Add agent
  Seleccionar otro agente de Copilot Studio como herramienta
  El agente principal orquesta, el sub-agente ejecuta tareas especializadas
```

---

## Knowledge (Bases de conocimiento)

El agente puede responder preguntas directamente desde fuentes de conocimiento sin definir un topic específico:

| Fuente | Cómo agregar |
|--------|--------------|
| **SharePoint** | URL del sitio de SharePoint |
| **Página web / URL** | URL pública del sitio |
| **Archivo (PDF, Word, etc.)** | Upload directo en Copilot Studio |
| **Dataverse** | Seleccionar tabla de Dataverse |
| **Azure OpenAI** | Conectar Azure OpenAI con base de datos vectorial |

Activar: `Knowledge → + Add knowledge → [tipo de fuente]`

---

## Canales de publicación

Copilot Studio permite publicar en múltiples canales sin cambiar la lógica del agente:

| Canal | Requisito |
|-------|-----------|
| **Microsoft Teams** | Publicar → Teams → Aprobar en Teams Admin Center |
| **Web (Chat widget)** | Copiar el embed code HTML |
| **Custom website** | iframe o Direct Line |
| **Power Apps** | Integrar como componente en canvas app |
| **Dynamics 365** | Customer Service, Sales |
| **Azure Bot Service** | Registro en Azure Portal |
| **Telegram, Slack** | Vía Azure Bot Service + Direct Line |

---

## Adaptive Cards (Tarjetas adaptativas)

Copilot Studio puede enviar tarjetas adaptativas (JSON) como respuestas ricas:

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "📋 Resumen del pedido",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Pedido #", "value": "${PedidoID}"},
        {"title": "Estado", "value": "${Estado}"},
        {"title": "Total", "value": "${Total}"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "Ver detalle",
      "data": {"accion": "ver_detalle", "id": "${PedidoID}"}
    }
  ]
}
```

---

## Patrones conversacionales comunes

### Slot filling (recopilación de datos)

```
Topic: Crear Solicitud
Trigger: "nueva solicitud", "quiero hacer una solicitud"

→ Question: "¿Cuál es tu nombre?" → Var_Nombre (Text)
→ Question: "¿Tipo de solicitud?" → Var_Tipo (TipoSolicitud entity)
→ Question: "¿Fecha requerida?" → Var_Fecha (Date and time)
→ Condition: ¿Var_Tipo = "urgente"?
    ├── Sí → Action: Notificar supervisor vía Power Automate
    └── No → Action: Crear ticket en SharePoint
→ Message: "Tu solicitud fue registrada. ID: {Var_TicketID}"
```

### Escalation a agente humano

```
System Topic: Escalate (ya existe por defecto)
  → Nodo Message: "Te conectaré con un agente humano..."
  → Nodo "Transfer conversation" → Agente de soporte (Omnichannel)
```

### Fallback con IA generativa

```
System Topic: Fallback (cuando ningún topic coincide)
  → Activar "Generative answers" → Knowledge sources
  → El agente intenta responder con las bases de conocimiento disponibles
  → Si no encuentra → Escalar o mostrar mensaje de disculpa
```

---

## Autenticación de usuarios

Copilot Studio soporta autenticación de usuarios para acceder a datos personalizados:

| Modo | Descripción |
|------|-------------|
| **No authentication** | Anónimo — cualquier usuario |
| **Only for Teams/Power Apps** | Autenticación automática con la sesión del usuario en M365 |
| **Manual (Azure AD)** | OAuth 2.0 con app registration en Azure AD |

Con autenticación habilitada, `System.User.Email` y `System.User.Id` están disponibles.

---

## Deployment y testing

```
// Probar en el panel "Test your agent" (chat en tiempo real dentro de Copilot Studio)
// Activar "Track between topics" para ver el flujo de topics durante el test

// Publicar en Teams:
Publish → Microsoft Teams → Submit for admin approval

// Compartir con usuarios específicos (durante testing):
Publish → Share → Add users/groups de Azure AD
```

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `Topic not triggered` | Frases de disparo no son variadas o relevantes | Agregar más variaciones; habilitar Generative Answers para NLU mejorado |
| `Variable is empty` | Variable no fue asignada antes de usarla | Agregar nodo Condition para verificar si la variable está vacía |
| `Action failed: Flow error` | Power Automate flow falló | Revisar el historial del flow en Power Automate; verificar permisos de conexión |
| `Knowledge not responding` | Fuente de conocimiento no indexada | Esperar a que se complete la indexación; verificar permisos en SharePoint |
| `Adaptive card not rendering` | JSON inválido o versión incompatible | Validar en https://adaptivecards.io/designer/ |
| `User not authenticated` | Autenticación requerida pero no configurada | Verificar config de autenticación en Settings → Security |
| `Loop detected` | Topic redirige a sí mismo | Revisar nodos Redirect; agregar condición de salida |
| `HTTP action timeout` | API externa tarda demasiado | Aumentar timeout en la acción o usar llamada asincrónica con Power Automate |

---

## Integración con Umbral Agent Stack

Copilot Studio puede invocar el Worker de Umbral como acción HTTP:

```
Topic: Investigar tema
→ Question: "¿Qué quieres que investigue?" → Var_Consulta
→ Action → Call an API:
    URL: http://vps-ip:8088/execute
    Method: POST
    Headers: Authorization: Bearer WORKER_TOKEN
    Body:
    {
      "task_type": "research.web",
      "input": {"query": "{Var_Consulta}", "max_results": 5}
    }
→ Message: "Investigando '{Var_Consulta}'... resultados: {Var_APIResponse.result}"
```

---

## Buenas prácticas

- **Frases de disparo**: al menos 5 variaciones naturales por topic; no copiar frases entre topics.
- **Fallback inteligente**: siempre configurar el topic Fallback con Knowledge o escalación.
- **Variables globales con prefijo**: `Global.VarNombre` para distinguirlas de variables de topic.
- **Separar topics por función**: un topic = una tarea clara. No hacer topics "todo en uno".
- **Test antes de publicar**: usar el panel de test extensivamente; probar frases límite y errores.
- **Adaptive cards para UX**: usar tarjetas en lugar de texto plano para respuestas estructuradas.
- **Monitorear con Analytics**: Copilot Studio incluye analytics de sesiones, frases no reconocidas y abandono.
- **Versionar**: antes de cambios grandes, exportar el agente como solución de Dataverse.

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/microsoft-copilot-studio/
- Topics: https://learn.microsoft.com/microsoft-copilot-studio/guidance/topics-overview
- Actions: https://learn.microsoft.com/microsoft-copilot-studio/advanced-plugin-actions
- Adaptive Cards designer: https://adaptivecards.io/designer/
- Canal Teams: https://learn.microsoft.com/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams
- Autenticación: https://learn.microsoft.com/microsoft-copilot-studio/configuration-authentication-overview
