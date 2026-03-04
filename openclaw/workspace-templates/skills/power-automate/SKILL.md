---
name: power-automate
description: >-
  Automatizar flujos de trabajo en la nube y en escritorio con Microsoft Power Automate.
  Cubre cloud flows (automatizados, programados, instantáneos), Power Automate Desktop (PAD),
  conectores premium y expresiones del lenguaje de flujo.
  Use when "crear flujo power automate", "automatizar con power automate", "cloud flow",
  "power automate desktop", "flujo programado", "trigger power automate",
  "conectar sharepoint power automate", "automate workflow microsoft",
  "schedule flow", "approval flow", "power automate expression".
metadata:
  openclaw:
    emoji: "\u26A1"
    requires:
      env: []
---

# Power Automate Skill

Rick puede diseñar, ejecutar y depurar flujos de Power Automate para automatizar procesos de negocio conectando Microsoft 365, Azure, Dataverse y cientos de servicios externos.

## Tipos de flujos

| Tipo | Trigger | Caso de uso |
|------|---------|-------------|
| Automated flow | Evento (e.g. email recibido, fila SharePoint nueva) | Reaccionar a cambios en tiempo real |
| Scheduled flow | Recurrencia (cron) | Reportes diarios, sincronización periódica |
| Instant flow | Manual o botón | Aprobaciones on-demand, notificaciones |
| Desktop flow (PAD) | RPA — interfaz gráfica | Automatizar apps legacy sin API |
| Process mining flow | Análisis de procesos | Identificar ineficiencias en procesos |

## Conectores principales

### Microsoft 365
- **SharePoint**: leer/escribir listas, bibliotecas de documentos
- **Outlook / Exchange**: enviar emails, gestionar calendarios
- **Teams**: enviar mensajes, crear chats, mencionar usuarios
- **OneDrive**: crear, mover, copiar archivos
- **Excel Online (Business)**: leer/escribir tablas, ejecutar scripts
- **Forms**: procesar respuestas de formularios
- **Planner**: crear y actualizar tareas

### Azure y Datos
- **Dataverse**: CRUD en tablas de entorno Power Platform
- **Azure Blob Storage**: gestión de archivos en blobs
- **Azure SQL**: queries SQL desde flujos
- **Azure Key Vault**: leer secretos de forma segura

### Automatización y Aprobación
- **Approvals**: flujos de aprobación multi-etapa
- **HTTP**: llamadas REST a cualquier API
- **HTTP + Swagger**: integración con OpenAPI specs

### Externos (ejemplos)
- Salesforce, ServiceNow, Jira, GitHub, Slack, SAP, DocuSign

## Expresiones clave (Workflow Definition Language)

Las expresiones se escriben en el campo de fórmulas anteponiendo `@` o usando `@{expresión}` inline.

### Texto
```
concat('Hola ', triggerBody()?['Name'])
replace(body('Get_item')?['Title'], ' ', '_')
toLower(variables('status'))
toUpper(outputs('Compose'))
trim(triggerBody()?['email'])
substring(body('Get_email')?['Subject'], 0, 50)
split(variables('csv'), ',')
join(variables('array'), '; ')
```

### Números y Lógica
```
if(equals(variables('count'), 0), 'vacío', 'tiene datos')
greater(variables('total'), 100)
less(variables('score'), 50)
and(equals(variables('status'), 'active'), greater(variables('age'), 18))
or(empty(variables('name')), empty(variables('email')))
coalesce(body('Get_item')?['Description'], 'Sin descripción')
int(variables('amount_str'))
float(variables('price_str'))
```

### Fechas y Tiempo
```
utcNow()
utcNow('yyyy-MM-dd')
addDays(utcNow(), 7)
addHours(utcNow(), -3)
formatDateTime(utcNow(), 'dd/MM/yyyy HH:mm')
formatDateTime(triggerBody()?['fecha'], 'yyyy-MM-dd')
convertTimeZone(utcNow(), 'UTC', 'Argentina Standard Time')
```

### Colecciones y Arrays
```
first(body('Get_items')?['value'])
last(variables('items'))
length(body('Get_items')?['value'])
union(variables('lista1'), variables('lista2'))
intersection(variables('a'), variables('b'))
contains(variables('tags'), 'urgente')
item()?['Title']           // dentro de Apply to each
items('Apply_to_each')?['ID']
```

### JSON y Datos
```
json(body('HTTP'))
string(variables('objeto'))
base64(variables('texto'))
base64ToString(variables('encoded'))
body('Parse_JSON')?['campo_anidado']?['subcampo']
triggerBody()?['value']?[0]?['name']
```

### Variables de entorno y sistema
```
parameters('SharePoint_URL')
workflow()['name']
workflow()['run']['name']
environment()['name']
```

## Power Automate Desktop (PAD) — Acciones clave

PAD usa acciones drag-and-drop para RPA (Robotic Process Automation):

```
# Flujo básico PAD
Variables.Set: %NombreArchivo% = "reporte.xlsx"
Excel.Launch: Path: "C:\datos\%NombreArchivo%"
Excel.ReadCell: Row: 2, Column: 1 → %valor%
Conditionals.If: %valor% > 100
  Email.Send: To: "gerente@empresa.com", Subject: "Alerta: valor superado"
Conditionals.End
Excel.CloseAndSave
```

Acciones PAD frecuentes:
- `System.RunApplication` — lanzar apps
- `Web.LaunchEdge` / `Web.Navigate` — automatizar browser
- `WebAutomation.Click` / `FillTextBox` — interactuar con web
- `UIAutomation.Click` / `GetTextFrom` — apps desktop
- `File.ReadText` / `WriteText` — manipular archivos
- `Excel.*` — automatización completa de Excel

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `BadRequest (400)` en conector | Payload inválido o campo requerido vacío | Verificar campos obligatorios; usar `coalesce()` |
| `Unauthorized (401)` | Conexión expirada o permisos insuficientes | Recrear conexión en Power Automate portal |
| `Forbidden (403)` | El usuario del conector no tiene acceso | Verificar permisos en SharePoint/Teams/etc. |
| `Timeout (408)` | Acción tardó más de 120s | Fragmentar en pasos más pequeños; usar async |
| `TooManyRequests (429)` | Rate limit del conector | Agregar `Delay` entre iteraciones; usar concurrency control |
| `InvalidTemplate` | Error en expresión | Validar con el editor de expresiones; revisar `?` para nullables |
| Loop infinito | Trigger activa el mismo flujo | Agregar condición de control o filtro de trigger |
| `Apply to each` lento | Concurrencia 1 por defecto | Habilitar concurrencia paralela (máx 50) en el loop |

## Patrones comunes

### Aprobación de solicitudes
```
Trigger: Form → Enviar email de aprobación (Approvals) →
  If approved: Actualizar lista SharePoint → Notificar solicitante
  If rejected: Notificar con motivo
```

### Sincronización bidireccional
```
Trigger: When item modified (SharePoint) →
  Condition: Modified by != "Service Account" →
  Update row in SQL / Dataverse
```

### Reporte diario programado
```
Trigger: Recurrence (8:00 AM) →
  Get items (SharePoint) →
  Create HTML table →
  Send email with table to distribution list
```

## Variables de entorno (Environment Variables)

Las variables de entorno en Power Platform permiten parametrizar flujos entre ambientes:
- Tipo: Text, Number, Boolean, JSON, Data Source, Secret
- Se crean en **Solutions** → **Environment Variables**
- Referencia en flujo: `parameters('NombreVariable')`

## Documentación oficial

- Referencia de expresiones: https://learn.microsoft.com/power-automate/use-expressions-in-conditions
- Conectores: https://learn.microsoft.com/connectors/
- Power Automate Desktop: https://learn.microsoft.com/power-automate/desktop-flows/introduction
- Guías de código: https://learn.microsoft.com/power-automate/guidance/coding-guidelines/
