---
name: speckle-dalux-powerbi
description: >-
  Gestionar modelos BIM en Speckle (viewer 3D, streams, commits), revisar
  incidencias en Dalux Field, y conectar datos BIM a Power BI. Usa cuando
  el usuario diga "Speckle", "Dalux", "incidencias campo", "BIM viewer",
  "Power BI BIM", "stream BIM", "modelo en la nube".
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      env:
        - SPECKLE_TOKEN
---

# Speckle + Dalux + Power BI — Integración BIM en la nube

Rick usa este skill para gestionar modelos BIM en Speckle, revisar incidencias de campo en Dalux Field, y conectar datos BIM a dashboards de Power BI.

## Speckle — Plataforma de datos BIM

### Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Workspace** | Espacio de trabajo donde se organizan proyectos y equipos |
| **Project** | Contenedor de modelos dentro de un workspace |
| **Model** | Conjunto de datos (geometría y propiedades) de una disciplina |
| **Version** | Punto en el tiempo de un modelo. Cada envío crea nueva versión |
| **Federation** | Combinar varios modelos en una vista unificada |
| **Connector** | Plugin para Revit, Rhino, Grasshopper, AutoCAD, Tekla, etc. |

### API REST — Autenticación y operaciones

```python
import requests

SPECKLE_SERVER = "https://app.speckle.systems"
TOKEN = os.environ["SPECKLE_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
```

#### Listar streams (proyectos)

```python
query = """
query {
  streams(limit: 10) {
    items {
      id
      name
      updatedAt
      branches {
        items {
          id
          name
          commits(limit: 1) {
            items {
              id
              message
              createdAt
              authorName
            }
          }
        }
      }
    }
  }
}
"""

resp = requests.post(
    f"{SPECKLE_SERVER}/graphql",
    json={"query": query},
    headers=HEADERS
)
streams = resp.json()["data"]["streams"]["items"]
for s in streams:
    print(f"Stream: {s['name']} ({s['id']})")
```

#### Obtener objetos de un commit

```python
def get_commit_objects(stream_id: str, commit_id: str):
    query = """
    query($streamId: String!, $commitId: String!) {
      stream(id: $streamId) {
        commit(id: $commitId) {
          referencedObject
          message
          authorName
          createdAt
        }
      }
    }
    """
    resp = requests.post(
        f"{SPECKLE_SERVER}/graphql",
        json={
            "query": query,
            "variables": {"streamId": stream_id, "commitId": commit_id}
        },
        headers=HEADERS
    )
    return resp.json()["data"]["stream"]["commit"]
```

#### Crear un commit

```python
def create_commit(stream_id: str, branch_name: str, object_id: str, message: str):
    mutation = """
    mutation($commit: CommitCreateInput!) {
      commitCreate(commit: $commit)
    }
    """
    resp = requests.post(
        f"{SPECKLE_SERVER}/graphql",
        json={
            "query": mutation,
            "variables": {
                "commit": {
                    "streamId": stream_id,
                    "branchName": branch_name,
                    "objectId": object_id,
                    "message": message
                }
            }
        },
        headers=HEADERS
    )
    return resp.json()["data"]["commitCreate"]
```

### Speckle Python SDK — specklepy

```bash
pip install specklepy
```

#### Enviar objetos

```python
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from specklepy.objects import Base
from specklepy.transports.server import ServerTransport
from specklepy.api import operations

client = SpeckleClient(host="https://app.speckle.systems")
account = get_default_account()
client.authenticate_with_token(account.token)

# Crear un objeto Base
wall = Base()
wall.name = "Muro Exterior"
wall.height = 3.0
wall.width = 0.20
wall.material = "Hormigón armado"
wall.level = "Nivel 1"

# Enviar al servidor
transport = ServerTransport(stream_id="abc123", client=client)
obj_id = operations.send(base=wall, transports=[transport])
print(f"Objeto enviado: {obj_id}")

# Crear commit
commit_id = client.commit.create(
    stream_id="abc123",
    object_id=obj_id,
    branch_name="main",
    message="Muro exterior nivel 1"
)
```

#### Recibir objetos

```python
transport = ServerTransport(stream_id="abc123", client=client)

# Obtener último commit
stream = client.stream.get(id="abc123")
latest_commit = stream.branches.items[0].commits.items[0]

# Recibir objeto
received = operations.receive(obj_id=latest_commit.referencedObject, remote_transport=transport)
print(f"Nombre: {received.name}")
print(f"Elementos: {len(received.elements) if hasattr(received, 'elements') else 0}")
```

#### Base objects — Estructura personalizada

```python
from specklepy.objects import Base

class BIMWall(Base, speckle_type="Objects.BIM.Wall"):
    name: str = ""
    height: float = 0.0
    width: float = 0.0
    material: str = ""
    level: str = ""
    is_external: bool = False
    fire_rating: str = ""

wall = BIMWall(
    name="M-EXT-01",
    height=3.0,
    width=0.25,
    material="Hormigón H30",
    level="Nivel 2",
    is_external=True,
    fire_rating="F120"
)
```

### Speckle Manager y conectores

| Conector | Funcionalidad |
|----------|---------------|
| **Revit** | Enviar/recibir categorías, vistas, familias |
| **Rhino** | Geometría NURBS, meshes, layers |
| **Grasshopper** | Nodos Send/Receive en definiciones |
| **AutoCAD** | Bloques, layers, anotaciones |
| **Tekla** | Elementos estructurales, armaduras |
| **Navisworks** | Modelos federados, clash data |
| **Archicad** | Elementos 3D, zonas, propiedades |
| **Blender** | Meshes, materiales |
| **Power BI** | Datos tabulares + visual 3D |

Instalación: Speckle Manager detecta las aplicaciones instaladas y gestiona los conectores automáticamente.

### Viewer embebido

```html
<!-- Embeber viewer Speckle en una página web -->
<iframe
  src="https://app.speckle.systems/projects/PROJECT_ID/models/MODEL_ID"
  width="100%"
  height="600px"
  frameborder="0">
</iframe>
```

El viewer soporta: órbita, pan, zoom, cortes en X/Y/Z, filtros por categoría, selección de elementos, propiedades al clic.

## Dalux Field — Gestión BIM en campo

### Tipos de incidencias (Punch Items)

| Tipo | Descripción | Flujo |
|------|-------------|-------|
| **Defecto** | No conformidad detectada en campo | Crear → Asignar → Corregir → Verificar → Cerrar |
| **RFI** | Solicitud de información al diseñador | Crear → Asignar → Responder → Verificar → Cerrar |
| **Observación** | Registro de situación sin acción requerida | Crear → Registrar |
| **Seguridad** | Incidencia HSE | Crear → Asignar → Corregir → Verificar → Cerrar |
| **Formulario QC** | Check de calidad vinculado a plan | Programar → Ejecutar → Aprobar/Rechazar |

### Estados de tarea

| Estado | Color | Significado |
|--------|-------|-------------|
| Nuevo | Gris | Asignada, no vista/iniciada |
| En proceso | Amarillo | En trabajo por responsable |
| Reportado listo | Verde con tick | Esperando aprobación |
| Aprobado/cerrado | Verde | Trabajo aceptado |
| Rechazado | Rojo | Trabajo no aceptado, requiere retrabajo |
| Archivado | Negro | Tarea eliminada o no válida |

### Flujo de QA/QC en campo

```
1. Oficina técnica carga modelos BIM y planos a Dalux
2. Inspector de campo abre Dalux en tablet/móvil
3. Navega al plano o modelo 3D del área a inspeccionar
4. Crea incidencia (defecto/observación) con:
   - Foto georeferenciada
   - Ubicación en plano 2D o modelo 3D
   - Categoría y prioridad
   - Responsable asignado
5. Subcontratista recibe notificación y corrige
6. Inspector verifica corrección in situ
7. Aprueba o rechaza con nueva foto de evidencia
```

### Paquetes y organización

| Configuración | Recomendación |
|---------------|---------------|
| Paquetes | Un paquete por disciplina o contrato |
| Grupos de usuarios | Crear por rol (Dirección, Supervisión, Subcontratos) |
| Perfiles | Asignar permisos por grupo, no por usuario individual |
| Plantillas | Estandarizar formularios QC para reutilizar en proyectos |
| Planos | Organizar por nivel y zona, mantener actualizados |

### BIM Viewer en Dalux

Capacidades del viewer integrado:
- Navegación: órbita, pan, zoom, primera persona (WASD)
- Cortes en planos X/Y/Z
- Filtros por disciplina (Arquitectura, Estructura, MEP)
- Propiedades BIM al hacer clic en un elemento
- Split view 2D+3D sincronizado
- Vincular incidencias a elementos del modelo 3D

### Exportar datos de Dalux

```
Dalux > Vista Lista > Filtrar por estado/responsable/fecha
  > Seleccionar registros > Exportar a Excel o PDF
```

Los exports de Excel son la base para alimentar Power BI con datos de campo.

## Power BI + Speckle — Dashboards BIM

### Conector oficial Speckle

**Instalación:**
1. Descargar conector desde https://app.speckle.systems/connectors
2. En Power BI: Get Data > buscar "Speckle" > Connect
3. Habilitar extensiones: File > Options > Security > Data Extensions > Allow any extension
4. Pegar URL del modelo Speckle
5. Importar visual 3D: Visualizations > ... > Import from file > `Speckle 3D Visual.pbiviz`

**Requisito:** Speckle Desktop Service debe estar en ejecución.

### Configuración del visual 3D

| Campo | Requerido | Uso |
|-------|-----------|-----|
| Model Info | Sí | Visualización del modelo 3D |
| Object IDs | Sí | Interactividad (selección, drill-down) |
| Tooltip | No | Información al pasar el cursor |
| Color by | No | Colorear elementos por categoría/propiedad |

### Helpers Power Query

| Función | Uso |
|---------|-----|
| `Speckle.Projects.Issues(url, getReplies)` | Issues del proyecto/modelo/versión |
| `Speckle.Objects.Properties(record, filterKeys)` | Propiedades de un objeto |
| `Speckle.Objects.CompositeStructure(record, outputAsList)` | Capas de muros/suelos |
| `Speckle.Objects.MaterialQuantities(record, outputAsList)` | Cantidades materiales por objeto |
| `Speckle.Models.MaterialQuantities(table, addPrefix)` | Cantidades a nivel de modelo |
| `Speckle.Models.Federate(tables, excludeData)` | Federar modelos para visual 3D |
| `Speckle.Utils.ExpandRecord(table, columnName, FieldNames, UseCombinedNames)` | Expandir columnas tipo record |

### Crear reportes de avance con Power BI

```
1. Conectar modelo Speckle → tablas de elementos
2. Crear medidas DAX:
   - Total_Elementos = COUNTROWS(Elements)
   - Completados = CALCULATE(COUNTROWS(Elements), Elements[Status]="Complete")
   - Avance_% = DIVIDE([Completados], [Total_Elementos])
3. Crear visualizaciones:
   - KPI card con porcentaje de avance
   - Gráfico de barras por nivel/disciplina
   - Visual 3D Speckle coloreado por estado
   - Tabla detallada con drill-through
4. Publicar en Power BI Service
5. Configurar Data Gateway para refresco automático
```

### Data Gateway para refresco programado

Para Power BI Service: configurar Data Gateway (Personal o Standard). Añadir conector Speckle (.pqx) a carpeta Custom Connectors del gateway. Configurar OAuth2 en semantic model.

### Integración Dalux → Power BI

Power BI no tiene conector nativo a Dalux. Opciones:

| Método | Complejidad | Automatización |
|--------|-------------|----------------|
| Export Excel manual | Baja | No |
| Power Automate + SharePoint | Media | Sí |
| API Dalux (si disponible) + Power Query | Alta | Sí |
| Base de datos intermedia | Alta | Sí |

Flujo recomendado:
```
Dalux > Exportar Excel > SharePoint/OneDrive
  > Power BI Data Source > Refresco programado
```

## Integración con `research.web` para documentación

```python
# Buscar documentación actualizada de Speckle
result = await client.execute_task("research.web", {
    "query": "Speckle API GraphQL mutations commits 2026",
    "depth": "standard"
})

# Buscar cambios en la API de Dalux
result = await client.execute_task("research.web", {
    "query": "Dalux Field API integration REST endpoints",
    "depth": "quick"
})
```

## Flujos de integración

### Flujo 1: Modelo BIM → Speckle → Power BI

```
Revit/Rhino/Tekla → Conector Speckle → Servidor Speckle
    → Conector Power BI → Tablas + Visual 3D
    → Dashboard ejecutivo con drill-down
```

### Flujo 2: Dalux → Excel → Power BI (datos de campo)

```
Inspector en campo → Dalux (crear incidencia con foto)
    → Export Excel → SharePoint
    → Power BI (cargar, modelar, visualizar)
    → Dashboard seguimiento defectos/RFIs
```

### Flujo 3: Speckle + Dalux + Power BI (visión unificada)

```
Speckle: modelos BIM centralizados (diseño)
Dalux: tareas vinculadas a ubicaciones (campo)
Power BI: cargar ambos, crear modelo relacional por nivel/zona
    → Visual 3D coloreado por estado de tarea
    → KPIs: avance diseño vs. construcción
```

### Speckle Intelligence vs Power BI

| Criterio | Speckle Intelligence | Power BI |
|----------|---------------------|----------|
| Fuente datos | Solo modelos Speckle | Speckle + Dalux + otras |
| Integración Dalux | No nativa | Manual o API |
| Visual 3D | Integrado | Visual Speckle 3D |
| Colaboración | Workspace Speckle | Power BI Service |
| Complejidad | Baja (widgets listos) | Media-Alta (DAX, modelado) |
| Personalización | Limitada | Total |

Speckle Intelligence para análisis rápido de modelos. Power BI cuando se necesita combinar con Dalux u otras fuentes de datos.

## Troubleshooting frecuente

| Problema | Solución |
|----------|---------|
| No carga modelo en Power BI | Verificar Speckle Desktop Service en ejecución |
| Error autenticación Power BI | File > Options > Security > desmarcar "Use my default web browser" |
| Token caducado | Clear Permissions en Data source settings. Eliminar PowerBITokenCache.db |
| Sin permisos Speckle | Verificar acceso al proyecto en Speckle. Re-autenticar |
| Dalux no exporta | Verificar permisos del perfil de usuario en el paquete |
| Visual 3D no aparece | Importar .pbiviz manualmente desde Visualizations |

## Ejemplos de uso con Rick

- **Rick: "Conectá el modelo de Revit a Speckle y mostrame los datos en Power BI"** → Conector Speckle Revit + Power BI con visual 3D.
- **Rick: "Cuántas incidencias abiertas hay en Dalux?"** → Export Excel + análisis rápido o `research.web` para API.
- **Rick: "Creá un dashboard que combine el modelo BIM con las tareas de campo"** → Speckle + Dalux Excel + Power BI relacional.
- **Rick: "Enviá este objeto Base a Speckle desde Python"** → specklepy `operations.send()` + `commit.create()`.
- **Rick: "Listame los streams de Speckle via API"** → GraphQL query `streams(limit: N)`.

## Recursos oficiales

- Speckle docs: https://docs.speckle.systems/
- Speckle Python SDK: https://speckle.guide/dev/python.html
- Speckle GraphQL API: https://docs.speckle.systems/dev/server-graphql-api
- Speckle Power BI: https://docs.speckle.systems/connectors/power-bi/power-bi
- Dalux Field: https://support.dalux.com/hc/es/categories/4405292014738-Field
- Dalux Academy: https://academy.dalux.com/
- Power BI Desktop: https://powerbi.microsoft.com/desktop/

## Notas

- `SPECKLE_TOKEN` se obtiene en https://app.speckle.systems/ > Profile > Access Tokens. Scopes: `streams:read`, `streams:write`, `profile:read`.
- Speckle usa GraphQL como API principal. Las mutaciones requieren autenticación con token.
- Los conectores de Speckle son gratuitos y open source. Speckle Manager gestiona la instalación.
- Dalux no ofrece API pública documentada; la integración con Power BI se hace via exports Excel.
- Para refrescos automáticos en Power BI Service, configurar Data Gateway con el conector Speckle .pqx.
- El visual 3D de Speckle para Power BI es un custom visual (.pbiviz) que se importa manualmente.
