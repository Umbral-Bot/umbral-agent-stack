---
name: power-apps
description: >-
  Build and debug Microsoft Power Apps canvas apps and model-driven apps using
  Power Fx formulas, data connectors, and controls to create business applications
  without full-stack coding.
  Use when "create power apps", "canvas app formula", "power fx", "model-driven app",
  "power apps connector", "build app without code", "power apps gallery filter",
  "patch sharepoint from power apps", "power apps form", "navigate between screens".
metadata:
  openclaw:
    emoji: "\U0001F4F1"
    requires:
      env: []
---

# Power Apps Skill

Rick puede asistir en el diseño y depuración de aplicaciones Power Apps (canvas apps y model-driven apps), incluyendo fórmulas Power Fx, conectores de datos y componentes de UI.

Documentación oficial: https://learn.microsoft.com/power-apps/

---

## Tipos de app

| Tipo | Descripción | Cuándo usarlo |
|------|-------------|---------------|
| **Canvas App** | Diseño libre en lienzo, muy flexible | UI personalizada, formularios, apps móviles |
| **Model-Driven App** | Basada en datos de Dataverse, estructura fija | CRM, tracking de casos, procesos complejos |
| **Pages (Portal)** | Sitio web externo conectado a Dataverse | Portales de clientes, formularios públicos |

---

## Power Fx — Fórmulas clave

### Navegación y pantallas

```powerfx
Navigate(ScreenName, ScreenTransition.Fade)
Navigate(DetailScreen, ScreenTransition.Cover, {recordParam: ThisItem})
Back()
```

### Variables

```powerfx
Set(varName, "valor")                    // variable global
UpdateContext({localVar: 42})            // variable local a la pantalla
Set(varCurrentUser, User().Email)
Set(varIsAdmin, "admin@contoso.com" in User().Email)
```

### Colecciones

```powerfx
ClearCollect(colItems, DataSource)                      // reemplaza colección
Collect(colItems, {Title: "Nuevo", Status: "Open"})     // agrega item
Remove(colItems, thisItem)                              // elimina item
Clear(colItems)                                         // vacía colección
SortByColumns(colItems, "Title", SortOrder.Ascending)
```

### Filtros y búsqueda

```powerfx
Filter(SharePointList, Status = "Active")
Filter(SharePointList, StartsWith(Title, TextInput1.Text))
Search(SharePointList, SearchBox.Text, "Title", "Description")
LookUp(Products, ID = varSelectedID)
LookUp(Products, ID = varSelectedID, Title)            // solo el campo Title
```

### Formularios y Patch

```powerfx
// Guardar registro desde formulario
SubmitForm(Form1)

// Patch directo a origen de datos
Patch(SharePointList, Defaults(SharePointList), {
  Title: TextTitle.Text,
  Status: DropdownStatus.Selected.Value,
  AssignedTo: {
    '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser",
    Claims: "i:0#.f|membership|" & ComboBoxUser.Selected.Email
  }
})

// Actualizar registro existente
Patch(SharePointList, LookUp(SharePointList, ID = varSelectedID), {
  Status: "Closed"
})

// Patch a Dataverse
Patch(Accounts, Defaults(Accounts), {
  name: TextName.Text,
  telephone1: TextPhone.Text
})
```

### Condicionales y lógica

```powerfx
If(Len(TextInput1.Text) > 0, true, false)
Switch(DropdownStatus.Selected.Value,
  "Active", Color.Green,
  "Pending", Color.Orange,
  Color.Red
)
And(IsBlank(TextEmail.Text), IsBlank(TextPhone.Text))
Or(varIsAdmin, varIsManager)
IsBlank(TextInput1.Text)
IsEmpty(colItems)
Not(varLoading)
```

### Texto y formato

```powerfx
Concatenate("Hola, ", User().FullName)
Text(Now(), "dd/mm/yyyy hh:mm")
Text(varAmount, "[$-es-MX]#,##0.00")
Upper(TextInput1.Text)
Lower(TextInput1.Text)
Trim(TextInput1.Text)
Left(TextTitle.Text, 50)
Len(TextInput1.Text)
```

### Fechas

```powerfx
Now()                                    // fecha y hora actual
Today()                                  // fecha actual (sin hora)
DateAdd(Today(), 30, TimeUnit.Days)
DateDiff(DateColumn, Today(), TimeUnit.Days)
Text(DateValue, "dd/MM/yyyy")
DateTimeValue("2026-03-04T10:00:00Z")
```

### Galería y delegación

```powerfx
// En la propiedad Items de la Galería
Sort(
  Filter(SharePointList, Status = DropdownFilter.Selected.Value),
  Modified, SortOrder.Descending
)

// Delegable en SharePoint: Filter por columna indexada, StartsWith, Search
// NO delegable: Mid(), Len() en filter, colecciones locales
```

---

## Conectores de datos

| Conector | Operaciones soportadas |
|----------|----------------------|
| **SharePoint** | ClearCollect, Patch, Filter, LookUp, Remove |
| **Dataverse** | Full CRUD, relaciones, BPF |
| **SQL Server** | Queries, store procedures |
| **Excel Online (Business)** | Tablas Excel como origen de datos |
| **Office 365 Users** | User().Email, profiles, manager |
| **Outlook** | Enviar email desde canvas app |
| **HTTP / Custom Connector** | Llamar APIs externas |
| **Azure Blob Storage** | Leer/escribir archivos |

### Agregar conector en canvas app
`Datos → Agregar datos → Buscar conector`

---

## Controles más usados

| Control | Propiedad clave | Uso |
|---------|----------------|-----|
| `Gallery` | `Items`, `OnSelect`, `ThisItem` | Lista de registros |
| `Form` | `DataSource`, `Item`, `Mode` | Crear/editar registros |
| `TextInput` | `Text`, `HintText`, `OnChange` | Entrada de texto |
| `Dropdown` | `Items`, `Selected`, `OnChange` | Selección simple |
| `ComboBox` | `Items`, `Selected`, `SelectMultiple` | Selección con búsqueda |
| `DatePicker` | `SelectedDate` | Selección de fecha |
| `Button` | `OnSelect`, `DisplayMode` | Acciones |
| `Label` | `Text`, `Color`, `Size` | Mostrar texto |
| `Image` | `Image`, `Fill` | Mostrar imágenes |
| `Toggle` | `Value`, `OnChange` | Booleano visual |
| `DataTable` | `Items`, columnas | Tabla de datos |

---

## Patrones comunes

### Pantalla de lista → detalle

```powerfx
// Gallery.OnSelect
Set(varSelectedRecord, ThisItem);
Navigate(DetailScreen, ScreenTransition.Cover)

// En DetailScreen, Form.Item
varSelectedRecord
```

### Formulario de nuevo registro

```powerfx
// Botón "Nuevo" en ListScreen
NewForm(Form1);
Navigate(EditScreen, ScreenTransition.Cover)

// Botón "Guardar" en EditScreen
SubmitForm(Form1);
Navigate(ListScreen, ScreenTransition.UnCover)

// Form1.OnSuccess
Notify("Guardado exitosamente", NotificationType.Success);
ClearCollect(colItems, SharePointList)
```

### Búsqueda en tiempo real

```powerfx
// Gallery.Items
Search(
  Filter(SharePointList, Status = DropdownStatus.Selected.Value),
  SearchBox.Text,
  "Title"
)
```

### Carga con spinner

```powerfx
// Botón Guardar.OnSelect
Set(varLoading, true);
Patch(SharePointList, Defaults(SharePointList), {Title: TextInput1.Text});
Set(varLoading, false);
Notify("Guardado", NotificationType.Success)

// Spinner.Visible
varLoading
```

---

## Model-Driven Apps

- Basadas en **Dataverse** (reemplaza CDS).
- Se configuran con **vistas**, **formularios**, **dashboards** y **gráficos**.
- Soportan **Business Rules** (validaciones sin código) y **Business Process Flows**.
- Se extienden con **Power Fx Commands** y **Custom Pages** (canvas embebida).

```
Tabla Dataverse → Formulario (campos) → Vista (listado) → App Model-Driven
```

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `Delegation warning` | Filtro/orden no delegable al origen | Usar columnas indexadas; cargar datos en colección local si el dataset es pequeño (<500) |
| `The data returned by the gallery is not valid` | Items no es tabla/colección | Verificar que el origen devuelva una tabla; usar `Table()` si hace falta |
| `Form submission failed` | Campo obligatorio vacío o validación falló | Revisar `Form.Error` y `Form.ErrorKind` |
| `This function is not supported` | Función usada en contexto incorrecto | `Filter` con funciones no delegables → colección local |
| `Invalid argument type` | Tipo de dato incorrecto en fórmula | Usar `Text()`, `Value()`, `DateValue()` para conversiones |
| `Record not found` | LookUp retorna Blank | Verificar con `IsBlank(LookUp(...))` antes de usar |
| Límite 2000 registros | SharePoint no devuelve más de 2000 sin delegación | Indexar columna de filtro o usar Dataverse |

---

## Buenas prácticas

- **Nombre descriptivo** en todos los controles: `GalleryOrders`, `FormEditItem`, `BtnSave`.
- **Evitar hard-coding**: usar variables globales o parámetros de URL para valores configurables.
- **Delegación**: siempre usar filtros delegables (columnas indexadas en SharePoint, filtros nativo en Dataverse).
- **Colecciones locales**: para datos pequeños o lookup frecuentes, cargar en `OnStart` con `ClearCollect`.
- **Componentes reutilizables**: crear componentes de biblioteca para headers, footers y tarjetas.
- **Accesibilidad**: establecer `AccessibleLabel` en todos los controles interactivos.
- **Separar lógica**: usar `With()` y variables locales en lugar de expresiones anidadas muy largas.

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/power-apps/
- Referencia de fórmulas canvas: https://learn.microsoft.com/power-platform/power-fx/formula-reference-canvas-apps
- Referencia Power Fx model-driven: https://learn.microsoft.com/power-platform/power-fx/formula-reference-model-driven-apps
- Conectores canvas: https://learn.microsoft.com/power-apps/maker/canvas-apps/connections-list
- Delegación: https://learn.microsoft.com/power-apps/maker/canvas-apps/delegation-overview
