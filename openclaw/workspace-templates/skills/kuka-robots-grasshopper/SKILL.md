---
name: kuka-robots-grasshopper
description: >-
  Programación de robots industriales KUKA en Grasshopper mediante los plugins
  KukaPRC y Robots: toolpaths, fabricación digital y generación de código KRL.
  Use when "KukaPRC", "Robots plugin", "robot KUKA", "fabricación digital",
  "toolpath robot", "KRL", "Grasshopper robot", "robot Grasshopper",
  "fabricación robótica", "KUKA Grasshopper", "programar KUKA",
  "robot ABB", "robot UR Grasshopper".
metadata:
  openclaw:
    emoji: "\U0001F916"
    requires:
      env: []
---

# KUKA + Robots en Grasshopper — Fabricación Digital

Rick usa este skill para asistir con programación de robots industriales desde Grasshopper usando KukaPRC y el plugin Robots: generación de toolpaths, simulación y exportación a KRL/URScript.

## Plugins disponibles

| Plugin | Robots soportados | Output | Fuente |
|--------|------------------|--------|--------|
| **KukaPRC** | KUKA | KRL (.src) | Food4Rhino |
| **Robots** | KUKA, ABB, UR, Fanuc, Staubli | KRL, RAPID, URScript | GitHub (github.com/visose/Robots) |
| **HAL** | Multi-marca | Múltiples | Food4Rhino (comercial) |

## KukaPRC — Workflow básico

### Componentes principales por categoría

| Categoría | Componentes clave |
|-----------|------------------|
| **Robot** | `KUKA Robot` (definición del robot) |
| **Toolpath** | `Target`, `Joint Target`, `Speed`, `Zone` |
| **Tool** | `PRC Tool`, `Change Tool` |
| **Utilities** | `Safe Plane`, `Reduce Toolpath`, `Tangential Offset` |
| **I/O** | `Digital Output`, `Wait For Digital Input` |
| **Export** | `SRC Export` (genera código KRL) |

### Flujo típico en KukaPRC

```
[Curva o superficie] → [Dividir/puntos] → [Target] → [Tool] → [Speed/Zone] → [Robot] → [SRC Export]
```

### Definición de robot

1. Agregar componente `KUKA Robot`
2. Seleccionar modelo (KR 6 R900, KR 10 R1420, etc.)
3. Conectar posición base (plano)
4. Conectar herramienta (TCP)

### Targets y toolpaths

```
// Estructura de un Target en KukaPRC:
Target:
  - Plane: plano de orientación del TCP (Point3d + Normal)
  - Speed: velocidad (mm/s) via componente Speed
  - Zone: precisión de aproximación (mm) via componente Zone
  - Tool: herramienta activa
  - External axes (si aplica)
```

**Tipos de target:**
- **Cartesian Target**: posición definida por plano en espacio 3D
- **Joint Target**: posición definida por ángulos de eje (evita singularidades)

### Parámetros de movimiento

| Parámetro | Descripción | Valores típicos |
|-----------|-------------|-----------------|
| **Speed** | Velocidad TCP (mm/s) o porcentaje | 10–2000 mm/s |
| **Zone** | Radio de aproximación | Z0 (exacto), Z1, Z5, Z10, CONT |
| **Motion type** | LIN (lineal) o PTP (joint-to-joint) | LIN para trayectorias, PTP para reposición |

### Ejemplo de toolpath en superficie

```
// Workflow GH (pseudocódigo de nodos):

1. Surface (Srf) → Divide Surface (U=20, V=1) → Points
2. Points → Sort Points (por X o según dirección de trabajo)
3. Sort Points → Evaluate Surface → Normals
4. Normals + Points → Construct Plane (PlaneNormal)
5. Planes → KukaPRC Target (Speed=200, Zone=Z1)
6. Targets (lista) → KukaPRC Toolpath
7. Toolpath → KukaPRC Robot (con herramienta y base)
8. Robot → SRC Export → archivo .src (KRL)
```

### Exportación KRL

El componente `SRC Export` genera:
- `program.src` — programa principal
- `program.dat` — archivo de datos (tools, speeds)

Subir a KUKA KR C4 via WorkVisual, USB o red.

## Plugin Robots — Alternativa multi-marca

El plugin **Robots** (github.com/visose/Robots) soporta KUKA, ABB, UR, Fanuc y más.

### Instalación

```
Rhino PackageManager → buscar "Robots" → Instalar
```

### Conceptos del plugin Robots

| Concepto | Descripción |
|----------|-------------|
| **Robot System** | Define robot + tool + base |
| **Target** | Posición + orientación + velocidad + zona |
| **Motion** | JointMotion (PTP) o CartesianMotion (LIN/CIRC) |
| **Program** | Secuencia de targets → simula y exporta |
| **Tool** | TCP con frame, peso, centro de masa |

### Crear Tool (herramienta)

```python
# En Python Node de GH con Robots plugin
import Robots

# Definir herramienta por TCP
tcp_plane = x  # Input: Plane del TCP
tool_weight = 2.5  # kg
mesh = y  # Input: Mesh de la herramienta (visualización)

tool = Robots.Tool("Extrusora", tcp_plane, tool_weight, mesh=mesh)
a = tool
```

### Crear targets y programa

```python
import Robots
from Robots import Target, JointMotion, CartesianMotion, Speed, Zone, Frame

# Speed y Zone
spd = Speed(translation=200, rotation=1.0)  # mm/s, rad/s
zn = Zone(0.5)  # radio en mm

# Target cartesiano
target = Target(
    plane=planes[i],           # Rhino.Geometry.Plane
    speed=spd,
    zone=zn,
    motion=CartesianMotion(),
    tool=tool,
    frame=Frame.Default
)

targets.append(target)
```

### Programa y simulación

```python
# Crear programa
robot = robot_system  # Input: RobotSystem de GH
program = Robots.Program("Fabricacion", robot, [targets])

# Verificar errores
errors = program.Errors
warnings = program.Warnings

# Simular (obtener posición en tiempo t)
position, _ = program.Animate(t=0.5, calculateMeshes=True)

# Exportar código
code = program.Code  # Lista de strings por archivo

a = program
b = errors
c = code
```

## Técnicas de fabricación digital

### Impresión 3D robótica (extrusión)

```
Curva de extrusión → Dividir cada Xmm → Planos perpendiculares a tangente
→ Agregar offset Z por capa → Target list → Toolpath con speed baja
```

### Fresado CNC robótico

```
Superficie → Generar iso-curvas de mecanizado → Puntos equidistantes
→ Normales de superficie → Planos TCP (Normal = eje herramienta)
→ Ajustar orientación herramienta → Target list
```

### Winding / enrollado de fibra

```
Mandrel (geometría) → Geodésicas o curvas personalizadas
→ Puntos sobre curvas → Planos tangentes
→ Calcular tensión de fibra → Targets
```

## KRL — Código generado (referencia)

```krl
&ACCESS RVO
&REL 1
&PARAM EDITMASK = *
&PARAM TEMPLATE = C:\KRC\Roboter\Template\vorgabe
DEF program()
  ; Inicialización
  BAS(#INITMOV,0)
  
  ; Movimiento PTP a posición home
  PTP HOME Vel=100% DEFAULT
  
  ; Movimiento lineal (LIN)
  LIN {X 500.00, Y 0.00, Z 300.00, A 0.00, B -90.00, C 0.00} Vel=200mm/s CPDAT1 Tool[1] Base[0]
  
  ; Digital output
  $OUT[1] = TRUE
  WAIT SEC 0.5
  
  ; Retorno a home
  PTP HOME Vel=100% DEFAULT
END
```

## Singularidades y configuraciones

| Singularidad | Causa | Solución |
|--------------|-------|----------|
| **Wrist singularity** | Eje 4 y 6 alineados | Usar `Joint Target` en zona conflictiva |
| **Shoulder singularity** | Robot estirado | Reposicionar base o cambiar configuración |
| **Elbow singularity** | Brazo completamente extendido | Acortar alcance |

- Usar **`Safe Plane`** (KukaPRC) para definir planes de aproximación seguros antes de cada target.
- **Reduce Toolpath** elimina puntos redundantes para optimizar el programa.

## Ejemplos de uso con Rick

- **Rick: "Generá un toolpath para fresar una superficie curva con robot KUKA"** → Divide Surface → Normals → KukaPRC Targets → SRC Export.
- **Rick: "Cómo defino el TCP de una extrusora en Robots plugin?"** → `Robots.Tool` con TCP plane + peso.
- **Rick: "El robot llega a singularidad en ciertos targets, cómo lo evito?"** → Insertar Joint Targets en zonas problemáticas, usar Safe Planes.
- **Rick: "Exportá el toolpath a KRL para subirlo al KUKA KR C4"** → SRC Export de KukaPRC o `program.Code` de Robots plugin.
- **Rick: "Cuántos puntos tiene mi toolpath y cuánto tiempo tarda?"** → `program.Duration` en Robots plugin.

## Recursos oficiales

- KukaPRC en Food4Rhino: https://www.food4rhino.com/en/app/kukaprc
- KukaPRC Docs en GH Docs: https://grasshopperdocs.com/addons/kukaprc.html
- Robots Plugin GitHub: https://github.com/visose/Robots
- Rhino Developer (GH guides): https://developer.rhino3d.com/guides/grasshopper/
- KUKA KRL Manual: https://www.kuka.com/en-de/services/downloads (registración requerida)
- Discourse Robots plugin: https://discourse.mcneel.com/c/plug-ins/robots/

## Notas

- KukaPRC es gratuito para uso no comercial; verificar licencia para proyectos comerciales.
- El plugin Robots es open-source (MIT) y soporta más marcas que KukaPRC.
- Siempre simular el programa completo antes de enviar al robot físico.
- El sistema de coordenadas de Rhino (Z arriba) difiere del de KUKA (Z arriba con convenciones distintas); KukaPRC maneja la conversión.
- Para robots reales, la validación final siempre la hace un operador certificado en KUKA.
