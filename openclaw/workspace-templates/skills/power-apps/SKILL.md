---
name: power-apps
description: >-
  Crear aplicaciones de negocio con Microsoft Power Apps sin necesidad de código profundo.
  Cubre canvas apps, model-driven apps, Power Fx (fórmulas), conectores de datos y despliegue.
  Use when "crear power app", "canvas app", "model driven app", "power apps formula",
  "power fx", "power apps connector", "app sin código", "low-code app microsoft",
  "power apps sharepoint", "power apps dataverse", "gallery power apps",
  "patch power apps", "form power apps".
metadata:
  openclaw:
    emoji: "\U0001F4F1"
    requires:
      env: []
---

# Power Apps Skill

Rick puede guiar el diseño y desarrollo de aplicaciones Power Apps, incluyendo fórmulas Power Fx, integración de conectores, lógica de negocio y despliegue a Microsoft Teams o dispositivos móviles.

## Tipos de aplicaciones

| Tipo | Descripción | Mejor para |
|------|-------------|------------|
| Canvas App | Diseño libre con arrastrar y soltar; fórmulas Power Fx | Apps personalizadas, móvil/tablet |
| Model-Driven App | Basada en Dataverse; estructura de datos primero | CRM, gestión de casos, procesos |
| Power Pages | Portal web externo con formularios y datos | Portales de cliente, registro, soporte |

## Power Fx — Fórmulas esenciales

Power Fx es un lenguaje de fórmulas declarativo similar a Excel. Se aplica en propiedades de controles.

### Navegación y pantallas
```powerfx
// Navegar a otra pantalla
Navigate(PantallaDetalle, ScreenTransition.Fade)

// Navegar con datos
Navigate(PantallaEdicion, ScreenTransition.None, {recordID: Gallery1.Selected.ID})

// Ir atrás
Back()

// Navegar desde Timer o botón
If(varCargando, Navigate(PantallaCarga), Navigate(PantallaInicio))
```

### Variables
```powerfx
// Variable global (persiste entre pantallas)
Set(varUsuario, User().Email)
Set(varTotal, Sum(colItems, Precio))

// Variable de contexto (solo pantalla actual)
UpdateContext({varModo: "edicion", varID: Gallery1.Selected.ID})

// Variable de colección (tabla en memoria)
Collect(colCarrito, {Producto: "A", Precio: 100})
ClearCollect(colFiltrado, Filter(colItems, Activo = true))
Clear(colCarrito)
```

### Consultas y filtros de datos
```powerfx
// Filtrar fuente de datos
Filter(Productos, Categoria = "Electrónica" && Precio < 500)

// Buscar texto
Filter(Clientes, StartsWith(Nombre, TextInput1.Text))
Search(Empleados, TextBusqueda.Text, "Nombre", "Email")

// Lookup (buscar un solo registro)
LookUp(Pedidos, ID = Gallery1.Selected.ID)
LookUp(Productos, SKU = varSKU, Descripcion)

// Ordenar
Sort(Productos, Precio, SortOrder.Descending)
SortByColumns(Clientes, "Apellido", SortOrder.Ascending)

// Primeros N registros
FirstN(Pedidos, 10)
LastN(Logs, 5)
```

### Operaciones CRUD en datos
```powerfx
// Crear / actualizar (Patch)
Patch(Clientes,
  {ID: varID, Nombre: txtNombre.Text, Email: txtEmail.Text}
)

// Crear nuevo registro
Patch(Pedidos, Defaults(Pedidos),
  {Producto: ddProducto.Selected.Nombre, Cantidad: Slider1.Value}
)

// Actualizar múltiples registros
ForAll(colSeleccionados,
  Patch(Tareas, LookUp(Tareas, ID = ThisRecord.ID), {Estado: "Completado"})
)

// Eliminar registro
Remove(Clientes, Gallery1.Selected)
RemoveIf(Logs, FechaCreacion < DateAdd(Today(), -30, Days))

// Submit de formulario
SubmitForm(Form1)
ResetForm(Form1)
```

### Funciones de texto y datos
```powerfx
// Texto
Concatenate("Hola ", User().FullName)
Left(txtCodigo.Text, 3)
Mid(txtTexto.Text, 2, 5)
Len(txtDescripcion.Text)
Upper(Nombre)
Lower(Email)
Trim(txtInput.Text)
Replace(texto, " ", "_")
Text(Today(), "dd/mm/yyyy")
Text(Precio, "$#,##0.00")
Value("123.45")
```

### Lógica y condiciones
```powerfx
// If simple
If(varLogueado, "Bienvenido", "Por favor inicie sesión")

// If con múltiples condiciones
If(
  Slider1.Value > 80, "Alto",
  Slider1.Value > 50, "Medio",
  "Bajo"
)

// Switch
Switch(ddEstado.Selected.Value,
  "activo", Color.Green,
  "pendiente", Color.Yellow,
  "inactivo", Color.Red
)

// IsBlank y Coalesce
IsBlank(txtNombre.Text)
IsEmpty(colCarrito)
Coalesce(txtEmail.Text, "no-email@dominio.com")
```

### Fechas y tiempo
```powerfx
Today()                          // Fecha actual (sin hora)
Now()                            // Fecha y hora actuales
DateAdd(Today(), 7, Days)        // +7 días
DateDiff(FechaInicio, Hoy, Days) // Diferencia en días
Date(2026, 3, 15)                // Fecha específica
Year(Today())  Month(Now())  Day(Today())
Weekday(Today())
Text(Now(), "dd/mm/yyyy hh:mm")
```

### Agregaciones
```powerfx
Sum(colPedidos, Monto)
Average(colCalificaciones, Valor)
Min(colProductos, Precio)
Max(colVentas, Cantidad)
Count(Filter(Tareas, Completada = true))
CountIf(colItems, Precio > 100)
```

## Conectores disponibles

### Datos propios de Microsoft
- **SharePoint** — listas y bibliotecas (más común)
- **Dataverse** — base de datos relacional de Power Platform
- **Excel Online (Business)** — tablas en OneDrive/SharePoint
- **SQL Server** — bases de datos on-premises o Azure SQL
- **Outlook / Exchange** — emails y calendarios

### Microsoft 365
- **Teams** — enviar mensajes, gestionar canales
- **OneDrive** — gestión de archivos
- **Forms** — procesar respuestas
- **Planner** — tareas de equipo

### Externos (ejemplos)
- Salesforce, Dynamics 365, ServiceNow, SAP, Google Sheets, Dropbox, DocuSign, Twilio

### Conectores personalizados
- Crear desde OpenAPI/Swagger spec
- Conectar a cualquier REST API con autenticación OAuth2, API Key o Basic

## Galería (Gallery) — Patrones comunes

```powerfx
// Items de la galería con filtro
Filter(Productos, Activo = true && TipoID = ddTipo.Selected.ID)

// Selección del item en galería
Gallery1.Selected.Nombre

// Obtener índice del item seleccionado
Gallery1.SelectedIndex

// Colorear ítem seleccionado
If(ThisItem.IsSelected, Color.LightBlue, Color.White)
```

## Formularios (Forms)

```powerfx
// Vincular formulario a galería
Form1.Item = Gallery1.Selected

// Modo del formulario
FormMode.New      // Crear
FormMode.Edit     // Editar
FormMode.View     // Ver

// Verificar validez antes de guardar
If(Form1.Valid, SubmitForm(Form1), Notify("Completar campos requeridos", NotificationType.Error))

// Acción después de submit exitoso
OnSuccess: Navigate(PantallaLista, ScreenTransition.None)
```

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `Delegation warning` | Fórmula no delegable (procesa local hasta 500/2000 registros) | Usar Filter/Search con columnas indexadas; aumentar límite de delegación |
| `Expected Table value` | Función recibe tipo incorrecto | Envolver en `Table()` o revisar que el origen devuelva tabla |
| `Invalid argument` en Patch | Campo no existe o tipo incorrecto | Verificar nombres de columna exactos |
| `Concurrent modification` | Dos usuarios editando el mismo registro | Usar `OnSuccess`/`OnFailure` para manejar conflictos |
| App lenta | Muchas llamadas a datos en el inicio | Cargar datos en `App.OnStart` con `ClearCollect`; usar delegación |

## Despliegue

```
Power Apps Portal → Apps → Publicar → Compartir
  ├── Compartir con usuarios individuales o grupos AD
  ├── Agregar a Teams como pestaña (Teams → + → Power Apps)
  └── Generar link para móvil (Power Apps mobile app)
```

## Documentación oficial

- Referencia Power Fx: https://learn.microsoft.com/power-platform/power-fx/formula-reference-overview
- Canvas apps: https://learn.microsoft.com/power-apps/maker/canvas-apps/
- Conectores: https://learn.microsoft.com/power-apps/maker/canvas-apps/connections-list
- Model-driven apps: https://learn.microsoft.com/power-apps/maker/model-driven-apps/
