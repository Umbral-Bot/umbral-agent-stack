---
name: power-automate
description: >-
  Design, build, and debug Microsoft Power Automate cloud flows and desktop
  flows (PAD) using connectors, expressions, and triggers to automate business
  processes across Microsoft 365 and third-party services.
  Use when "create power automate flow", "automate email", "schedule task in power automate",
  "power automate connector", "cloud flow", "power automate desktop", "PAD flow",
  "automate sharepoint", "automate teams notification", "flow expression help".
metadata:
  openclaw:
    emoji: "\u26A1"
    requires:
      env: []
---

# Power Automate Skill

Rick puede asistir en el diseño, depuración y optimización de flujos de Power Automate (cloud flows y Power Automate Desktop / PAD).

Documentación oficial: https://learn.microsoft.com/power-automate/

---

## Tipos de flujo

| Tipo | Descripción | Trigger |
|------|-------------|---------|
| **Cloud Flow – Automated** | Se ejecuta cuando ocurre un evento | Correo recibido, ítem creado en SharePoint |
| **Cloud Flow – Instant** | Se dispara manualmente | Botón en Teams/móvil, llamada HTTP |
| **Cloud Flow – Scheduled** | Se ejecuta según cron | Cada día a las 8:00 |
| **Desktop Flow (PAD)** | Automatiza UI de escritorio / legacy | Invocado desde cloud flow |
| **Business Process Flow** | Guía de etapas en Dataverse | Avance de etapas en un proceso |

---

## Conectores clave

### Microsoft 365

| Conector | Acciones frecuentes |
|----------|---------------------|
| SharePoint | Create item, Update item, Get items (con filtro OData), Get file content |
| Outlook / Office 365 | Send email, Get emails, Create event, Reply to email |
| Microsoft Teams | Post message to chat/channel, Create meeting, Get team members |
| OneDrive for Business | Upload file, Get file content, List files |
| Excel Online (Business) | Add row, Get rows, Update row |
| Planner | Create task, Update task, List tasks |
| Dataverse | Add row, List rows (con filter), Update row, Delete row |

### Servicios de terceros

| Conector | Uso |
|----------|-----|
| HTTP (Premium) | Llamar a cualquier API REST |
| Azure Service Bus | Enviar/recibir mensajes de colas |
| SQL Server | Ejecutar query, Insert row |
| Salesforce | Create record, Get record |
| Approvals | Crear solicitud de aprobación, esperar respuesta |
| Adobe PDF Tools | Convertir, fusionar PDFs |

### Externos (ejemplos)
- Salesforce, ServiceNow, Jira, GitHub, Slack, SAP, DocuSign

## Expresiones y funciones comunes

Las expresiones se escriben con el prefijo `@` dentro de valores, o directamente en el editor de expresiones:

### Texto
```
concat('Hola, ', triggerBody()?['nombre'])
toUpper(variables('myVar'))
replace(body('Get_item')?['Title'], ' ', '_')
substring('PowerAutomate', 0, 5)     → 'Power'
```

### Fechas
```
utcNow()                                   → ISO 8601 actual
formatDateTime(utcNow(), 'dd/MM/yyyy')
addDays(utcNow(), 7)                       → +7 días
convertTimeZone(utcNow(), 'UTC', 'America/Mexico_City')
dayOfWeek(utcNow())                        → 0=Dom … 6=Sáb
```

### Condiciones y lógica
```
if(equals(variables('status'), 'done'), 'Completado', 'Pendiente')
and(greater(variables('count'), 0), not(empty(variables('name'))))
or(equals(triggerBody()?['type'], 'A'), equals(triggerBody()?['type'], 'B'))
empty(triggerBody()?['email'])
```

### Arrays y objetos
```
length(triggerBody()?['items'])
first(outputs('List_items')?['body/value'])
last(body('Get_items')?['value'])
join(variables('tagsArray'), ', ')
union(variables('arr1'), variables('arr2'))
contains(body('Get_items')?['value'], 'keyword')
```

### Datos de acciones
```
triggerOutputs()?['body/id']
outputs('Send_email')?['statusCode']
body('Parse_JSON')?['campo']
items('Apply_to_each')?['name']
```

### Variables
```
variables('myVariable')
setVariable('myVariable', 'nuevo valor')   // acción
```

---

## Flujo de ejemplo — Notificación de aprobación en Teams

```
Trigger: When a new item is created (SharePoint)
│
├─ Condición: ¿Status == "Pending Approval"?
│   ├─ Sí → Start and wait for an approval
│   │         ├─ Aprobado → Update item (Status = "Approved")
│   │         │              Post message to Teams: "✅ Aprobado: @{items('...')?['Title']}"
│   │         └─ Rechazado → Update item (Status = "Rejected")
│   │                         Send email to requestor
│   └─ No → Terminate (Cancelled)
```

---

## Power Automate Desktop (PAD) — Flujos de escritorio

PAD permite automatizar aplicaciones de escritorio (legacy, SAP, Excel local, web scraping):

```
// Ejemplo: Leer Excel, procesar y pegar en app web
Launch Excel → Read from Excel worksheet
For each row:
  → Launch browser → Navigate to URL
  → Fill text field: CurrentItem['nombre']
  → Click button: "Guardar"
  → Wait for element to appear
Close Excel
```

**Acciones clave de PAD:**
- `Launch application` / `Close application`
- `Click UI element` / `Set text field value`
- `Wait for web page to load` / `Extract data from web page`
- `Run script` (PowerShell, VBScript)
- `Read/Write text file`
- `Send key` (Ctrl+C, Enter, etc.)

PAD se integra con cloud flows mediante el conector **Desktop flows** (requiere gateway o máquina registrada).

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `429 Too Many Requests` | Rate limit del conector alcanzado | Agregar acción **Delay** (30s) + habilitar **Retry Policy** |
| `The expression is invalid` | Sintaxis de expresión incorrecta | Verificar comillas, corchetes y uso de `?['campo']` para nullables |
| `Workflow run was throttled` | Plan Free/Developer con límites | Revisar límites del plan; agregar Delay o cambiar trigger |
| `ActionFailed: Connection not authorized` | Conexión expirada o revocada | Re-autenticar la conexión en el portal |
| `The item does not exist` | ID o URL incorrecta en SharePoint | Verificar `siteAddress` + `id` con una acción **Get item** previa |
| `Size limit exceeded` | Payload supera límite del conector | Usar **chunking** o dividir en múltiples acciones |
| `Cannot read property of null` | Campo nullable no verificado | Usar `?['campo']` en lugar de `['campo']` |

---

## Buenas prácticas

- **Nombrar acciones descriptivamente**: `Get SharePoint Item - Solicitud` en lugar de `Get item`.
- **Usar variables** en lugar de expresiones inline repetidas para facilitar mantenimiento.
- **Scope de error**: Envolver acciones críticas en un bloque **Scope** con `Configure run after → Has failed` para manejo elegante.
- **Paralelismo**: En `Apply to each`, habilitar **Concurrency Control** (ej.: 5 hilos) para acelerar loops.
- **Evitar loops innecesarios**: Usar OData `$filter` en SharePoint/Dataverse para filtrar en origen, no en el flujo.
- **Entornos**: Desarrollar en entorno de desarrollo y promover a producción vía soluciones (Solutions).

---

## Casos de uso típicos

- Aprobar solicitudes automáticamente según criterios y notificar por Teams/email.
- Sincronizar datos entre SharePoint y Dataverse cuando se crea/actualiza un ítem.
- Generar reportes PDF diarios y enviarlos por correo con adjunto.
- Disparar flujos desde Make.com o n8n vía HTTP trigger (webhook).
- Automatizar entrada de datos en aplicaciones legacy usando PAD.
- Procesar formularios de Power Apps y registrar resultados en SharePoint.

Acciones PAD frecuentes:
- `System.RunApplication` — lanzar apps
- `Web.LaunchEdge` / `Web.Navigate` — automatizar browser
- `WebAutomation.Click` / `FillTextBox` — interactuar con web
- `UIAutomation.Click` / `GetTextFrom` — apps desktop
- `File.ReadText` / `WriteText` — manipular archivos
- `Excel.*` — automatización completa de Excel

## Errores frecuentes

- Documentación oficial: https://learn.microsoft.com/power-automate/
- Referencia de conectores: https://powerautomate.microsoft.com/en-us/connectors/
- Referencia de expresiones: https://learn.microsoft.com/azure/logic-apps/workflow-definition-language-functions-reference
- Guías de codificación: https://learn.microsoft.com/power-automate/guidance/coding-guidelines/
- PAD (Desktop): https://learn.microsoft.com/power-automate/desktop-flows/introduction
