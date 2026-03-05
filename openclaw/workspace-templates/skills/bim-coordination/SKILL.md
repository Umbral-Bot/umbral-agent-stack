---
name: bim-coordination
description: >-
  Coordinar modelos multidisciplinarios BIM: clash detection, federación de
  modelos, BCF (BIM Collaboration Format), NWD/NWC en Navisworks. Usa cuando
  el usuario diga "clash detection", "interferencias", "coordinación BIM",
  "BCF", "federar modelos", "NWD", "Navisworks Manage".
metadata:
  openclaw:
    emoji: "⚙️"
    requires:
      env: []
---

# BIM Coordination Skill — Clash Detection, Federación y BCF

Rick usa este skill para coordinar modelos BIM multidisciplinarios: detección de interferencias, federación de modelos, gestión de issues vía BCF y automatización de reportes de coordinación.

## Flujo de coordinación BIM

```
1. Modelado por disciplina (Arquitectura, Estructura, MEP)
2. Exportación a NWC desde Revit/ArchiCAD/Tekla
3. Federación en NWD (Navisworks)
4. Clash Detection (reglas por par de disciplinas)
5. Revisión y clasificación de interferencias
6. Generación de BCF con issues asignados
7. Distribución de BCF a equipos de diseño
8. Corrección en modelos nativos
9. Re-exportación y verificación
10. Reporte de estado para coordinación semanal
```

### Matriz de coordinación típica

| Par de disciplinas | Tipo de clash | Tolerancia |
|--------------------|---------------|-----------|
| Estructura vs. MEP Eléctrico | Hard | 25 mm |
| Estructura vs. MEP Sanitario | Hard | 25 mm |
| Arquitectura vs. Estructura | Hard | 50 mm |
| MEP Eléctrico vs. MEP Sanitario | Hard | 25 mm |
| MEP HVAC vs. Estructura | Hard | 50 mm |
| Arquitectura vs. MEP (general) | Clearance | 100 mm |
| Estructura vs. MEP (ductos) | Clearance | 150 mm |

## BCF — BIM Collaboration Format

### Qué es BCF

BCF (BIM Collaboration Format) es un estándar abierto de buildingSMART para comunicar issues de coordinación entre herramientas BIM. Un archivo BCF contiene:

| Componente | Contenido |
|------------|-----------|
| `markup.bcf` | Título, descripción, autor, fecha, estado, prioridad |
| `viewpoint.bcfv` | Cámara, componentes visibles/seleccionados, secciones |
| `snapshot.png` | Captura de pantalla del issue |
| Metadatos | GUID del issue, GUID de elementos IFC relacionados |

### Versiones BCF

| Versión | Soporte |
|---------|---------|
| BCF 2.1 | Estándar más adoptado. Soporte en Navisworks, Revit, Solibri, BIMcollab |
| BCF 3.0 | Extensiones para documentos, modelos vinculados |
| BCF-API | REST API para gestión en la nube (BIMcollab, Trimble Connect) |

### Workflow BCF entre plataformas

```
Navisworks (Coordinador BIM)
    → Exportar BCF con clashes detectados
    → Subir a BIMcollab / Trimble Connect
    → Arquitecto abre BCF en Revit
    → Navega al viewpoint, corrige modelo
    → Marca issue como "Resolved"
    → Estructural abre BCF en Tekla
    → Corrige y marca como "Resolved"
    → Coordinador verifica en siguiente ronda
```

### Herramientas BCF

| Herramienta | Rol BCF |
|-------------|---------|
| **BIMcollab** | Plataforma cloud de gestión BCF. Integración con Revit, Navisworks, Solibri |
| **Trimble Connect** | Gestión de issues BCF + viewer 3D |
| **Solibri** | Validación de reglas + generación BCF |
| **Navisworks** | Exportar/importar BCF desde clash tests |
| **Revit** | Plugin BCF para recibir/resolver issues |

### BCF con Python (bcf-client)

```python
from bcf.v2.bcfxml import BcfXml

# Leer un archivo BCF
bcf = BcfXml.load("coordination_issues.bcfzip")

for topic_id, topic in bcf.topics.items():
    header = topic.header
    print(f"Issue: {header.title}")
    print(f"  Estado: {header.topic_status}")
    print(f"  Prioridad: {header.priority}")
    print(f"  Asignado: {header.assigned_to}")
    print(f"  Fecha: {header.creation_date}")
```

## Navisworks — Federación y Clash Detection

### Archivos NWC y NWD

| Formato | Descripción |
|---------|-------------|
| **NWC** | Cache de modelo. Exportado desde Revit/AutoCAD/Tekla. Lectura rápida |
| **NWD** | Modelo federado. Contiene múltiples NWC + Search Sets + Clash Tests |
| **NWF** | Archivo de sesión. Referencias a NWC/NWD + configuración de usuario |

### Flujo de federación

```
Revit ARQ → exportar ARQ.nwc
Revit EST → exportar EST.nwc
Revit MEP-E → exportar MEP-E.nwc
Revit MEP-S → exportar MEP-S.nwc
Revit MEP-HVAC → exportar MEP-HVAC.nwc

Navisworks Manage:
  → Append todos los NWC
  → Configurar Search Sets por disciplina
  → Crear Clash Tests por par
  → Ejecutar → Revisar → Clasificar → Exportar BCF/HTML
  → Guardar como PROYECTO.nwd
```

### Navisworks API (COM) para automatizar clash reports

```python
import win32com.client

nw = win32com.client.Dispatch("Navisworks.Automation")
nw.OpenFile(r"C:\BIM\Proyecto\federado.nwd")

doc = nw.Document
clash = doc.GetClash()
tests = clash.Tests

for i in range(tests.Count):
    test = tests.Item(i)
    print(f"Test: {test.DisplayName}")
    print(f"  Clashes: {test.Results.Count}")
    print(f"  Estado: {'Activo' if test.Enabled else 'Deshabilitado'}")

    for j in range(test.Results.Count):
        result = test.Results.Item(j)
        print(f"    Clash {j+1}: {result.Status} | "
              f"Item A: {result.Item1.DisplayName} | "
              f"Item B: {result.Item2.DisplayName}")

# Exportar reporte HTML
clash.ExportReport(
    r"C:\BIM\Reportes\clash_report.html",
    "HTML"
)

nw.Dispose()
```

### Automatizar clash test con parámetros

```python
import win32com.client

nw = win32com.client.Dispatch("Navisworks.Automation")
nw.OpenFile(r"C:\BIM\federado.nwd")

doc = nw.Document
clash_module = doc.GetClash()

# Crear nuevo clash test
new_test = clash_module.Tests.Add()
new_test.DisplayName = "EST vs MEP-Sanitario"
new_test.TestType = 0  # Hard clash
new_test.Tolerance = 0.025  # 25mm

# Configurar Selection A (Estructura) y B (MEP-S)
# ... (requiere Search Sets pre-configurados)

# Ejecutar
clash_module.RunTests()

# Exportar resultados
for i in range(clash_module.Tests.Count):
    test = clash_module.Tests.Item(i)
    if test.Results.Count > 0:
        test.ExportResults(
            f"C:\\BIM\\Reportes\\{test.DisplayName}.xml",
            "XML"
        )

nw.Dispose()
```

## IFC Federation con IfcOpenShell

Cuando no se dispone de Navisworks, se puede federar y analizar modelos IFC con herramientas open source.

### Federar modelos IFC

```python
import ifcopenshell

# Cargar modelos por disciplina
arq = ifcopenshell.open("arquitectura.ifc")
est = ifcopenshell.open("estructura.ifc")
mep = ifcopenshell.open("mep.ifc")

# Análisis cruzado: elementos por tipo en cada modelo
models = {"ARQ": arq, "EST": est, "MEP": mep}
for name, model in models.items():
    products = model.by_type("IfcProduct")
    print(f"{name}: {len(products)} elementos")
```

### Clash detection con ifcclash

```python
from ifcclash import ifcclash

settings = ifcclash.IfcClashSettings()
settings.output = "clash_results.json"

clasher = ifcclash.IfcClash(settings)
clasher.add_group("Estructura", "estructura.ifc")
clasher.add_group("MEP", "mep.ifc")
clasher.clash()
clasher.export()

# Leer resultados
import json
with open("clash_results.json") as f:
    clashes = json.load(f)
    print(f"Interferencias detectadas: {len(clashes)}")
    for c in clashes[:5]:
        print(f"  {c['a_name']} vs {c['b_name']} | Distancia: {c['distance']:.3f}m")
```

## Herramientas de coordinación BIM

| Herramienta | Función | Licencia |
|-------------|---------|----------|
| **Navisworks Manage** | Federación + Clash Detection + TimeLiner | Comercial (Autodesk) |
| **Navisworks Simulate** | Viewer + TimeLiner (sin clash) | Comercial (Autodesk) |
| **Autodesk Construction Cloud** | Model Coordination cloud | Comercial (Autodesk) |
| **Trimble Connect** | Federación cloud + BCF | Freemium |
| **BIMcollab** | Gestión BCF cloud | Freemium |
| **Solibri** | Validación de reglas BIM | Comercial |
| **IfcOpenShell (ifcclash)** | Clash detection open source | Open source |
| **Speckle** | Federación cloud open source | Open source |

### ACC Model Coordination (cloud)

```
Autodesk Construction Cloud > Model Coordination:
  → Subir modelos Revit/NWC a la nube
  → Clash detection automático
  → Revisión en visor web
  → Crear issues desde clashes
  → Asignar a equipos
  → Tracking de resolución
```

## Integración con `notion.upsert_task` para rastrear issues

```python
# Crear issue de coordinación en Notion
for clash in critical_clashes:
    await client.execute_task("notion.upsert_task", {
        "title": f"Clash: {clash['a_name']} vs {clash['b_name']}",
        "description": (
            f"Interferencia detectada entre {clash['a_discipline']} y "
            f"{clash['b_discipline']}.\n"
            f"Distancia: {clash['distance']:.3f}m\n"
            f"Ubicación: Nivel {clash['level']}, Eje {clash['grid']}\n"
            f"Prioridad: {'Alta' if clash['distance'] < 0 else 'Media'}"
        ),
        "status": "open",
        "assigned_to": clash["responsible_team"]
    })
```

## Integración con `linear.create_issue` para escalamiento

```python
# Escalar clashes críticos a Linear
critical = [c for c in clashes if c["severity"] == "critical"]

if critical:
    await client.execute_task("linear.create_issue", {
        "title": f"[BIM] {len(critical)} clashes críticos en Ronda {round_number}",
        "description": (
            f"Se detectaron {len(critical)} interferencias críticas en la "
            f"ronda de coordinación #{round_number}.\n\n"
            + "\n".join(
                f"- {c['a_name']} vs {c['b_name']} ({c['a_discipline']}/{c['b_discipline']})"
                for c in critical[:10]
            )
            + (f"\n... y {len(critical)-10} más" if len(critical) > 10 else "")
        ),
        "team": "BIM",
        "priority": "urgent",
        "labels": ["clash-detection", "coordination"]
    })
```

## Reporte de coordinación semanal

### Estructura del reporte

```
1. Resumen ejecutivo
   - Total de clashes por ronda
   - Clashes resueltos vs. nuevos vs. pendientes
   - Tendencia (gráfico)

2. Detalle por par de disciplinas
   - ARQ vs EST: X clashes (Y nuevos, Z resueltos)
   - EST vs MEP-E: ...
   - EST vs MEP-S: ...

3. Clashes críticos (top 10)
   - Descripción, ubicación, responsable, fecha límite

4. Acciones requeridas
   - Por equipo de diseño

5. Próxima sesión de coordinación
   - Fecha, participantes, agenda
```

### Generar reporte con datos

```python
import json
from datetime import datetime

def coordination_report(clashes: list, round_num: int) -> str:
    total = len(clashes)
    critical = sum(1 for c in clashes if c["severity"] == "critical")
    resolved = sum(1 for c in clashes if c["status"] == "resolved")
    new = sum(1 for c in clashes if c["status"] == "new")
    pending = total - resolved - new

    by_pair = {}
    for c in clashes:
        pair = f"{c['a_discipline']} vs {c['b_discipline']}"
        by_pair.setdefault(pair, []).append(c)

    report = f"""# Reporte Coordinación BIM — Ronda {round_num}
Fecha: {datetime.now().strftime('%Y-%m-%d')}

## Resumen
- Total interferencias: {total}
- Nuevas: {new}
- Pendientes: {pending}
- Resueltas: {resolved}
- Críticas: {critical}

## Por disciplinas
"""
    for pair, pair_clashes in sorted(by_pair.items()):
        report += f"- **{pair}**: {len(pair_clashes)} clashes\n"

    return report
```

## Ejemplos de uso con Rick

- **Rick: "Ejecutá el clash detection entre estructura y MEP"** → Navisworks COM API `RunTests()` o `ifcclash` open source.
- **Rick: "Generá el reporte de coordinación de la ronda 5"** → `coordination_report()` + `notion.upsert_task` para issues.
- **Rick: "Exportá los clashes a BCF para distribuir al equipo"** → Navisworks export BCF o generar BCF con Python.
- **Rick: "Cuántos clashes nuevos hay respecto a la ronda anterior?"** → Comparar JSON de rondas con diff.
- **Rick: "Escalá los clashes críticos a Linear"** → `linear.create_issue` con resumen de interferencias.
- **Rick: "Federá los 5 modelos IFC sin Navisworks"** → `ifcclash` con grupos por disciplina.

## Recursos oficiales

- BCF Standard: https://www.buildingsmart.org/standards/bsi-standards/bim-collaboration-format-bcf/
- Navisworks API: https://aps.autodesk.com/developer/overview/navisworks
- BIMcollab: https://www.bimcollab.com/
- Trimble Connect: https://connect.trimble.com/
- IfcOpenShell ifcclash: https://docs.ifcopenshell.org/ifcclash.html
- ACC Model Coordination: https://aps.autodesk.com/en/docs/acc/v1/tutorials/model-coordination/

## Notas

- La coordinación BIM es un proceso iterativo. Cada ronda reduce interferencias hasta llegar a cero (o tolerancia aceptable).
- BCF 2.1 es el formato más compatible entre herramientas. Usar BCF-API para flujos cloud.
- Navisworks Manage es la herramienta estándar de la industria para clash detection; Navisworks Simulate no incluye clash.
- `ifcclash` de IfcOpenShell es la alternativa open source para proyectos sin licencia Navisworks.
- Los Search Sets en Navisworks son la base de un buen clash test: dedicar tiempo a definirlos correctamente por disciplina, nivel y sistema.
- Las tolerancias de clash varían por par de disciplinas y por fase del proyecto (diseño vs. construcción).
