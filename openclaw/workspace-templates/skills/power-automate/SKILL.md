---
name: power-automate
description: >-
  Asistente para crear y depurar flujos de automatización con Microsoft Power
  Automate: cloud flows, desktop flows (PAD), conectores, expresiones y triggers.
  Use when "power automate", "automatizar flujo", "cloud flow", "desktop flow",
  "PAD", "conector power automate", "trigger automático", "flow condition",
  "expresión power automate", "automatizar tarea repetitiva", "schedule flow".
metadata:
  openclaw:
    emoji: "\u26A1"
    requires:
      env: []
---

# Power Automate Skill

Rick usa este skill para guiar la creación, depuración y optimización de flujos de automatización con Microsoft Power Automate. Cubre cloud flows, Power Automate Desktop (PAD), conectores y expresiones.

Fuente oficial: https://learn.microsoft.com/power-automate/

---

## Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Cloud Flow** | Flujo que corre en la nube; tipos: Automated, Instant, Scheduled |
| **Desktop Flow (PAD)** | Flujo de automatización de escritorio con Power Automate Desktop; requiere gateway o acceso attended/unattended |
| **Trigger** | Evento que inicia el flujo (mensaje nuevo, hora programada, formulario enviado) |
| **Action** | Paso del flujo que hace algo (enviar email, crear fila, llamar HTTP) |
| **Connector** | Adaptador que conecta Power Automate con servicios externos |
| **Connection Reference** | Referencia desacoplada de conexión; recomendada para ALM y soluciones |
| **Environment** | Contenedor de flujos, apps y datos de Power Platform |
| **Solution** | Paquete exportable de flujos + apps + conectores para ALM |

---

## Tipos de flujos

### Cloud Flows

| Tipo | Trigger | Casos de uso |
|------|---------|--------------|
| **Automated** | Evento automático (new email, row added) | Sincronización de datos, notificaciones |
| **Instant** | Manual (botón en app, Teams) | Aprobaciones, acciones bajo demanda |
| **Scheduled** | Recurrencia (diario, semanal) | Reportes, limpiezas, backups |

### Desktop Flows (PAD)

Automatizan UI de apps de escritorio/web cuando no hay API disponible.

| Tipo | Descripción |
|------|-------------|
| **Attended** | El usuario está presente; interacción con escritorio visible |
| **Unattended** | Corre en segundo plano, sin usuario; requiere licencia premium |

---

## Conectores más usados

| Conector | Tipo | Casos de uso |
|----------|------|--------------|
| Office 365 Outlook | Standard | Emails, calendario, contactos |
| SharePoint | Standard | Listas, documentos, permisos |
| Microsoft Teams | Standard | Mensajes, canales, reuniones |
| Excel Online (Business) | Standard | Leer/escribir filas y tablas |
| Dataverse | Premium | CRUD en Common Data Service |
| HTTP | Premium | Llamadas REST a APIs externas |
| Approvals | Standard | Flujos de aprobación |
| Azure Blob Storage | Premium | Archivos en nube Azure |
| SQL Server | Premium | Bases de datos relacionales |
| Planner | Standard | Tareas y planes de equipo |

**Licencias:** conectores Standard → licencia M365. Conectores Premium → licencia Power Automate Premium o per-flow.

---

## Expresiones clave (lenguaje de fórmulas)

Power Automate usa [lenguaje de expresiones de Azure Logic Apps](https://learn.microsoft.com/power-automate/use-expressions-in-conditions).

### Cadenas de texto

```
concat('Hola ', triggerBody()?['name'])
toLower(body('Get_item')?['Title'])
toUpper(variables('miVar'))
substring('Power Automate', 6, 8)    → 'Automate'
replace('error_code', '_', '-')
trim('  texto  ')
split('a,b,c', ',')                   → array
```

### Fechas y horas

```
utcNow()                              → ISO 8601 actual
convertTimeZone(utcNow(), 'UTC', 'Argentina Standard Time')
addDays(utcNow(), -7)
formatDateTime(utcNow(), 'yyyy-MM-dd')
dayOfWeek(utcNow())                   → 0=Dom … 6=Sáb
```

### Condicionales y lógica

```
if(equals(variables('estado'), 'activo'), 'Sí', 'No')
and(greater(length(body), 0), not(empty(body)))
or(equals(status, 200), equals(status, 201))
empty(triggerBody()?['email'])
```

### Manejo de datos

```
length(variables('miArray'))
first(body('List_items')?['value'])
last(body('List_items')?['value'])
union(array1, array2)
intersection(array1, array2)
json('{"key": "value"}')
string(123)
int('42')
float('3.14')
```

### Acceso a valores de pasos anteriores

```
triggerBody()?['campo']               → datos del trigger
body('Nombre_del_paso')?['campo']     → output de un paso
outputs('Nombre_del_paso')?['headers']
variables('miVariable')
items('Apply_to_each')                → elemento actual en loop
```

---

## Patrones frecuentes

### Aprobación con timeout

1. Trigger: evento (email, Teams)
2. Action: **Start and wait for an approval** (tipo: Approve/Reject)
3. Condición: `outputs('Approval')?['body/outcome']` equals `'Approve'`
4. Branch Yes: acción aprobada; Branch No: rechazar + notificar

### Procesar lista de items (Apply to each)

1. Obtener lista (Get items de SharePoint, List rows de Excel)
2. **Apply to each** sobre `body('Get_items')?['value']`
3. Dentro del loop: `items('Apply_to_each')?['campo']`

### Error handling con Scope + Configure run after

1. Envolver acciones en un **Scope**
2. Agregar acción de manejo de errores con **Configure run after** → `has failed`
3. En el branch de error: enviar email de alerta, actualizar log

### Llamar API REST externa

```
Action: HTTP
Method: POST
URI: https://api.ejemplo.com/endpoint
Headers: {"Authorization": "Bearer @{variables('token')}", "Content-Type": "application/json"}
Body: {"campo": "@{triggerBody()?['valor']}"}
```

---

## Triggers más comunes

| Trigger | Conector | Descripción |
|---------|----------|-------------|
| When a new email arrives | Outlook | Email en bandeja o carpeta |
| When an item is created | SharePoint | Nueva fila en lista |
| When a file is created | OneDrive/SharePoint | Nuevo archivo en carpeta |
| Recurrence | Scheduled | Cada N minutos/horas/días |
| When a HTTP request is received | HTTP | Webhook entrante |
| When an approval is completed | Approvals | Respuesta de aprobación |
| When a row is added to a table | Excel Online | Nueva fila en tabla Excel |
| Manually trigger a flow | Instant | Botón o Teams |

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| `The expression is invalid` | Sintaxis de expresión incorrecta | Verificar comillas, paréntesis y nombres de paso |
| `Connection not authorized` | Token expirado o permisos insuficientes | Reconectar conexión en Power Automate > Connections |
| `Action failed: 429 Too Many Requests` | Rate limit del conector | Agregar **Delay** o usar retry policy |
| `Object reference not set` | Campo nulo sin manejo | Usar `?['campo']` (null-safe) + `empty()` para validar |
| `Flow timeout (30 days)` | Approval o loop muy largo | Dividir flujo o usar flujos hijos |
| `Concurrency limit reached` | Muchas ejecuciones paralelas | Configurar concurrency control en trigger settings |
| Desktop Flow: `Element not found` | Selector roto por cambio de UI | Actualizar selector en PAD; usar esperas inteligentes |

---

## ALM y soluciones

- Crear flujos **dentro de soluciones** para exportar entre entornos.
- Usar **Connection References** (no conexiones directas) en flujos de soluciones.
- Usar **Environment Variables** para URLs y configuraciones por entorno.
- Pipeline: Desarrollo → Test → Producción via Power Platform CLI (`pac solution export/import`).

---

## Power Automate Desktop (PAD) — Acciones clave

```
# Variables
Set variable → nombre / valor
# UI Automation
Click UI element → selector
Get text from window → campo de texto
Fill text field → campo / texto
# Web
Launch new browser (Chrome/Edge)
Go to web page → URL
Click link on web page → selector
Get details of web page element → atributo
# Excel
Launch Excel → ruta archivo
Read from Excel worksheet → columna/fila inicio/fin
Write to Excel worksheet → valor, columna, fila
# Conditionals & Loops
If / Else if / Else / End
Loop while / For each / End loop
```

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/power-automate/
- Referencia de expresiones: https://learn.microsoft.com/azure/logic-apps/workflow-definition-language-functions-reference
- Conectores disponibles: https://learn.microsoft.com/connectors/connector-reference/
- PAD acciones: https://learn.microsoft.com/power-automate/desktop-flows/actions-reference
- Comunidad: https://powerusers.microsoft.com/t5/Microsoft-Power-Automate/ct-p/MPACommunity
