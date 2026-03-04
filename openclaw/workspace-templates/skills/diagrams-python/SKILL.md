---
name: diagrams-python
description: >-
  Genera diagramas de arquitectura como código con la librería Diagrams
  (mingrammer). Crea diagramas de flujos BIM, arquitecturas de sistemas,
  workflows de proyectos y pipelines de datos en PNG/SVG desde Python.
  Usar cuando: "diagrama de arquitectura", "diagrama de flujo BIM",
  "documentar pipeline", "diagrama de sistema", "esquema de infraestructura".
metadata:
  openclaw:
    emoji: "\U0001F5FA\uFE0F"
    requires:
      env: []
---

# Diagrams — Arquitectura como Código

La librería `diagrams` (mingrammer) permite crear diagramas de arquitectura
de sistemas y flujos de trabajo usando Python puro. El resultado es un PNG/SVG
reproducible y versionable en Git.

## Instalación

```bash
# Requiere Graphviz instalado en el sistema
brew install graphviz          # macOS
sudo apt install graphviz      # Ubuntu/Debian

pip install diagrams
```

## Casos de uso

### 1. Diagrama de workflow BIM en la nube

Documenta el flujo completo de un proyecto BIM desde modelo hasta entregable.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import User
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage

with Diagram("BIM Workflow — Proyecto Torre", show=False, filename="bim_workflow"):
    arquitecto = User("Arquitecto")
    modelo = Storage("Modelo Revit\n(.rvt)")
    nube = BlobStorage("Azure Blob\nStorage")
    servidor_ifc = Rack("Servidor IFC\n(IfcOpenShell)")
    entregable = Storage("Entregables\n(IFC, PDF, DWG)")

    arquitecto >> Edge(label="Publica modelo") >> modelo
    modelo >> Edge(label="Sync") >> nube
    nube >> Edge(label="Convierte") >> servidor_ifc
    servidor_ifc >> Edge(label="Genera") >> entregable
```

### 2. Pipeline de automatización con IA

Visualiza un pipeline de procesamiento de datos BIM con inteligencia artificial.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.generic.compute import Rack
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage

with Diagram(
    "Pipeline IA — Análisis de Costos BIM",
    show=False,
    filename="pipeline_ia_costos",
    direction="LR",
):
    with Cluster("Input"):
        modelo_bim = Storage("Modelo BIM\nRevit/IFC")
        precios = Storage("Base de\nPrecios")

    procesamiento = Python("IfcOpenShell\n+ Pandas")
    ia = Rack("LLM\n(Gemini 2.5)")

    with Cluster("Output"):
        reporte = Storage("Reporte PDF")
        notion = Storage("Notion\nDashboard")

    modelo_bim >> procesamiento
    precios >> procesamiento
    procesamiento >> Edge(label="Extrae cantidades") >> ia
    ia >> reporte
    ia >> notion
```

### 3. Diagrama de infraestructura de consultoría

Muestra la arquitectura técnica del stack de herramientas de una consultoría.

```python
from diagrams import Diagram, Cluster
from diagrams.saas.collaboration import Notion
from diagrams.azure.compute import VM
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import FastAPI

with Diagram(
    "Stack Consultoría BIM/IA",
    show=False,
    filename="stack_consultoria",
    direction="TB",
):
    notion = Notion("Notion\n(Control Room)")

    with Cluster("VPS Control Plane"):
        dispatcher = FastAPI("Dispatcher")
        redis = Redis("Redis Queue")

    with Cluster("VM Execution Plane"):
        worker = FastAPI("Worker API")
        revit = VM("Revit + PAD")

    notion >> dispatcher >> redis >> worker >> revit
```

## Notas

- Exporta a PNG, SVG, PDF y DOT (para Graphviz manual).
- `show=False` evita abrir automáticamente la imagen (útil en servidores).
- Nodos disponibles: AWS, Azure, GCP, K8s, SaaS, OnPrem, Generic.
- Docs oficiales: https://diagrams.mingrammer.com/
