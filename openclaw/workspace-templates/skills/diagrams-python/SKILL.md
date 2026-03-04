---
name: diagrams-python
description: >-
  Generar diagramas de arquitectura de sistemas como codigo Python usando
  la libreria Diagrams. Soporta iconos de AWS, Azure, GCP, Kubernetes,
  herramientas on-premise y nodos personalizados. Exporta PNG/SVG.
  Use when "diagrama arquitectura", "diagrama flujo BIM", "diagrama sistema",
  "documentar workflow", "arquitectura cloud", "generar diagrama codigo",
  "diagrama como codigo", "infrastructure diagram".
metadata:
  openclaw:
    emoji: "\U0001F5FA"
    requires:
      env: []
---

# Diagrams — Diagramas de Arquitectura como Codigo

La libreria `diagrams` de Python permite crear diagramas de arquitectura de sistemas directamente desde codigo. Usa Graphviz para renderizar y soporta mas de 200 iconos de servicios cloud, herramientas DevOps, bases de datos y nodos personalizados.

**Instalacion:**
```bash
pip install diagrams
# Requiere Graphviz instalado en el sistema:
# macOS: brew install graphviz
# Ubuntu: sudo apt install graphviz
# Windows: descargar desde https://graphviz.org/download/
```

**Docs oficiales:** https://diagrams.mingrammer.com/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Diagrama de flujo BIM: datos desde Revit hasta Power BI

Documenta el flujo de datos de un proyecto BIM desde el modelo hasta el dashboard de reportes, con las herramientas que David usa en su stack.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.azure.general import Managementgroups
from diagrams.onprem.database import Mysql
from diagrams.azure.analytics import AnalysisServices
from diagrams.onprem.workflow import Airflow
from diagrams.generic.storage import Storage

with Diagram(
    "Flujo BIM: Revit → Power BI",
    filename="flujo_bim_powerbi",
    show=False,
    direction="LR",
):
    arquitecto = User("Arquitecto / BIM Coordinator")
    modelo = Storage("Modelo Revit (.rvt)")
    acc = Managementgroups("Autodesk Construction Cloud (ACC)")
    extractor = Airflow("Power Automate\n(extraccion datos)")
    sharepoint = Managementgroups("SharePoint / Excel")
    powerbi = AnalysisServices("Power BI Dashboard")
    cliente = User("Cliente / Gerencia")

    arquitecto >> Edge(label="publica modelo") >> acc
    acc >> Edge(label="ACC Data Connector") >> extractor
    extractor >> Edge(label="exporta tablas") >> sharepoint
    sharepoint >> Edge(label="fuente de datos") >> powerbi
    powerbi >> Edge(label="reportes en tiempo real") >> cliente
```

### 2. Diagrama de arquitectura del stack Umbral Agent (Rick)

Visualiza la arquitectura del sistema de automatizacion con sus componentes: Dispatcher, Worker, Redis y canales de entrada.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.queue import Redis
from diagrams.onprem.client import User
from diagrams.programming.framework import FastAPI
from diagrams.onprem.network import Nginx
from diagrams.saas.chat import Slack

with Diagram(
    "Umbral Agent Stack — Arquitectura",
    filename="umbral_architecture",
    show=False,
    direction="TB",
):
    david = User("David (usuario)")
    notion = Slack("Notion\n(Control Room)")

    with Cluster("VPS Control Plane"):
        dispatcher = FastAPI("Dispatcher")
        redis = Redis("Redis Queue")

    with Cluster("VM Execution Plane"):
        worker = FastAPI("Worker API\n:8088")

    david >> notion >> dispatcher
    dispatcher >> redis
    redis >> dispatcher
    dispatcher >> Edge(label="HTTP task") >> worker
    worker >> Edge(label="resultado") >> notion
```

### 3. Diagrama de proceso de consultoria BIM para propuestas

Genera un diagrama de fases de proyecto para incluir en propuestas tecnicas a clientes.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.generic.blank import Blank
from diagrams.onprem.client import User, Users

with Diagram(
    "Proceso de Consultoria BIM",
    filename="proceso_consultoria_bim",
    show=False,
    direction="LR",
    graph_attr={"rankdir": "LR", "splines": "ortho"},
):
    cliente = User("Cliente")

    with Cluster("Fase 1: Diagnostico (2 sem)"):
        diag = Blank("Levantamiento\nde procesos")
        gap = Blank("Analisis\nde brechas")
        diag >> gap

    with Cluster("Fase 2: Diseno (2 sem)"):
        plan = Blank("Plan BIM\nBEP")
        estandar = Blank("Estandares\ny templates")
        plan >> estandar

    with Cluster("Fase 3: Implementacion (4-8 sem)"):
        piloto = Blank("Proyecto\npiloto")
        capacit = Blank("Capacitacion\nequipo")
        piloto >> capacit

    with Cluster("Fase 4: Mejora Continua"):
        auditoria = Blank("Auditoria\nBIM")
        soporte = Users("Soporte\ncontinuo")
        auditoria >> soporte

    cliente >> diag
    gap >> plan
    estandar >> piloto
    capacit >> auditoria
    soporte >> cliente
```

### 4. Diagrama de ecosistema Power Platform + BIM

Documenta la integracion de herramientas Microsoft con el stack BIM de un cliente.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.azure.general import Managementgroups
from diagrams.azure.integration import LogicApps
from diagrams.azure.analytics import AnalysisServices
from diagrams.azure.devops import Devops
from diagrams.onprem.client import Users

with Diagram(
    "Ecosistema Power Platform + BIM",
    filename="power_platform_bim",
    show=False,
    direction="TB",
):
    equipo = Users("Equipo de Proyecto")

    with Cluster("Microsoft 365"):
        sharepoint = Managementgroups("SharePoint\nDocumentos")
        teams = Managementgroups("Teams\nColaboracion")

    with Cluster("Power Platform"):
        automate = LogicApps("Power Automate\nFlujos")
        apps = Devops("Power Apps\nInterfaces")
        bi = AnalysisServices("Power BI\nDashboards")

    with Cluster("BIM Tools"):
        acc = Managementgroups("ACC / BIM360")
        revit = Managementgroups("Revit / Navisworks")

    equipo >> teams
    equipo >> apps
    teams >> sharepoint
    apps >> automate
    automate >> Edge(label="sync datos") >> acc
    acc >> Edge(label="extrae modelos") >> revit
    automate >> Edge(label="reportes") >> sharepoint
    sharepoint >> bi
    bi >> equipo
```

---

## Notas

- El nombre del archivo de salida (parametro `filename`) no debe tener extension; Diagrams agrega `.png` automaticamente.
- Para obtener SVG: `with Diagram(..., outformat="svg")`.
- Ver todos los iconos disponibles en: https://diagrams.mingrammer.com/docs/nodes/onprem
- Para nodos sin icono especifico, usar `from diagrams.generic.blank import Blank` o `from diagrams.custom import Custom` con imagen propia.
- Graphviz debe estar en el PATH del sistema; verificar con `dot -V` en terminal.
