---
name: docente-aec40
description: >-
  Asistente docente de David Moreira para el Master AEC 4.0. Prepara material
  de clase, ejercicios y guias tecnicas de programacion BIM: Dynamo, Python en
  Revit API, automatizacion y metodologia Citizen Developer.
  Use when "preparar clase", "material docente", "dynamo scripting",
  "revit python", "citizen developer", "ejercicio BIM", "guia tecnica",
  "clase automatizacion", "sesion master aec".
metadata:
  openclaw:
    emoji: "\U0001F393"
    requires:
      env: []
---

# Docente AEC 4.0 — Skill de David Moreira

Rick usa este skill para ayudar a David a preparar clases, ejercicios, guias tecnicas y materiales didacticos para el Master AEC 4.0 (Butic The New School / TEDIvirtual). El enfoque es eminentemente practico: Dynamo, Python, Revit API y metodologia Citizen Developer.

## Perfil docente

| Campo | Valor |
|-------|-------|
| **Institucion** | Butic The New School + TEDIvirtual |
| **Programa** | Master AEC 4.0 — Programacion y Automatizacion BIM |
| **Audiencia** | Arquitectos, ingenieros y coordinadores BIM sin perfil de programador |
| **Herramientas** | Dynamo, Revit API (Python/C#), Grasshopper, Power Automate, IA aplicada |
| **Enfoque** | Citizen Developer: resolver problemas reales con automatizacion accesible |
| **Credencial** | Autodesk Certified Instructor (ACI) #86900 |

## Metodologia Citizen Developer

El eje central del Master AEC 4.0 es convertir a profesionales AEC en Citizen Developers: personas capaces de automatizar sus propios flujos sin necesidad de ser programadores de software.

### Principios pedagogicos

1. **Problema primero:** Cada sesion parte de un problema real del sector (no de sintaxis ni teoria)
2. **Visual antes que textual:** Dynamo visual antes de saltar a Python/C#
3. **Iteracion rapida:** Ejercicios de 15-20 minutos con resultado tangible
4. **Replicabilidad:** Todo lo aprendido debe poder aplicarse al dia siguiente en el trabajo
5. **Gradualidad:** Nodos → Scripts Python → API → Automatizacion completa

### Niveles de autonomia Citizen Developer

| Nivel | Capacidad | Herramienta principal |
|-------|-----------|----------------------|
| 0 — Usuario | Consume herramientas existentes | Revit, Navisworks |
| 1 — Configurador | Adapta parametros y plantillas | Dynamo Player, scripts compartidos |
| 2 — Scriptero | Crea scripts basicos propios | Dynamo visual, Python basico |
| 3 — Automatizador | Flujos completos inter-aplicacion | Python avanzado, Revit API, Power Automate |
| 4 — Orquestador | Integra LLMs y APIs externas | IA aplicada, Make.com, Azure AI |

El Master AEC 4.0 lleva a los estudiantes del nivel 0 al nivel 3, con introduccion al nivel 4.

## Modulo 1 — Dynamo: Visual Scripting para BIM

### Fundamentos esenciales

- **Nodos clave:** Watch, Number Slider, Code Block, List.Map, List.Combine, If
- **Tipado dinamico:** Vigilar conversiones List → Element → String
- **Listas:** Anidamiento, @L1/@L2 (lacing), List.Transpose, List.Flatten
- **Geometria:** Diferencia entre geometria Dynamo y objetos Revit

### Acceso a datos de Revit desde Dynamo

```python
import clr
clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
doc = DocumentManager.Instance.CurrentDBDocument

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory
collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
OUT = list(collector)
```

### Best practices Dynamo

| Practica | Razon |
|---------|-------|
| Usar Code Block en vez de nodos matematicos basicos | Mas limpio, mas rapido |
| Nombrar nodos con anotaciones | Facilita mantenimiento |
| Modularizar en Custom Nodes | Reutilizacion y legibilidad |
| Usar List.Map en lugar de For Loops | Idioma nativo de Dynamo |
| Probar con un elemento antes de masivos | Evita corrupciones de modelo |
| Transacciones siempre en Python, no en nodos mixtos | Consistencia y rollback seguro |

### Anti-patterns Dynamo

- Anidar demasiados nodos sin agrupar (spaghetti graph)
- Ignorar errores de lista anidada sin inspeccionar con Watch
- Usar Element.GetParameterValueByName en bucles masivos sin caching
- Correr scripts sobre modelos vinculados sin abrir documento correcto

## Modulo 2 — Python en Dynamo y Revit API

### Estructura base de un script Python en Dynamo

```python
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument
inputs = IN[0]

results = []
TransactionManager.Instance.EnsureInTransaction(doc)
try:
    for element in inputs:
        pass  # operaciones sobre el modelo
    TransactionManager.Instance.TransactionTaskDone()
except Exception as e:
    TransactionManager.Instance.ForceCloseTransaction()
    raise e

OUT = results
```

### Operaciones frecuentes en Revit API

| Operacion | Codigo clave |
|-----------|-------------|
| Leer parametro | `elem.LookupParameter("Nombre").AsString()` |
| Escribir parametro | `elem.LookupParameter("Nombre").Set(valor)` |
| Filtrar por categoria | `FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls)` |
| Obtener tipo de elemento | `doc.GetElement(elem.GetTypeId())` |
| Mover elemento | `ElementTransformUtils.MoveElement(doc, elem.Id, XYZ(dx, dy, dz))` |
| Eliminar elemento | `doc.Delete(elem.Id)` |

### Best practices Python en Revit API

1. **Una transaccion por bloque logico** — no abrir/cerrar por cada elemento
2. **Usar BuiltInParameter cuando sea posible** — mas robusto que nombres de parametro
3. **Manejar excepciones por elemento** — un fallo no debe detener el procesamiento masivo
4. **Cachear colecciones** — no re-consultar FilteredElementCollector dentro de un loop
5. **Validar tipos antes de Set()** — Double vs Integer vs String generan errores silenciosos

### Ejercicio tipo: Renombrar habitaciones por nivel

```python
# Agregar prefijo "P1-" a todas las habitaciones del nivel 1
rooms = IN[0]

TransactionManager.Instance.EnsureInTransaction(doc)
renamed = []
for room in rooms:
    nombre = room.LookupParameter("Name").AsString()
    if not nombre.startswith("P1-"):
        room.LookupParameter("Name").Set("P1-" + nombre)
        renamed.append(room.Id.IntegerValue)
TransactionManager.Instance.TransactionTaskDone()
OUT = renamed
```

## Modulo 3 — IA y Orquestacion BIM

### IA aplicada al sector AEC (2025)

| Aplicacion | Herramienta | Caso de uso |
|-----------|-------------|-------------|
| Clasificacion automatica de planos | Vision API / GPT-4V | QA automatico en CDE |
| Generacion de documentacion | LLMs (Gemini, GPT-4) | Especificaciones, memorias |
| Extraccion de datos de PDF | Document Intelligence | Importar mediciones de proveedores |
| Asistente de coordinacion BIM | Copilot Studio + Revit API | Chatbot interno que ejecuta comandos |
| Revision automatica de modelos | Dynamo + reglas LLM | Verificar normas y estandares BIM |

### Prompts efectivos para asistentes BIM

**Estructura de prompt tecnico:**
```
Contexto: [software version, tipo de modelo, standard]
Rol: Eres un especialista en [Revit API / Dynamo / IFC]
Tarea: [accion especifica y acotada]
Restricciones: [limitaciones del entorno]
Formato de salida: [codigo Python / JSON / tabla]
```

**Ejemplo prompt Dynamo:**
```
Eres un experto en Dynamo 2.x con Revit 2024.
Escribe un script Python (nodo PythonScript) que lea todos los muros del modelo
activo y exporte a una lista: [Id, Tipo, Nivel, Longitud_m].
Usa FilteredElementCollector. Maneja la transaccion correctamente.
```

## Modulo 4 — Diseño instruccional AEC 4.0

### Estructura de una sesion de 2 horas

| Bloque | Duracion | Contenido |
|--------|----------|-----------|
| Contexto y problema | 10 min | Caso real de obra o oficina |
| Demo en vivo | 20 min | David muestra el flujo completo (no slides) |
| Ejercicio guiado | 40 min | Estudiantes replican con variacion |
| Desafio libre | 25 min | Extension con pista minima |
| Cierre y conexion | 5 min | "Con esto pueden mañana hacer..." |

### Tipos de material a generar

| Tipo | Descripcion | Cuando usarlo |
|------|-------------|---------------|
| Guia tecnica | Referencia rapida: comandos, parametros, patrones | Pre-clase, consulta rapida |
| Ejercicio base | Problema resuelto paso a paso | Durante la sesion |
| Ejercicio desafio | Variacion con menos guia | Final de sesion o tarea |
| Checklist de errores comunes | Top 5 errores y como solucionarlos | Post-ejercicio |
| Plantilla reutilizable | Script/grafo comentado | Entregable de la sesion |

### Niveles de dificultad para ejercicios

- **Nivel 1 (Replicar):** Script dado, cambiar solo parametros de entrada
- **Nivel 2 (Adaptar):** Esqueleto dado, completar logica principal
- **Nivel 3 (Crear):** Problema definido, solucion libre
- **Nivel 4 (Optimizar):** Script funcional dado, mejorar o extender

### Errores mas frecuentes en estudiantes AEC

| Error | Causa raiz | Solucion pedagogica |
|-------|-----------|---------------------|
| Script falla sin mensaje claro | No leen el Watch node | Enseniar a depurar antes que a programar |
| Loop infinito / Revit se congela | Transaccion mal cerrada | Siempre usar EnsureInTransaction + ForceClose |
| Resultado None inesperado | Parametro con nombre incorrecto | Verificar con LookupParameter is not None |
| Crash en modelos grandes | Sin filtros previos | Filtrar siempre por nivel/view antes de colectar |

## Conceptos clave del Master AEC 4.0

| Concepto | Definicion operacional |
|----------|----------------------|
| **BIM** | Metodologia de gestion de informacion del ciclo de vida (ISO 19650) |
| **Dynamo** | Entorno visual de programacion para Revit; automatizar sin codigo textual |
| **Revit API** | Interfaz programatica; acceso total a elementos, parametros y documentos |
| **IronPython / CPython** | Dos motores Python en Dynamo; CPython 3.x para libs externas |
| **Citizen Developer** | Profesional no-programador que crea automatizaciones propias |
| **CDE** | Common Data Environment: repositorio central de informacion (ACC, BIM 360) |
| **LOD** | Level of Development: grado de desarrollo de geometria e informacion |

## Reglas de comunicacion docente

- Instrucciones en segunda persona: "Abre Dynamo desde el menu Add-ins"
- Evitar jerga sin definir: "iteracion" → "repetir para cada elemento"
- Acompañar codigo con descripcion en lenguaje natural
- Usar tablas para comparar opciones, no parrafos largos
- Prohibido: "Como es sabido...", "Simplemente...", "Es facil..."

### Estructura de guia tecnica

```
## [Titulo del procedimiento]
**Cuando usar:** [caso de uso en 1 linea]
**Prerequisitos:** [lo que debe tener instalado/abierto]
**Pasos:**
1. [accion]
2. [accion]
**Resultado esperado:** [descripcion del output]
**Errores comunes:** [tabla de error → solucion]
```

## Prompts para generar material de clase

### Generar ejercicio Dynamo (nivel 2)

```
Crea un ejercicio de nivel 2 (adaptar) de Dynamo para arquitectos sin
experiencia en programacion. Tema: leer areas de habitaciones y exportarlas
a lista. Formato: contexto del problema, esqueleto con nodos nombrados,
codigo Python parcial con 3 huecos para completar, resultado esperado,
2 errores comunes y sus soluciones.
```

### Generar guia rapida Revit API

```
Genera una guia de referencia rapida (1 pagina) sobre FilteredElementCollector
en Revit API con Python. Incluir: proposito, 5 patrones de uso con codigo
funcional, 3 errores tipicos y como evitarlos. Tono directo, sin introduccion.
```

### Adaptar material para nivel 1

```
Tengo este script Python para Dynamo [pegar script]. Adaptalo para nivel 1:
agrega comentarios en cada linea explicando que hace, reemplaza variables con
nombres mas descriptivos, agrega 3 prints de depuracion clave. No cambies la
logica, solo hazlo mas legible para principiantes.
```
