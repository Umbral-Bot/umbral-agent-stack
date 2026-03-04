---
name: diagrams-python
description: >-
  Generar diagramas de arquitectura como codigo Python con la libreria Diagrams
  (mingrammer). Crea PNG/SVG/PDF de flujos BIM, workflows de proyectos,
  arquitecturas de sistemas y pipelines de datos directamente desde Python.
  Use when "diagrama arquitectura", "diagrama flujo BIM", "workflow proyecto",
  "diagram as code", "documentar sistema", "generar diagrama PNG".
metadata:
  openclaw:
    emoji: "\U0001F5FA"
    requires:
      env: []
---

# Diagrams — Diagramas de Arquitectura como Codigo

Diagrams (mingrammer) convierte codigo Python en diagramas PNG/SVG/PDF. Permite versionar y documentar arquitecturas de sistemas, flujos BIM y pipelines de datos igual que si fueran codigo fuente.

**Docs oficiales:** https://diagrams.mingrammer.com/

## Instalacion

```bash
pip install diagrams
# Requiere Graphviz instalado en el sistema
# macOS: brew install graphviz
# Ubuntu: sudo apt install graphviz
# Windows: descargar desde graphviz.org y agregar al PATH
```

## Conceptos clave

- **`Diagram`** — contexto principal, genera el archivo de salida
- **Nodos** — representan servicios/componentes (AWS, Azure, GCP, On-Premise, etc.)
- **Edges** — conexiones entre nodos con `>>`, `<<`, `-`
- **`Cluster`** — agrupa nodos relacionados en un bloque visual

---

## Casos de uso

### 1. Diagrama de flujo BIM — pipeline de entrega de modelos

Documenta el flujo completo desde modelado hasta entrega al cliente:

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User, Users
from diagrams.onprem.compute import Server
from diagrams.saas.collaboration import Slack
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL

with Diagram(
    "Pipeline BIM — Entrega de Modelos",
    filename="pipeline_bim",
    outformat="png",
    direction="LR"
):
    arquitecto = User("Arquitecto\n(Revit)")
    coordinador = User("Coordinador\nBIM")

    with Cluster("Control de Calidad"):
        clash = Server("Navisworks\nClash Detection")
        revision = User("Revisor BIM")

    with Cluster("Entrega"):
        acc = Storage("Autodesk\nConstruction Cloud")
        cliente = Users("Cliente / DO")

    arquitecto >> Edge(label="modelo .rvt") >> coordinador
    coordinador >> clash
    clash >> revision
    revision >> Edge(label="aprobado") >> acc
    acc >> cliente
```

### 2. Arquitectura del sistema Umbral Agent Stack (para propuestas)

Genera un diagrama tecnico para incluir en propuestas de consultoria IA:

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.queue import Redis
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.saas.chat import Slack
from diagrams.programming.framework import FastAPI

with Diagram(
    "Sistema Rick — Arquitectura Multi-Agente",
    filename="arquitectura_rick",
    outformat=["png", "svg"],
    direction="TB"
):
    david = User("David\n(Notion)")

    with Cluster("Control Plane (VPS)"):
        dispatcher = Server("Dispatcher")
        redis_q = Redis("Redis Queue")
        worker_vps = FastAPI("Worker\nVPS :8088")

    with Cluster("Execution Plane (VM)"):
        worker_vm = FastAPI("Worker\nVM :8088")
        revit = Server("Revit / Dynamo")

    david >> dispatcher
    dispatcher >> redis_q
    redis_q >> worker_vps
    redis_q >> worker_vm
    worker_vm >> revit
```

### 3. Workflow automatizacion Power Platform — para propuesta de cliente

Diagrama de arquitectura de automatizacion para presentar a cliente:

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.azure.integration import LogicApps
from diagrams.azure.storage import BlobStorage
from diagrams.azure.analytics import AnalysisServices
from diagrams.onprem.client import Users
from diagrams.saas.filesharing import Dropbox
from diagrams.generic.database import SQL

with Diagram(
    "Automatizacion de Reportes BIM\nPower Platform + SharePoint",
    filename="automatizacion_reportes_bim",
    outformat="png",
    direction="LR"
):
    campo = Users("Equipo\nde Obra")
    sharepoint = SQL("SharePoint\nFormularios")
    automate = LogicApps("Power\nAutomate")
    pbi = AnalysisServices("Power BI\nDashboard")
    blob = BlobStorage("Azure Blob\nPlanos PDF")
    gerencia = Users("Gerencia")

    campo >> Edge(label="formulario") >> sharepoint
    sharepoint >> automate
    automate >> pbi
    automate >> blob
    pbi >> gerencia
    blob >> gerencia
```

## Formatos de salida soportados

| Formato | Uso recomendado |
|---------|----------------|
| `"png"` | Presentaciones, propuestas en Word/PowerPoint |
| `"svg"` | Documentacion web, escala sin perder calidad |
| `"pdf"` | Documentos tecnicos, informes de consultoria |
| `["png", "svg"]` | Generar ambos en un solo llamado |

## Nodos mas utiles para contexto AEC/BIM

```python
# Computacion y servidores
from diagrams.onprem.compute import Server
from diagrams.onprem.client import User, Users

# Cloud (Azure — mas comun en AEC)
from diagrams.azure.storage import BlobStorage, DataLakeStorage
from diagrams.azure.analytics import AnalysisServices  # Power BI
from diagrams.azure.integration import LogicApps       # Power Automate

# Bases de datos y almacenamiento
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL

# Colas y mensajeria
from diagrams.onprem.queue import Redis
```

## Notas

- El nombre del archivo de salida se define en `filename` (sin extension)
- Instalar Graphviz es obligatorio; sin el el diagrama no se genera
- El atributo `direction` acepta: `"TB"` (top-bottom), `"LR"` (left-right), `"BT"`, `"RL"`
- Los diagramas se pueden versionar en Git junto con el codigo del proyecto
