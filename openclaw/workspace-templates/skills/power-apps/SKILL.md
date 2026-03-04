---
name: power-apps
description: >-
  Asistente para crear y depurar aplicaciones con Microsoft Power Apps: canvas
  apps, model-driven apps, fórmulas Power Fx, conectores y Dataverse.
  Use when "power apps", "canvas app", "model-driven app", "power fx",
  "fórmula power apps", "gallery power apps", "conector power apps",
  "dataverse tabla", "crear app desde cero", "galería filtrada", "formulario app".
metadata:
  openclaw:
    emoji: "\U0001F4F1"
    requires:
      env: []
---

# Power Apps Skill

Rick usa este skill para guiar la creación, depuración y optimización de aplicaciones con Microsoft Power Apps. Cubre canvas apps, model-driven apps, Power Fx, conectores y Dataverse.

Fuente oficial: https://learn.microsoft.com/power-apps/

---

## Tipos de aplicaciones

| Tipo | Descripción | Caso de uso |
|------|-------------|-------------|
| **Canvas App** | Diseño libre pixel-a-pixel; conecta con +900 orígenes de datos | Apps operativas, formularios, dashboards custom |
| **Model-Driven App** | Basada en datos de Dataverse; genera UI automática con tablas/formularios | CRM, gestión de proyectos, procesos estructurados |
| **Pages (Power Pages)** | Portales web externos para usuarios externos | Portales de clientes, registros públicos |

---

## Power Fx — Lenguaje de fórmulas

Power Fx es el lenguaje declarativo de Power Apps, inspirado en Excel. Es case-sensitive para los nombres de variables.

### Fórmulas esenciales

```
// Navegar entre pantallas
Navigate(Pantalla2, ScreenTransition.Fade)
Navigate(Pantalla2, ScreenTransition.None, {param: TextInput1.Text})

// Actualizar variable global
Set(miVariable, "nuevo valor")

// Variable de colección local
UpdateContext({loaderVisible: true})

// Crear colección en memoria
ClearCollect(colProductos, Filter(Productos, Activo = true))

// Limpiar colección
Clear(colProductos)

// Agregar registro
Collect(colProductos, {Nombre: "Item", Precio: 100})

// Guardar en origen de datos
SubmitForm(Form1)

// Crear nuevo registro
NewForm(Form1)

// Editar registro seleccionado
EditForm(Form1)

// Resetear formulario
ResetForm(Form1)
```

### Filtrado y búsqueda

```
// Filtrar tabla
Filter(ListaProductos, Categoria = "Electrónica")
Filter(ListaProductos, Precio > 100 && Activo = true)

// Buscar texto (contiene)
Search(ListaProductos, TextBusqueda.Text, "Nombre", "Descripcion")

// Ordenar
Sort(ListaProductos, Precio, SortOrder.Descending)

// Combinar Sort + Filter
SortByColumns(Filter(ListaProductos, Activo), "Nombre", Ascending)

// Lookup (primer resultado que cumple)
LookUp(Empleados, ID = 42, NombreCompleto)

// Primer / último elemento
First(colProductos)
Last(colProductos)

// Contar elementos
CountRows(Filter(Pedidos, Estado = "Pendiente"))
```

### Manejo de texto

```
Concatenate("Hola, ", User().FullName)
Text(1234.5, "$#,##0.00")           // → $1,234.50
Text(Today(), "dd/mm/yyyy")
Value("42")                          // string → número
DateValue("2026-03-04")
Upper(TextInput1.Text)
Lower(Label1.Text)
Len(TextInput1.Text)
Left("PowerApps", 5)                 // → Power
Right("PowerApps", 4)                // → Apps
Substitute("power_apps", "_", " ")
IsBlank(TextInput1.Text)
IsNumeric(TextInput1.Text)
```

### Condicionales

```
If(condición, resultado_verdadero, resultado_falso)
If(IsBlank(EmailInput.Text), "Requerido", "OK")
Switch(Dropdown1.Selected.Value, "A", "Opción A", "B", "Opción B", "Otro")
Coalesce(variable1, variable2, "default")
```

### Fechas y horas

```
Now()                                // fecha y hora actual
Today()                              // solo fecha
DateAdd(Today(), 30, TimeUnit.Days)
DateDiff(Inicio, Fin, TimeUnit.Days)
Text(Now(), "[$-es-AR]dddd d \de mmmm \de yyyy")
Hour(Now()) & ":" & Minute(Now())
```

---

## Componentes de UI

| Componente | Propiedad clave | Uso típico |
|------------|----------------|------------|
| **TextInput** | `Text`, `Default`, `OnChange` | Campos de entrada |
| **Label** | `Text` | Mostrar texto y cálculos |
| **Button** | `OnSelect` | Acciones (guardar, navegar) |
| **Gallery** | `Items`, `OnSelect`, `Selected` | Listas de registros |
| **Form** | `DataSource`, `Item`, `Mode` | Crear/editar registros |
| **Dropdown** | `Items`, `Selected`, `OnChange` | Selección de opciones |
| **Combo Box** | `Items`, `IsSearchable`, `SelectMultiple` | Búsqueda y selección múltiple |
| **Date Picker** | `SelectedDate`, `DisplayMode` | Selección de fechas |
| **Toggle** | `Value`, `OnCheck`, `OnUncheck` | Activar/desactivar |
| **Image** | `Image` (URL o media) | Imágenes locales o remotas |
| **Timer** | `Duration`, `OnTimerEnd`, `AutoStart` | Polling, animaciones |
| **Data Table** | `Items`, columnas | Vista tabular de datos |

### Gallery — Patrón común

```
// Items del gallery
Filter(SharePointList, Estado = "Activo")

// En label dentro del gallery
ThisItem.Nombre
ThisItem.FechaCreacion

// Al seleccionar un item → navegar con contexto
Navigate(DetalleScreen, None, {registroSeleccionado: ThisItem})

// En pantalla de detalle
Set(miRegistro, registroSeleccionado)
```

---

## Conectores principales

| Conector | Tipo | Descripción |
|----------|------|-------------|
| SharePoint | Standard | Listas y documentos |
| Dataverse | Premium | Base de datos nativa Power Platform |
| Excel Online (Business) | Standard | Tablas en OneDrive/SharePoint |
| SQL Server | Premium | Bases de datos SQL locales o Azure |
| Office 365 Users | Standard | Perfiles y organigramas |
| Office 365 Outlook | Standard | Emails y calendario |
| Approvals | Standard | Flujos de aprobación |
| Azure Blob Storage | Premium | Almacenamiento de archivos |
| Power BI | Premium | Datasets y reports embebidos |
| HTTP con Azure AD | Premium | APIs personalizadas con auth |
| OneDrive for Business | Standard | Archivos en OneDrive |

---

## Dataverse — Conceptos

| Concepto | Descripción |
|----------|-------------|
| **Tabla** | Equivalente a tabla de base de datos (antes: Entity) |
| **Columna** | Campo de la tabla (antes: Field/Attribute) |
| **Relación** | 1:N, N:N, N:1 entre tablas |
| **Vista** | Filtro/orden predefinido de una tabla |
| **Formulario** | UI generada automáticamente para una tabla |
| **Business Rule** | Lógica de negocio declarativa sin código |
| **Elección (Choice)** | Dropdown con valores predefinidos globales |

---

## Fórmulas de contexto del usuario

```
User().FullName          // Nombre completo del usuario logueado
User().Email             // Email
User().Image             // Foto de perfil (URL)
Office365Users.MyProfile()  // Perfil completo (requiere conector)
Office365Users.ManagerV2(User().Email)  // Jefe directo
```

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| `Delegation warning` | Filtro no delegable; procesa solo 500 registros | Usar columnas indexadas; habilitar delegación; considerar Dataverse |
| `The formula contains a syntax error` | Error de escritura en fórmula | Revisar paréntesis, comillas y nombres |
| `This record was changed by another user` | Conflicto de edición concurrente | Usar `Reload()` + `EditForm()` |
| `Connectors not responding` | Timeout o throttle del conector | Verificar credenciales y límites de API |
| `Incompatible types` | Tipo de dato incorrecto (texto vs número) | Usar `Value()`, `Text()`, `DateValue()` para conversiones |
| Gallery no muestra datos | Items mal configurado o delegación | Simplificar fórmula; usar `ClearCollect` para cargar datos primero |

---

## Patrones de desarrollo recomendados

### Variables y estado

- `Set()` → variables globales (toda la app)
- `UpdateContext()` → variables locales (pantalla actual)
- Colecciones → datos tabulares en memoria

### Performance

- Cargar datos al inicio: `OnStart` de App → `ClearCollect(colDatos, Fuente)`
- Limitar columnas: `ShowColumns(tabla, "Col1", "Col2")`
- Usar `Concurrent()` para cargar múltiples fuentes en paralelo

```
Concurrent(
    ClearCollect(colProductos, Productos),
    ClearCollect(colClientes, Clientes),
    ClearCollect(colPedidos, Filter(Pedidos, Año = 2026))
)
```

### Navegación con parámetros

```
// Pantalla origen → botón OnSelect
Navigate(DetalleScreen, None, {itemID: ThisItem.ID, modoEdicion: false})

// Pantalla destino → OnVisible
Set(registroActual, LookUp(Productos, ID = itemID))
```

---

## ALM (Application Lifecycle Management)

- Desarrollar en **entorno de desarrollo** → exportar solución → importar en test/producción
- Usar **variables de entorno** para URLs y configs cambiantes por entorno
- Control de versiones: integrar con Azure DevOps o GitHub vía Power Platform CLI
- Comando básico: `pac solution export --path ./soluciones --name MiSolucion`

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/power-apps/
- Referencia Power Fx: https://learn.microsoft.com/power-platform/power-fx/formula-reference-overview
- Conectores canvas: https://learn.microsoft.com/power-apps/maker/canvas-apps/connections-list
- Dataverse: https://learn.microsoft.com/power-apps/maker/data-platform/
- Comunidad: https://powerusers.microsoft.com/t5/Power-Apps-Community/ct-p/PowerApps1
