---
name: kuka-robots-grasshopper
description: >-
  Programación de robots industriales KUKA desde Grasshopper con plugins KukaPRC
  y Robots: generación de toolpaths, simulación, código KRL y fabricación digital.
  Use when "KukaPRC", "Robots plugin", "robot Grasshopper", "KUKA GH",
  "fabricación digital", "toolpath robot", "KRL", "robot industrial Rhino",
  "KUKA programación", "robotic fabrication".
metadata:
  openclaw:
    emoji: "\U0001F916"
    requires:
      env: []
---

# KUKA + Robots — Grasshopper Skill

Rick usa este skill para asistir con programación de robots industriales KUKA desde Grasshopper usando los plugins KukaPRC y Robots (de Visose), generación de código KRL y flujos de fabricación digital robotizada.

## Plugins disponibles

| Plugin | Autor | Enfoque |
|--------|-------|---------|
| **KukaPRC** | KUKA | Integración directa con KUKA robots; simulación y KRL |
| **Robots** | Visose (GitHub) | Multi-marca (KUKA, ABB, UR, etc.); código abierto |

Ambos se instalan desde **Yak** (package manager de Rhino) o desde [Food4Rhino](https://www.food4rhino.com/).

---

## KukaPRC — Flujo de trabajo

### Instalación

```
1. Rhino 7/8 → Tools → Package Manager (Yak)
2. Buscar "KukaPRC" → Instalar
3. Reiniciar Rhino
4. Verificar en GH: panel "KUKA|prc"
```

### Componentes principales de KukaPRC

| Componente | Función |
|-----------|---------|
| `KUKA|prc Core` | Componente principal; recibe comandos, genera código KRL |
| `Linear` | Movimiento lineal (LIN) a una posición |
| `PTP` | Point-to-Point (PTP); movimiento de eje a eje |
| `Spline` | Movimiento suave por spline continua |
| `Circular` | Movimiento circular (CIRC) |
| `SetDIO` | Activar/desactivar salida digital |
| `Wait` | Pausa en segundos |
| `Tool` | Definir TCP (Tool Center Point) |
| `Frame` | Definir sistema de coordenadas de trabajo (FRAME) |

### Grafo básico KukaPRC en GH

```
[Geometría/Curvas]
      ↓
[Dividir curva en puntos + frames]
      ↓ Planos (Plane)
[KUKA|prc Linear]  ← Tool, Frame, Speed
      ↓ Comandos
[KUKA|prc Core]    ← Robot model, Commands
      ↓
[Simulación 3D]  +  [Exportar KRL]
```

### Definir TCP (Tool Center Point)

```
En GH con KukaPRC:
1. Componente "Tool" de KUKA|prc
2. Entradas:
   - TCP Plane: plano que define origen y orientación del TCP
   - Name: nombre de la herramienta (ej: "spindle_v1")
   - Load: masa en kg del end-effector
   - LoadOffset: desplazamiento del centro de masa
```

### Generar frames desde curva (toolpath)

```python
# En GhPython — dividir curva en frames
import Rhino.Geometry as rg
import math

curve = IN_curve  # curva de entrada
count = int(IN_count)  # número de puntos

# Dividir por parámetro
params = curve.DivideByCount(count - 1, True)
frames = []
for t in params:
    pt = curve.PointAt(t)
    tangent = curve.TangentAt(t)
    tangent.Unitize()
    normal = rg.Vector3d.CrossProduct(tangent, rg.Vector3d.ZAxis)
    normal.Unitize()
    # Frame con Z = tangente (dirección de avance), X = normal
    frame = rg.Plane(pt, normal, rg.Vector3d.CrossProduct(normal, tangent))
    frames.append(frame)

a = frames
```

### Velocidades y zonas de aproximación

| Parámetro | Descripción | Valor típico |
|-----------|-------------|--------------|
| `Speed` | Velocidad en mm/s | 50–500 mm/s |
| `Acceleration` | % de aceleración máxima | 10–100% |
| `ApproxDistance` | Zona de aproximación (blend) | 5–50 mm |

---

## Plugin Robots (Visose) — Multi-marca

### Instalación

```
1. Rhino 7/8 → Tools → Package Manager (Yak)
2. Buscar "Robots" → Instalar
3. O desde GitHub: github.com/visose/Robots
4. Reiniciar Rhino
```

### Modelos de robots disponibles

- **KUKA**: KR 6 R900, KR 10 R1100, KR 210 R2700, KR 210-2, y más
- **ABB**: IRB 120, IRB 1200, IRB 6700
- **Universal Robots**: UR3, UR5, UR10
- **Staubli**, **Fanuc**, **Franka** (en desarrollo)

### Componentes principales de Robots

| Componente | Función |
|-----------|---------|
| `Load Robot` | Carga modelo de robot por nombre |
| `Create Program` | Genera programa con targets y robot |
| `Target` | Define una posición objetivo (frame + velocidad) |
| `Speed` | Define velocidad (translación + rotación + externa) |
| `Zone` | Define zona de aproximación (blend) |
| `Tool` | Define TCP con masa y centro de masa |
| `Frame` | Define sistema de referencia del trabajo |
| `Simulate` | Simula movimiento y muestra colisiones |
| `Save Code` | Guarda código KRL/RAPID/URP en disco |
| `Custom Code` | Inserta líneas de código nativas |

### Grafo básico Robots en GH

```
[Load Robot "KUKA KR 210-2"]
         ↓
[Frames del toolpath]
         ↓
[Target] ← Speed, Zone, Tool, Frame
         ↓ Lista de Targets
[Create Program] ← Robot, Targets
         ↓
[Simulate]   [Save Code → .src / .dat]
```

### Definir Target con Robots

```
Target:
  - Plane: frame de la posición (orientación del TCP)
  - Speed: (translación mm/s, rotación °/s, ext mm/s, ext °/s)
  - Zone: distancia de approximation (mm)
  - Tool: definición del TCP
  - Frame: frame de trabajo (WorkObject en KUKA)
  - Config: configuración de eje (None = automático)
```

---

## Código KRL generado — Estructura

### Archivo .src (programa)

```krl
DEF Mi_Programa()
  ; Generado por KukaPRC / Robots
  BAS(#INITMOV, 0)
  $TOOL = TOOL_DATA[1]   ; Herramienta activa
  $BASE = BASE_DATA[1]   ; Frame de trabajo activo

  ; Movimiento PTP al home
  PTP {A1 0, A2 -90, A3 90, A4 0, A5 -90, A6 0}

  ; Movimiento lineal
  LIN {X 500, Y 0, Z 300, A 0, B 90, C 0} C_DIS
  LIN {X 600, Y 100, Z 300, A 0, B 90, C 0} C_DIS
  LIN {X 600, Y 100, Z 200, A 0, B 90, C 0}

  ; Salida digital
  $OUT[1] = TRUE
  WAIT SEC 0.5
  $OUT[1] = FALSE

  PTP HOME
END
```

### Tipos de movimiento KRL

| Instrucción | Tipo | Uso |
|------------|------|-----|
| `PTP` | Point-to-Point | Reposicionamiento rápido; trayectoria no predecible |
| `LIN` | Lineal | Trayectoria recta en espacio cartesiano |
| `CIRC` | Circular | Arco definido por punto de paso y punto final |
| `SPTP` | Soft PTP | PTP con perfil suave |
| `SLIN` | Soft LIN | LIN con perfil suave |

### Aproximaciones (Blending)

```krl
; C_DIS = continuación por distancia (zona de approximation)
LIN {X 500, Y 0, Z 300, A 0, B 90, C 0} C_DIS
; C_VEL = continuación por velocidad constante
LIN {X 600, Y 0, Z 300, A 0, B 90, C 0} C_VEL
; Sin C_* = movimiento exacto (FINE)
LIN {X 700, Y 0, Z 300, A 0, B 90, C 0}
```

---

## Flujo completo de fabricación digital

```
1. DISEÑO en Rhino/GH
   → Geometría de pieza y trayectoria de herramienta

2. TOOLPATH en GH (KukaPRC o Robots)
   → Frames sobre la geometría → Targets
   → Configurar TCP, velocidades, zonas

3. SIMULACIÓN en GH
   → Verificar alcance del robot
   → Detectar singularidades y límites de eje
   → Visualizar colisiones

4. EXPORTAR código
   → KukaPRC: Export .src / .dat
   → Robots: Save Code → carpeta en disco

5. TRANSFERIR a robot
   → Via USB, red Ethernet o WorkVisual (KUKA)

6. EJECUTAR en robot
   → Modo T1 (velocidad reducida) para verificación
   → Modo AUTO para producción
```

---

## Consideraciones de seguridad

| Aspecto | Recomendación |
|---------|--------------|
| Velocidad de prueba | Siempre verificar en T1 (≤250 mm/s) antes de AUTO |
| Singularidades | Evitar extensión completa del brazo (eje 2+4+6 alineados) |
| Zona de trabajo | Definir `WORKSPACE` con límites en WorkVisual |
| E-stop virtual | Implementar lógica de paro en `$OUT` / SafeOp |
| TCP calibrado | Calibrar TCP con herramienta física antes de producción |

---

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Robot no alcanza posición | Punto fuera del espacio de trabajo | Acercar base o ajustar orientación del TCP |
| Singularidad detectada | Eje en posición degenerada | Ajustar orientación del frame para evitar la configuración |
| Orientación incorrecta | TCP mal definido | Recalibrar TCP o ajustar plano de entrada |
| Colisión simulada | Robot intersecta con pieza o mesa | Ajustar altura del toolpath o reposicionar base |

---

## Links oficiales

- [KukaPRC — Food4Rhino](https://www.food4rhino.com/en/app/kukaprc) — Descarga y documentación
- [Robots Plugin GitHub](https://github.com/visose/Robots) — Código fuente, wiki y ejemplos
- [KUKA Developer Docs](https://www.kuka.com/en-de/products/robotics-systems/software/system-software/kuka-system-software) — Software y documentación oficial KUKA
- [GH Robots Community](https://www.grasshopper3d.com/group/robots) — Foro del plugin Robots
- [KRL Programming Guide](https://www.kuka.com/-/media/kuka-corporate/documents/manual/kuka-system-software-kss/kuka-system-software_kss_8-3_programming_manual_en.pdf) — Manual de programación KRL
